package com.dsh.p38.nodebridge;

import android.app.Service;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.json.JSONArray;
import org.json.JSONObject;

/** P38 bounded original ARM64 Node streaming probe in a separate test package.
 * Real DSH original EngineManager is NEVER patched or started here.
 */
public final class P38NodeWorker extends Service {
  static final int INIT=301, HELLO=302, SESSION=303, STDOUT=304,
      STDERR=305, EXIT=306, FAIL=307, STOP=308, KILL=309;
  private static final String EXEC="libdshnode_p21_exec.so";
  private static final String ORIGINAL_NODE_SHA =
      "a0d21a1589312919114b24a5cc520c30ab7f26f9985b3f0c643c153172ebd1e6";
  private static final String ORIGINAL_SIGNED_APK_SHA =
      "3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5";
  private static final int MAX_LIBS=10;
  private static final String JS =
      "process.stdout.write('UID='+process.getuid()+'\\n');"
      +"process.stderr.write('P38-STDERR\\n');"
      +"setTimeout(function(){process.stdout.write('BOOT\\n');"
      +"setTimeout(function(){process.stdout.write('READY\\n');},60);},60);";
  private final Object sendLock=new Object();
  private final Handler main=new Handler(Looper.getMainLooper());
  private Messenger host;
  private int hostUid=-1;
  private String session;
  private long sequence=0;
  private volatile java.lang.Process node;
  private volatile boolean aborted=false;
  private boolean initialized=false,launchStarted=false;

  private static boolean safeName(String s) {
    return s!=null && s.matches("lib[a-zA-Z0-9_.+-]{1,70}\\.so")
        && !s.contains("..") && s.indexOf('/')<0;
  }
  private static String hash(File f) throws Exception {
    if(!f.isFile() || !f.canRead() || f.length()<1000
        || f.length()>128L*1024*1024)
      throw new IllegalStateException("MISSING_OR_UNREASONABLE_ELF");
    MessageDigest digest=MessageDigest.getInstance("SHA-256");
    try(InputStream source=new FileInputStream(f)) {
      byte[] buffer=new byte[65536];int count;
      while((count=source.read(buffer))!=-1)digest.update(buffer,0,count);
    }
    StringBuilder out=new StringBuilder();
    for(byte b:digest.digest())out.append(String.format(Locale.ROOT,"%02x",b&255));
    return out.toString();
  }
  private static String readAsset(InputStream source)throws Exception{
    try(InputStream input=source;ByteArrayOutputStream out=new ByteArrayOutputStream()) {
      byte[] bytes=new byte[1024];int n;
      while((n=input.read(bytes))!=-1){
        if(out.size()+n>16384)throw new IllegalStateException("LOCK_OVERSIZED");
        out.write(bytes,0,n);
      }
      return new String(out.toByteArray(),StandardCharsets.UTF_8);
    }
  }

  private static String limitedProcessOutput(InputStream input)throws Exception {
    ByteArrayOutputStream out=new ByteArrayOutputStream();
    byte[] buf=new byte[512];int count;
    while((count=input.read(buf))!=-1){
      if(out.size()+count>256)throw new IllegalStateException("NODE_STDOUT_EXCESSIVE");
      out.write(buf,0,count);
    }
    return out.toString("UTF-8").trim();
  }

