package com.dsh.android.p48;

import android.os.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.concurrent.TimeUnit;

/**
 * P48 tightly-scoped ORIGINAL-APK isolated child-process proof only.
 * Runs a hardcoded Android /system/bin/id -u, never DSH production Node.
 * Inputs cannot influence executable, argv, cwd, env, permissions, or files.
 */
public final class P48FixedIsolatedChild {
  public static final int START=481, HELLO=482, STDOUT=483, STDERR=484,
      EXIT=485, FAIL=486, STOP=487, KILL=488, CHILD_STARTED=489;
  private final Messenger host;
  private final String session;
  private long sequence;
  private volatile java.lang.Process child;
  private volatile boolean stopped;

  public P48FixedIsolatedChild(Messenger host,String session) {
    if(host==null || session==null || !session.matches("[a-f0-9]{64}") ||
       !android.os.Process.isIsolated())
      throw new IllegalArgumentException("P48_TRUSTED_ISOLATED_ONLY");
    this.host=host;this.session=session;
  }
  private synchronized void emit(int what,byte[] bytes,int code){
    if(stopped && what!=EXIT && what!=FAIL)return;
    Message msg=Message.obtain(null,what);
    Bundle b=new Bundle();b.putString("session",session);
    b.putLong("seq",what==HELLO ? 0 : ++sequence);
    if(bytes!=null)b.putByteArray("data",bytes);
    if(what==EXIT)b.putInt("exitCode",code);
    msg.setData(b);
    try{host.send(msg);}catch(RemoteException e){
      stopped=true;
      java.lang.Process p=child;
      if(p!=null)p.destroyForcibly();
    }
  }
  public void start(){
    emit(HELLO,null,0);
    Thread t=new Thread(this::runExactFixture,"p48-fixed-isolated-child");
    t.setDaemon(true);t.start();
  }
  public void stop(boolean kill){
    stopped=true;
    java.lang.Process p=child;
    if(p!=null){
      if(kill)p.destroyForcibly();else p.destroy();
    }
  }
  private static byte[] readUpTo(InputStream source,int limit)throws IOException {
    try(InputStream in=source;ByteArrayOutputStream out=new ByteArrayOutputStream()){
      byte[] buf=new byte[128];int n;
      while((n=in.read(buf))!=-1) {
        if(n>limit-out.size())throw new IOException("P48_STREAM_BOUND");
        if(n>0)out.write(buf,0,n);
      }
      return out.toByteArray();
    }
  }
  private void runExactFixture(){
    java.lang.Process p=null;
    try {
      if(!android.os.Process.isIsolated())
        throw new SecurityException("P48_ISOLATED_UID_REQUIRED");
      // Fixed synthetic POSIX UID witness, NOT a general command API.
      p=new ProcessBuilder("/system/bin/id","-u")
          .directory(new File("/")).start();
      child=p;
      if(stopped){p.destroyForcibly();throw new IOException("P48_STOP_BEFORE_EXEC");}
      // P53: irreversible ordering: Binder HELLO is only a session
      // greeting, never a claim that ProcessBuilder.start() succeeded.
      emit(CHILD_STARTED,null,0);
      // /system/bin/id emits a short UID and no stderr. waitFor is bounded
      // before draining; this executable never outputs more than 128 bytes.
      if(!p.waitFor(8,TimeUnit.SECONDS)) {
        p.destroyForcibly();throw new IOException("P48_CHILD_TIMEOUT");
      }
      byte[] out=readUpTo(p.getInputStream(),128);
      byte[] err=readUpTo(p.getErrorStream(),128);
      if(stopped)throw new IOException("P48_ABORTED");
      if(out.length==0||out.length>128)throw new IOException("P48_NO_UID");
      String s=new String(out,StandardCharsets.US_ASCII).trim();
      if(!s.matches("[0-9]{1,10}") ||
         !s.equals(Integer.toString(android.os.Process.myUid())))
        throw new IOException("P48_CHILD_UID_MISMATCH");
      emit(STDOUT,out,0);
      if(err.length>0)emit(STDERR,err,0);
      emit(EXIT,null,p.exitValue());
    }catch(Exception e){
      emit(FAIL,null,125);
    }finally {
      if(p!=null&&p.isAlive())p.destroyForcibly();
      child=null;
    }
  }
}
