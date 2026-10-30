package com.dsh.p38.nodebridge;

import android.app.Activity;
import android.content.*;
import android.os.*;
import android.widget.*;
import com.dsh.p37.P37RemoteProcess;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

/** Separate trusted Android host, never the actual DSH MainActivity. */
public final class P38Activity extends Activity {
  private final Handler main=new Handler(Looper.getMainLooper());
  private final SecureRandom random=new SecureRandom();
  private TextView report;
  private Button start,stop;
  private Messenger isolated;
  private boolean bound=false,started=false,complete=false,failed=false;
  private int workerUid=-1;
  private long expectedSeq=1;
  private String session,status="NOT_STARTED",failure="NONE";
  private P37RemoteProcess proxy;
  private final CountDownLatch readers=new CountDownLatch(2);
  private final AtomicReference<String> stdout=new AtomicReference<>("");
  private final AtomicReference<String> stderr=new AtomicReference<>("");

  private String newSession() {
    byte[] bytes=new byte[32];random.nextBytes(bytes);
    StringBuilder b=new StringBuilder(64);
    for(byte a:bytes)b.append(String.format(java.util.Locale.ROOT,"%02x",a&255));
    return b.toString();
  }
  private void render() {
    report.setText("P38_REAL_ORIGINAL_NODE_PROCESS_STREAM="+
        (complete?"PASS":failed?"BLOCKED":"INCOMPLETE")
        +"\nANDROID_API="+Build.VERSION.SDK_INT
        +"\nABI="+Build.SUPPORTED_ABIS[0]
        +"\nTRUSTED_HOST_UID="+android.os.Process.myUid()
        +"\nWORKER_BINDER_UID="+workerUid
        +"\nVERIFIED_NODE_STDOUT="+(complete?"PASS":"NOT_PROVEN")
        +"\nSEPARATE_STDERR="+(complete?"PASS":"NOT_PROVEN")
        +"\nREAL_JAVA_PROCESS_PROXY_WAIT_EXIT="+(complete?"PASS":"NOT_PROVEN")
        +"\nSTATUS="+status
        +"\nFAILURE="+failure
        +"\nORIGINAL_DSH_ENGINEMANAGER_PATCHED=NO"
        +"\nREAL_DSH_CHAT_BROWSER_FILES_TESTED=NO"
        +"\nORIGINAL_FIXED_SIGNING_KEY_USED=NO"
        +"\nV139_RELEASE=BLOCKED"
        +"\n\n此程序独立安装，不替换原版 DSH。");
  }
  private void fail(String code) {
    if(complete||failed)return;
    failed=true;failure=code;status="STOPPED_FAIL_CLOSED";
    if(proxy!=null)proxy.onTransportLost();
    stop.setEnabled(false);
    render();
  }
  private void control(int what) {
    if(isolated==null||session==null)throw new IllegalStateException("NO_BINDER");
    Message m=Message.obtain(null,what);Bundle b=new Bundle();
    b.putString("session",session);m.setData(b);
    try{isolated.send(m);}catch(Exception e){throw new IllegalStateException("IPC_SEND_FAILED",e);}
  }
  private void collect(InputStream input,AtomicReference<String> destination){
    try(InputStream stream=input;ByteArrayOutputStream out=new ByteArrayOutputStream()){
      byte[] buf=new byte[256];int n;
      while((n=stream.read(buf))!=-1){
        if(out.size()+n>1024)throw new IOException("OUTPUT_LIMIT");
        out.write(buf,0,n);
      }
      destination.set(new String(out.toByteArray(),StandardCharsets.UTF_8));
    }catch(Exception e){destination.set("COLLECTION_ERROR");}
    finally{readers.countDown();}
  }
  private void verifyAfterExit(final int reportedExit) {
    new Thread(()->{
      boolean finished=false;
      try{finished=readers.await(3,TimeUnit.SECONDS);}
      catch(InterruptedException interrupted){Thread.currentThread().interrupt();}
      final boolean done=finished;
      main.post(()->{
        if(failed||complete)return;
        String expected="UID="+workerUid+"\nBOOT\nREADY\n";
        if(!done||reportedExit!=0||proxy==null||
           proxy.terminalReason()!=P37RemoteProcess.TerminalReason.REMOTE_EXIT||
           !expected.equals(stdout.get())||!"P38-STDERR\n".equals(stderr.get())) {
          fail("ORIGINAL_NODE_STDOUT_STDERR_EXIT_CONTRACT_FAILED");return;
        }
        complete=true;status="REAL_NODE_STREAM_EXIT_AND_PROXY_EOF_VERIFIED";
        stop.setEnabled(false);render();
      });
    },"p38-verify").start();
  }
  private final Messenger incoming=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message m) {
      if(failed||complete)return;
      int sender=m.sendingUid;
      if(!android.os.Process.isIsolatedUid(sender)||sender==android.os.Process.myUid()||
         (workerUid!=-1&&sender!=workerUid)) {
        fail("BINDER_SENDER_NOT_ISOLATED_OR_CHANGED");return;
      }
      if(m.what==P38NodeWorker.HELLO){
        if(workerUid!=-1||proxy!=null||isolated==null) {
          fail("UNSOLICITED_OR_DUPLICATE_HELLO");return;
        }
        workerUid=sender;session=newSession();expectedSeq=1;
        proxy=new P37RemoteProcess(workerUid,session,
            android.os.Process::isIsolatedUid,new P37RemoteProcess.RemoteControl(){
              @Override public void requestGracefulStop(){control(P38NodeWorker.STOP);}
              @Override public void requestForceStop(){control(P38NodeWorker.KILL);}
            });
        new Thread(()->collect(proxy.getInputStream(),stdout),"p38-host-stdout-reader").start();
        new Thread(()->collect(proxy.getErrorStream(),stderr),"p38-host-stderr-reader").start();
        Message reply=Message.obtain(null,P38NodeWorker.SESSION);
        Bundle b=new Bundle();b.putString("session",session);reply.setData(b);
        try{isolated.send(reply);}catch(Exception e){fail("SESSION_SEND_FAILED");return;}
        status="ORIGINAL_NODE_START_REQUESTED";render();return;
      }
      if(proxy==null||session==null||sender!=workerUid) {
        fail("NO_AUTHENTICATED_SESSION");return;
      }
      final Bundle b;
      try{b=m.getData();}catch(RuntimeException e){fail("MALFORMED_BINDER_PARCEL");return;}
      if(!session.equals(b.getString("session"))||b.getLong("seq",-1)!=expectedSeq) {
        fail("SESSION_OR_FRAME_SEQUENCE_MISMATCH");return;
      }
      expectedSeq++;
      if(m.what==P38NodeWorker.STDOUT||m.what==P38NodeWorker.STDERR){
        byte[] frame=b.getByteArray("data");
        if(frame==null||frame.length==0||frame.length>512||
           !(m.what==P38NodeWorker.STDOUT?
              proxy.onAuthenticatedStdout(sender,session,frame):
              proxy.onAuthenticatedStderr(sender,session,frame))) {
          fail("STREAM_FRAME_REJECTED");return;
        }
        status="VERIFIED_REMOTE_STREAM_RECEIVING";render();
      }else if(m.what==P38NodeWorker.EXIT){
        int code=b.getInt("exitCode",125);
        if(!proxy.onAuthenticatedExit(sender,session,code)){
          fail("REMOTE_EXIT_REJECTED");return;
        }
        status="AUTHENTICATED_CHILD_EXIT";render();
        verifyAfterExit(code);
      }else if(m.what==P38NodeWorker.FAIL) {
        fail("ISOLATED_WORKER_OR_NODE_REPORTED_FAILURE");
      }else fail("UNKNOWN_BINDER_OPERATION");
    }
  });
  private final ServiceConnection connection=new ServiceConnection(){
    @Override public void onServiceConnected(ComponentName name,IBinder binder){
      isolated=new Messenger(binder);
      Message init=Message.obtain(null,P38NodeWorker.INIT);
      init.replyTo=incoming;
      try{isolated.send(init);}catch(Exception e){fail("INIT_SEND_FAILED");}
    }
    @Override public void onServiceDisconnected(ComponentName name){
      isolated=null;if(!complete)fail("BINDER_SERVICE_DISCONNECTED");
    }
    @Override public void onBindingDied(ComponentName name){
      isolated=null;if(!complete)fail("BINDER_DIED");
    }
    @Override public void onNullBinding(ComponentName name){
      isolated=null;fail("NULL_BINDING");
    }
  };
  @Override public void onCreate(Bundle state){
    super.onCreate(state);
    LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);
    root.setPadding(18,18,18,18);
    report=new TextView(this);report.setTextSize(14);
    ScrollView scroll=new ScrollView(this);scroll.addView(report);
    root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
    start=new Button(this);start.setText("启动原版 Node → 进程代理测试");root.addView(start);
    stop=new Button(this);stop.setText("终止隔离 Node");stop.setEnabled(false);root.addView(stop);
    Button copy=new Button(this);copy.setText("复制脱敏状态报告");root.addView(copy);
    setContentView(root);render();
    start.setOnClickListener(v->{
      if(started)return;
      started=true;start.setEnabled(false);stop.setEnabled(true);
      status="BINDING_ISOLATED_WORKER";render();
      bound=bindService(new Intent(this,P38NodeWorker.class),connection,Context.BIND_AUTO_CREATE);
      if(!bound)fail("BIND_SERVICE_FAILED");
    });
    stop.setOnClickListener(v->{
      if(proxy!=null&&proxy.isAlive()){
        proxy.destroy();status="STOP_REQUESTED_WAITING_FOR_REAL_ACK";render();
        main.postDelayed(()->{
          if(proxy!=null&&proxy.isAlive()&&!failed&&!complete){
            proxy.destroyForcibly();proxy.onStopDeadlineExpired();
            fail("STOP_DEADLINE_EXPIRED");
          }
        },2000);
      }
    });
    copy.setOnClickListener(v->{
      ClipboardManager clip=(ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
      if(clip!=null)clip.setPrimaryClip(ClipData.newPlainText("P38 status",report.getText()));
    });
  }
  @Override protected void onStop(){
    if(started&&!complete&&!failed) {
      if(proxy!=null)proxy.destroyForcibly();
      fail("TRUSTED_HOST_BACKGROUND_REVOKES_SESSION");
    }
    super.onStop();
  }
  @Override protected void onDestroy(){
    if(proxy!=null&&proxy.isAlive())proxy.destroyForcibly();
    if(bound)unbindService(connection);
    super.onDestroy();
  }
}