  private void send(int type,byte[] bytes,int exitCode) {
    synchronized(sendLock) {
      if(host==null||session==null||aborted)return;
      Bundle b=new Bundle();
      b.putString("session",session);
      b.putLong("seq",++sequence);
      if(bytes!=null)b.putByteArray("data",bytes);
      if(type==EXIT)b.putInt("exitCode",exitCode);
      Message out=Message.obtain(null,type);out.setData(b);
      try { host.send(out); } catch(Exception err) { aborted=true; }
    }
  }
  private void fatal(){
    java.lang.Process p=node;
    if(p!=null&&p.isAlive())p.destroyForcibly();
    send(FAIL,null,125);
  }
  private void pipe(InputStream input,int type,AtomicReference<String> failed) {
    try(InputStream source=input) {
      byte[] buffer=new byte[512];int n;long total=0;
      while((n=source.read(buffer))!=-1) {
        total+=n;
        if(total>2048){failed.compareAndSet(null,"STREAM_TOO_LONG");return;}
        if(n!=0)send(type,Arrays.copyOf(buffer,n),0);
        if(aborted)throw new IOException("IPC_DISCONNECTED");
      }
    }catch(Exception e){failed.compareAndSet(null,"PIPE_ERROR");}
  }
  private void runFixedOriginalNode(){
    java.lang.Process p=null;
    try {
      if(!android.os.Process.isIsolated()||Build.VERSION.SDK_INT<34||
          !Arrays.asList(Build.SUPPORTED_ABIS).contains("arm64-v8a"))
        throw new SecurityException("REQUIRES_ARM64_ISOLATED_UID");
      if(checkSelfPermission(android.Manifest.permission.INTERNET)
          ==PackageManager.PERMISSION_GRANTED)
        throw new SecurityException("NO_INTERNET");
      File dir=new File(getApplicationInfo().nativeLibraryDir).getCanonicalFile();
      if(!dir.isDirectory())throw new IOException("MISSING_NATIVE_DIR");
      File executable=new File(dir,EXEC).getCanonicalFile();
      if(!dir.equals(executable.getParentFile())||!executable.canExecute())
        throw new IOException("INVALID_IMMUTABLE_NODE");
      JSONObject lock=new JSONObject(readAsset(getAssets().open("p28-runtime-lock.json")));
      if(!"P28_EXACT_V138_NODE_SHA_PIN".equals(lock.getString("gate"))||
         !ORIGINAL_SIGNED_APK_SHA.equals(lock.getString("source_apk_sha256"))||
         !ORIGINAL_NODE_SHA.equals(lock.getString("node_sha256"))||
         !ORIGINAL_NODE_SHA.equals(hash(executable)))
        throw new SecurityException("NODE_LOCK_MISMATCH");
      JSONArray libs=lock.getJSONArray("libs"),preloads=lock.getJSONArray("preload");
      if(libs.length()!=MAX_LIBS||preloads.length()!=6)
        throw new SecurityException("LIB_COUNT_MISMATCH");
      Set<String> verified=new HashSet<>();
      for(int i=0;i<libs.length();i++){
        JSONObject record=libs.getJSONObject(i);
        String name=record.getString("alias"),expected=record.getString("sha256");
        if(!safeName(name)||!expected.matches("[a-f0-9]{64}")||!verified.add(name))
          throw new SecurityException("LIB_ALIAS_INVALID");
        File f=new File(dir,name).getCanonicalFile();
        if(!dir.equals(f.getParentFile())||!expected.equals(hash(f)))
          throw new SecurityException("LIB_HASH_MISMATCH");
      }
      StringBuilder preloadEnv=new StringBuilder();
      Set<String> preloadSeen=new HashSet<>();
      for(int i=0;i<preloads.length();i++){
        String name=preloads.getString(i);
        if(!safeName(name)||!verified.contains(name)||!preloadSeen.add(name))
          throw new SecurityException("PRELOAD_INVALID");
        if(i>0)preloadEnv.append(':');
        preloadEnv.append(new File(dir,name).getAbsolutePath());
      }
      ProcessBuilder builder=new ProcessBuilder(executable.getAbsolutePath(),
          "--no-warnings","--eval",JS);
      builder.directory(new File("/"));
      Map<String,String> env=builder.environment();env.clear();
      env.put("PATH","/system/bin");env.put("HOME","/");
      env.put("LD_LIBRARY_PATH",dir.getAbsolutePath());
      env.put("LD_PRELOAD",preloadEnv.toString());
      p=builder.start();node=p;
      AtomicReference<String> failed=new AtomicReference<>();
      final java.lang.Process child=p;
      Thread out=new Thread(()->pipe(child.getInputStream(),STDOUT,failed),"p38-node-stdout");
      Thread err=new Thread(()->pipe(child.getErrorStream(),STDERR,failed),"p38-node-stderr");
      out.start();err.start();
      boolean terminated=p.waitFor(18,TimeUnit.SECONDS);
      if(!terminated){p.destroyForcibly();failed.compareAndSet(null,"TIMEOUT");}
      out.join(3000);err.join(3000);
      if(out.isAlive()||err.isAlive()||failed.get()!=null||aborted||!terminated)
        throw new IOException("STREAM_OR_TIMEOUT_FAILED");
      send(EXIT,null,p.exitValue());
    }catch(Exception | LinkageError failure){
      fatal();
    }finally {
      if(p!=null&&p.isAlive())p.destroyForcibly();
      node=null;
    }
  }
  private final Messenger inbox=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message m){
      if(m.what==INIT){
        if(initialized||host!=null||!android.os.Process.isIsolated()||
           m.replyTo==null||m.sendingUid!=getApplicationInfo().uid)return;
        initialized=true;hostUid=m.sendingUid;host=m.replyTo;
        Message reply=Message.obtain(null,HELLO);
        try{host.send(reply);}catch(Exception e){host=null;}
        return;
      }
      if(host==null||m.sendingUid!=hostUid)return;
      if(m.what==SESSION){
        if(launchStarted)return;
        String proposed=m.getData().getString("session");
        if(proposed==null||!proposed.matches("[a-f0-9]{64}"))return;
        session=proposed;launchStarted=true;
        new Thread(()->runFixedOriginalNode(),"p38-original-node").start();
      }else if(m.what==STOP||m.what==KILL){
        if(session==null||!session.equals(m.getData().getString("session")))return;
        java.lang.Process p=node;
        if(p!=null&&p.isAlive()){
          if(m.what==KILL)p.destroyForcibly();else p.destroy();
        }
      }
    }
  });
  @Override public IBinder onBind(Intent intent){
    if(!android.os.Process.isIsolated())throw new SecurityException("ISOLATED_ONLY");
    return inbox.getBinder();
  }
  @Override public void onDestroy(){
    aborted=true;
    java.lang.Process p=node;
    if(p!=null&&p.isAlive())p.destroyForcibly();
    host=null;session=null;
    super.onDestroy();
  }
}
