package com.dsh.android.p48;

import android.os.*;
import com.dsh.p37.P37RemoteProcess;
import com.dsh.android.p53.P53StartOrder;
import com.dsh.android.p68.P68AndroidBinderIntake;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

/**
 * P48 true original DSH host-side authenticated Binder adapter to a Java
 * Process proxy. Never exposes a general start(command) interface.
 * Only a pre-authorized synthetic /system/bin/id -u fixture is executed.
 */
public final class P48HostProcessProbe {
  public interface Listener {
    void report(String status);
    void fail(String code);
  }
  /**
   * P53: deliver a live java.lang.Process facade only AFTER an authenticated
   * CHILD_STARTED frame emitted after isolated ProcessBuilder.start returns.
   * HELLO alone never authorizes this callback. Neither proves Node READY.
   * Only trusted same-app code may receive the facade; no global registry.
   */
  public interface LiveProcessReceiver {
    void onLiveProxy(java.lang.Process proxy,int isolatedUid);
  }
  private final Handler main=new Handler(Looper.getMainLooper());
  private final Messenger isolated;
  private final String session;
  private final Listener listener;
  private final boolean exactOriginalArm64Node;
  private final LiveProcessReceiver liveProcessReceiver;
  private final CountDownLatch readers=new CountDownLatch(2);
  private final AtomicReference<String> stdout=new AtomicReference<>("");
  private final AtomicReference<String> stderr=new AtomicReference<>("");
  private int workerUid=-1;
  private final P53StartOrder startOrder=new P53StartOrder();
  private P37RemoteProcess proxy;
  private final boolean p68Mode;
  private P68AndroidBinderIntake p68;
  private boolean complete,failed,started,childStartedAck;
  private final Messenger inbox=new Messenger(new Handler(Looper.getMainLooper()) {
    @Override public void handleMessage(Message m) {
      if(failed||complete)return;
      if(p68Mode){handleP68Message(m);return;}
      int sender=m.sendingUid;
      if(!android.os.Process.isIsolatedUid(sender) ||
         sender==android.os.Process.myUid() ||
         (workerUid!=-1&&sender!=workerUid)) {
        failClosed("P48_BINDER_SENDER_UID_NOT_ISOLATED");return;
      }
      Bundle b;
      try{b=m.getData();}catch(RuntimeException e){failClosed("P48_BAD_BUNDLE");return;}
      if(!session.equals(b.getString("session"))) {
        failClosed("P48_SESSION_MISMATCH");return;
      }
      if(!startOrder.accept(m.what,b.getLong("seq",-1))) {
        failClosed("P53_PROTOCOL_ORDER_OR_REPLAY_REJECTED");return;
      }
      if(m.what==P48FixedIsolatedChild.HELLO) {
        if(workerUid!=-1 || b.getLong("seq",-1)!=0){
          failClosed("P48_DUPLICATE_HELLO");return;
        }
        workerUid=sender;
        proxy=new P37RemoteProcess(workerUid,session,
            android.os.Process::isIsolatedUid,
            new P37RemoteProcess.RemoteControl(){
              @Override public void requestGracefulStop() {
                sendControl(P48FixedIsolatedChild.STOP);
              }
              @Override public void requestForceStop() {
                sendControl(P48FixedIsolatedChild.KILL);
              }
            });
        new Thread(()->collect(proxy.getInputStream(),stdout),
                   "p48-host-stdout").start();
        new Thread(()->collect(proxy.getErrorStream(),stderr),
                   "p48-host-stderr").start();
        listener.report("P48_ORIGINAL_APP_BOUND_P37_REMOTE_PROCESS=PASS");
        listener.report("P53_BINDER_HELLO_ALONE_NOT_CHILD_STARTED=PASS");
        return;
      }
      if(proxy==null || workerUid!=sender){
        failClosed("P48_PROXY_OR_WORKER_MISMATCH");return;
      }
      if(m.what==P48FixedIsolatedChild.CHILD_STARTED) {
        // P53 one-shot proof: only this isolated UID + session + strict
        // monotone seq can attest ProcessBuilder.start() returned.
        // This is NOT a production Node READY nor pid/SELinux attestation.
        if(childStartedAck || b.containsKey("data") ||
           b.containsKey("exitCode")) {
          failClosed("P53_DUPLICATE_OR_MALFORMED_CHILD_STARTED");return;
        }
        childStartedAck=true;
        if(liveProcessReceiver!=null){
          try {liveProcessReceiver.onLiveProxy(proxy,workerUid);}
          catch(RuntimeException rejected){
            failClosed("P53_CHILD_STARTED_RECEIVER_REJECTED");return;
          }
        }
        listener.report("P53_AUTHENTICATED_CHILD_STARTED_BEFORE_PROCESS_HANDOFF=PASS");
        return;
      }
      // Explicit pre-start FAIL is allowed to terminate without ever
      // handing out a fake Process. Stdout/stderr/exit are never allowed.
      if(m.what==P48FixedIsolatedChild.FAIL){
        failClosed("P48_WORKER_CHILD_DENIED_OR_FAILED");return;
      }
      if(!childStartedAck){
        failClosed("P53_FRAME_BEFORE_REAL_CHILD_STARTED");return;
      }
      if(m.what==P48FixedIsolatedChild.STDOUT ||
         m.what==P48FixedIsolatedChild.STDERR) {
        byte[] payload=b.getByteArray("data");
        if(payload==null||payload.length<1||payload.length>128 ||
           !(m.what==P48FixedIsolatedChild.STDOUT
             ? proxy.onAuthenticatedStdout(sender,session,payload)
             : proxy.onAuthenticatedStderr(sender,session,payload))) {
          failClosed("P48_FRAME_REJECTED");return;
        }
      }else if(m.what==P48FixedIsolatedChild.EXIT){
        int exit=b.getInt("exitCode",125);
        if(!proxy.onAuthenticatedExit(sender,session,exit)){
          failClosed("P48_EXIT_REJECTED");return;
        }
        verifyAsync(exit);
      }else failClosed("P48_UNRECOGNIZED_MESSAGE");
    }
  });

  public P48HostProcessProbe(Messenger isolated,String session,Listener listener) {
    this(isolated,session,listener,false,null,false);
  }
  public P48HostProcessProbe(Messenger isolated,String session,
                             Listener listener,boolean exactOriginalArm64Node) {
    this(isolated,session,listener,exactOriginalArm64Node,null,false);
  }
  public P48HostProcessProbe(Messenger isolated,String session,
                             Listener listener,boolean exactOriginalArm64Node,
                             LiveProcessReceiver liveProcessReceiver) {
    this(isolated,session,listener,exactOriginalArm64Node,liveProcessReceiver,false);
  }
  public P48HostProcessProbe(Messenger isolated,String session,
                             Listener listener,boolean exactOriginalArm64Node,
                             LiveProcessReceiver liveProcessReceiver,
                             boolean enableP68ForFixtureOnly) {
    if(isolated==null||listener==null||session==null||
       !session.matches("[a-f0-9]{64}"))
      throw new IllegalArgumentException("P48_BAD_HOST_SESSION");
    this.isolated=isolated;
    this.session=session;
    this.listener=listener;
    this.exactOriginalArm64Node=exactOriginalArm64Node;
    this.liveProcessReceiver=liveProcessReceiver;
    this.p68Mode=enableP68ForFixtureOnly;
  }
  /**
   * P68 opt-in test path: Binder-supplied framework sendingUid is checked
   * inside P68AndroidBinderIntake, then P67 owns all sequence and Process
   * lifecycle transitions. The older P48 path remains unchanged.
   */
  private void handleP68Message(Message message) {
    if(p68==null){
      p68=new P68AndroidBinderIntake(session,
          new P37RemoteProcess.RemoteControl(){
            @Override public void requestGracefulStop(){
              sendControl(P48FixedIsolatedChild.STOP);
            }
            @Override public void requestForceStop(){
              sendControl(P48FixedIsolatedChild.KILL);
            }
          });
    }
    P68AndroidBinderIntake.Result result=p68.accept(message);
    if(result==P68AndroidBinderIntake.Result.REJECTED){
      failClosed("P68_UID_SESSION_FRAME_OR_SEQUENCE_REJECTED");return;
    }
    if(result==P68AndroidBinderIntake.Result.HELLO){
      workerUid=p68.isolatedUid();
      if(proxy!=null || childStartedAck ||
         p68.processAfterAuthenticatedChildStart()!=null){
        failClosed("P68_HELLO_NOT_UNSTARTED");return;
      }
      listener.report("P68_BINDER_HELLO_NO_PROCESS_ALLOCATED=PASS");
      listener.report("P53_BINDER_HELLO_ALONE_NOT_CHILD_STARTED=PASS");
      return;
    }
    if(result==P68AndroidBinderIntake.Result.CHILD_STARTED){
      if(proxy!=null || childStartedAck ||
         !(p68.processAfterAuthenticatedChildStart() instanceof P37RemoteProcess)){
        failClosed("P68_VERIFIED_CHILD_PROXY_UNAVAILABLE");return;
      }
      proxy=(P37RemoteProcess)p68.processAfterAuthenticatedChildStart();
      childStartedAck=true;
      new Thread(()->collect(proxy.getInputStream(),stdout),
                 "p68-host-stdout").start();
      new Thread(()->collect(proxy.getErrorStream(),stderr),
                 "p68-host-stderr").start();
      listener.report("P48_ORIGINAL_APP_BOUND_P37_REMOTE_PROCESS=PASS");
      if(liveProcessReceiver!=null){
        try {liveProcessReceiver.onLiveProxy(proxy,workerUid);}
        catch(RuntimeException rejection){
          failClosed("P68_PROCESS_RECEIVER_REJECTED");return;
        }
      }
      listener.report("P68_ANDROID_BINDER_P67_P37_CHILD_HANDOFF=PASS");
      listener.report("P68_CHILD_STARTED_NOT_ENGINE_READY=PASS");
      listener.report("P53_AUTHENTICATED_CHILD_STARTED_BEFORE_PROCESS_HANDOFF=PASS");
      return;
    }
    if(result==P68AndroidBinderIntake.Result.FAIL){
      failClosed("P68_WORKER_FAILURE");return;
    }
    if(result==P68AndroidBinderIntake.Result.EXIT) {
      verifyAsync(message.getData().getInt("exitCode",125));return;
    }
    // STDOUT and STDERR have already been forwarded by P67 into P37.
  }

  public void start() {
    if(started)throw new IllegalStateException("P48_ALREADY_STARTED");
    started=true;
    Message m=Message.obtain(null,P48FixedIsolatedChild.START);
    Bundle b=new Bundle();b.putString("session",session);
    b.putString("p50_mode",exactOriginalArm64Node?
        "p50-exact-original-node":"p48-fixed-id");
    m.setData(b);
    m.replyTo=inbox;
    try{isolated.send(m);}
    catch(Exception e){failClosed("P48_INIT_SEND_FAILED");return;}
    main.postDelayed(()->{
      if(!failed&&!complete)failClosed("P48_ISOLATED_CHILD_DEADLINE");
    },14000);
  }
  private void sendControl(int code){
    Message m=Message.obtain(null,code);
    Bundle b=new Bundle();b.putString("session",session);m.setData(b);
    try{isolated.send(m);}catch(Exception ignored){}
  }
  private void collect(InputStream input,AtomicReference<String> sink){
    try(InputStream stream=input; ByteArrayOutputStream out=new ByteArrayOutputStream()){
      byte[] buf=new byte[64];int n;
      while((n=stream.read(buf))!=-1){
        if(n>256-out.size())throw new IOException("P48_HOST_STREAM_LIMIT");
        out.write(buf,0,n);
      }
      sink.set(new String(out.toByteArray(),StandardCharsets.US_ASCII));
    }catch(Exception e){sink.set("P48_READER_ERROR");}
    finally{readers.countDown();}
  }
  private void verifyAsync(int exit){
    new Thread(()->{
      boolean done;
      try{done=readers.await(4,TimeUnit.SECONDS);}
      catch(InterruptedException e){Thread.currentThread().interrupt();done=false;}
      final boolean completeReaders=done;
      main.post(()->{
        if(failed||complete)return;
        if(!childStartedAck || !completeReaders || exit!=0 || proxy==null ||
           proxy.terminalReason()!=P37RemoteProcess.TerminalReason.REMOTE_EXIT||
           proxy.isAlive() ||
           !stdout.get().equals(exactOriginalArm64Node?
                "UID="+workerUid+"\nBOOT\nREADY\n":workerUid+"\n") ||
           !stderr.get().equals(exactOriginalArm64Node?"P50-STDERR\n":"")) {
          failClosed("P48_P37_STREAM_UID_OR_EOF_MISMATCH");return;
        }
        try {
          if(proxy.exitValue()!=0 || proxy.waitFor(0,TimeUnit.SECONDS)==false){
            failClosed("P48_PROCESS_WAIT_EXIT_MISMATCH");return;
          }
        }catch(InterruptedException e){
          Thread.currentThread().interrupt();
          failClosed("P48_PROCESS_WAIT_INTERRUPTED");return;
        }
        complete=true;
        if(exactOriginalArm64Node) {
          listener.report("P50_REAL_ORIGINAL_DSH_PACKAGE_EXACT_NODE_IN_ISOLATED_UID=PASS");
          listener.report("P50_PINNED_NODE_STREAM_STDERR_READY_EXIT=PASS");
          listener.report("P50_ORIGINAL_NODE_PRODUCTION_SCRIPTS=NOT_EXECUTED");
          listener.report("P50_REAL_DSH_ENGINEMANAGER_PROXY_HANDOFF=NO");
        }else {
          listener.report("P48_ORIGINAL_APK_ISOLATED_CHILD_UID_MATCHES_BINDER=PASS");
          listener.report("P48_P37_PROCESS_STDOUT_EOF_WAIT_EXIT=PASS");
          listener.report("P48_HOST_DID_NOT_EXECUTE_CHILD=PASS_SCOPE_LIMITED");
          listener.report("P48_REAL_PRODUCTION_DSH_NODE=NOT_STARTED");
        }
        listener.report("P48_FIXED_SIGNED_V139_APK=BLOCKED");
      });
    },"p48-host-process-verify").start();
  }
  private void failClosed(String code){
    if(failed||complete)return;
    failed=true;
    if(p68!=null)p68.disconnected();
    if(proxy!=null)proxy.onTransportLost();
    listener.fail(code);
  }
  public void close(){
    if(p68!=null)p68.disconnected();
    if(proxy!=null&&proxy.isAlive())proxy.destroyForcibly();
    if(!complete&&!failed)failClosed("P48_HOST_CLOSED");
  }
}
