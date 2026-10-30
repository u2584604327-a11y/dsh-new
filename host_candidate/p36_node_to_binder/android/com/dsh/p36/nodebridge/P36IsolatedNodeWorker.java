package com.dsh.p36.nodebridge;

import android.app.Service;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.Process;
import android.util.Log;
import com.dsh.p32.P32AndroidBinderPort;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * P36 actual ORIGINAL SHA-pinned ARM64 Node -> Worker -> platform Messenger
 * -> P32 trusted UI one-shot broker. NEVER the installed DSH engine.
 * Fixed only: no arbitrary code/script, file, user data, network or tooling.
 */
public final class P36IsolatedNodeWorker extends Service {
  static final int INIT=991;
  private static final String TAG="P36_NODE_BRIDGE";
  private static final String EXEC="libdshnode_p21_exec.so";
  private static final String ORIGINAL_NODE_SHA =
      "a0d21a1589312919114b24a5cc520c30ab7f26f9985b3f0c643c153172ebd1e6";
  private static final String ORIGINAL_SIGNED_APK_SHA =
      "3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5";
  private static final int MAX_LIBS=10;
  private static final String CANONICAL="{\"op\":\"METADATA_COUNT\",\"limit\":3}";
  // THIS is what the original native Node executes, not Java synthetic frame.
  private static final String FIXED_JS =
      "process.stdout.write('UID='+process.getuid()+'\\n'"
      +"+JSON.stringify({op:'METADATA_COUNT',limit:3})+'\\n');";
  private final Handler main=new Handler(Looper.getMainLooper());
  private Messenger host=null;
  private Messenger statusInbox=null;
  private int hostUid=-1, phase=0,childUid=-1;
  private String session=null,token=null,verifiedNodeFrame=null;
  private volatile boolean originalHashes=false,nodeUidMatch=false;
  private volatile java.lang.Process nodeProcess=null;
  private boolean began=false;
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
  private void status(String state) {
    if(statusInbox==null)return;
    Bundle b=new Bundle();
    b.putString("state",state);
    b.putInt("workerUid",Process.myUid());
    b.putInt("childUid",childUid);
    b.putBoolean("allHashes",originalHashes);
    b.putBoolean("childMatch",nodeUidMatch);
    Message m=Message.obtain(null,202);
    m.setData(b);
    try{statusInbox.send(m);}catch(Exception ignored){}
  }
  private void runVerifiedOriginalNode() {
    java.lang.Process p=null;
    try {
      if(!Process.isIsolated()||Build.VERSION.SDK_INT<34 ||
         !Arrays.asList(Build.SUPPORTED_ABIS).contains("arm64-v8a"))
        throw new SecurityException("P36_REQUIRES_REAL_ANDROID_ARM64_ISOLATED_UID");
      if(checkSelfPermission(android.Manifest.permission.INTERNET)
            ==PackageManager.PERMISSION_GRANTED)
        throw new SecurityException("P36_NO_INTERNET_PERMITTED");
          File directory=new File(getApplicationInfo().nativeLibraryDir).getCanonicalFile();
          if(!directory.isDirectory())throw new IllegalStateException("NATIVE_DIR_ABSENT");
          File executable=new File(directory,EXEC).getCanonicalFile();
          if(!directory.equals(executable.getParentFile()) ||
              !executable.canExecute())
            throw new SecurityException("EXECUTABLE_NOT_PACKAGE_INSTALLED");
          JSONObject lock=new JSONObject(readAsset(getAssets().open("p28-runtime-lock.json")));
          if(!"P28_EXACT_V138_NODE_SHA_PIN".equals(lock.getString("gate")) ||
             !ORIGINAL_SIGNED_APK_SHA.equals(lock.getString("source_apk_sha256")) ||
             !ORIGINAL_NODE_SHA.equals(lock.getString("node_sha256")))
            throw new SecurityException("PINNED_SOURCE_CHANGED");
          JSONArray libs=lock.getJSONArray("libs");
          JSONArray preload=lock.getJSONArray("preload");
          if(libs.length()!=MAX_LIBS || preload.length()!=6)
            throw new SecurityException("DEPENDENCY_COUNT_MISMATCH");
          if(!ORIGINAL_NODE_SHA.equals(hash(executable)))
            throw new SecurityException("NODE_SHA256_MISMATCH");
          Set<String> verifiedNames=new HashSet<>();
          for(int index=0;index<libs.length();index++){
            JSONObject record=libs.getJSONObject(index);
            String alias=record.getString("alias");
            String expected=record.getString("sha256");
            if(!safeName(alias) || !expected.matches("[a-f0-9]{64}") ||
               !verifiedNames.add(alias))
              throw new SecurityException("LIBRARY_ALIAS_OR_SHA_INVALID");
            File library=new File(directory,alias).getCanonicalFile();
            if(!directory.equals(library.getParentFile()) ||
               !expected.equals(hash(library)))
              throw new SecurityException("ORIGINAL_LIBRARY_SHA_MISMATCH");
          }
          StringBuilder preloadEnv=new StringBuilder();
          Set<String> preloadAliases=new HashSet<>();
          for(int index=0;index<preload.length();index++){
            String alias=preload.getString(index);
            if(!safeName(alias) || !verifiedNames.contains(alias) ||
               !preloadAliases.add(alias))
              throw new SecurityException("PRELOAD_MAP_INVALID");
            File dependency=new File(directory,alias).getCanonicalFile();
            if(!directory.equals(dependency.getParentFile()))
              throw new SecurityException("PRELOAD_OUTSIDE_IMMUTABLE_DIR");
            if(index>0)preloadEnv.append(':');
            preloadEnv.append(dependency.getAbsolutePath());
          }

      originalHashes=true;
      ProcessBuilder pb=new ProcessBuilder(executable.getAbsolutePath(),
          "--no-warnings","--eval",FIXED_JS);
      pb.redirectErrorStream(true);
      pb.directory(new File("/"));
      Map<String,String> environment=pb.environment();
      environment.clear();
      environment.put("PATH","/system/bin");
      environment.put("HOME","/");
      environment.put("LD_LIBRARY_PATH",directory.getAbsolutePath());
      environment.put("LD_PRELOAD",preloadEnv.toString());
      p=pb.start();
      nodeProcess=p;
      if(!p.waitFor(18,TimeUnit.SECONDS))
        throw new IllegalStateException("P36_NODE_START_TIMEOUT");
      if(p.exitValue()!=0)throw new IllegalStateException("P36_NODE_EXIT_NONZERO");
      String output=limitedProcessOutput(p.getInputStream());
      String[] lines=output.split("\\n",-1);
      if(lines.length!=2 || !lines[0].matches("UID=[0-9]{4,6}") ||
          !CANONICAL.equals(lines[1]))
        throw new SecurityException("P36_NODE_OUTPUT_NOT_CANONICAL");
      childUid=Integer.parseInt(lines[0].substring(4));
      nodeUidMatch=Process.myUid()==childUid;
      if(!nodeUidMatch)throw new SecurityException("P36_CHILD_NOT_WORKER_UID");
      verifiedNodeFrame=lines[1];
      main.post(()->{
        if(phase!=0||host==null||session==null)return;
        phase=1;
        status("ORIGINAL_NODE_FRAME_VERIFIED");
        try{sendRequest(null);}catch(Exception e){status("BLOCKED_BINDER_SEND");}
      });
    }catch(Exception | LinkageError failure){
      main.post(()->{phase=90;status("BLOCKED_NODE_OR_SHA_OR_UID");});
    }finally{
      if(p!=null && p.isAlive())p.destroyForcibly();
      nodeProcess=null;
    }
  }
  private void sendRequest(String grant)throws Exception{
    if(host==null||verifiedNodeFrame==null||
         !originalHashes||!nodeUidMatch)
      throw new IllegalStateException("NO_VERIFIED_ORIGINAL_NODE");
    Message q=Message.obtain(null,P32AndroidBinderPort.REQUEST);
    q.replyTo=workerInbox;
    Bundle b=new Bundle();
    b.putString("session",session);
    if(grant!=null)b.putString("grant",grant);
    // ONLY original Node stdout after exact SHA, child getuid and canonical parse.
    b.putString("nodeFrame",verifiedNodeFrame);
    q.setData(b);
    host.send(q);
  }
  private final Messenger workerInbox=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message m){
      try {
        if(m.what==INIT){
          if(began || host!=null || !Process.isIsolated() || m.replyTo==null ||
             Process.isIsolatedUid(m.sendingUid) ||
             m.sendingUid!=getApplicationInfo().uid)return;
          Bundle first=m.getData();
          IBinder statusBinder=first.getBinder("statusReceiver");
          if(statusBinder==null)return;
          statusInbox=new Messenger(statusBinder);
          began=true;
          hostUid=m.sendingUid;
          host=m.replyTo;
          Message hello=Message.obtain(null,P32AndroidBinderPort.HELLO);
          hello.replyTo=workerInbox;
          host.send(hello);
          return;
        }
        if(host==null||m.sendingUid!=hostUid)return;
        if(m.what==P32AndroidBinderPort.HELLO_REPLY){
          if(phase!=0)return;
          Bundle b=m.getData();
          if(!"BOUND_NOT_APPROVED".equals(b.getString("result")))return;
          session=b.getString("session");
          if(session==null||!session.matches("[a-f0-9]{64}"))return;
          new Thread(()->runVerifiedOriginalNode(),"p36-fixed-original-node").start();
        }else if(m.what==P32AndroidBinderPort.GRANT){
          if(phase!=2 || verifiedNodeFrame==null)return;
          Bundle b=m.getData();
          if(!session.equals(b.getString("session")) ||
             !"METADATA_COUNT".equals(b.getString("scope")))return;
          token=b.getString("grant");
          if(token==null||!token.matches("[a-f0-9]{64}"))return;
          phase=3;
          sendRequest(token);
        }else if(m.what==P32AndroidBinderPort.REQUEST_REPLY){
          String response=m.getData().getString("result","");
          if(phase==1){
            if(!"DENY_NO_GRANT".equals(response)){
              phase=90;status("BLOCKED_PREGRANT_RESULT");return;
            }
            phase=2;
            status("PREGRANT_DENIED");
          }else if(phase==3){
            if(!"ALLOW_COUNT".equals(response)||
                 m.getData().getInt("syntheticCount",-1)!=3){
              phase=90;status("BLOCKED_REAL_NODE_APPROVAL");return;
            }
            phase=4;
            status("ONE_APPROVED");
            sendRequest(token);
          }else if(phase==4){
            if(!"DENY_NO_GRANT".equals(response)){
              phase=90;status("BLOCKED_REPLAY_WAS_NOT_DENIED");return;
            }
            phase=5;
            status("REPLAY_DENIED_COMPLETE");
          }
        }
      }catch(Exception e){phase=90;status("BLOCKED_PROTOCOL_EXCEPTION");}
    }
  });
  @Override public IBinder onBind(Intent intent) {
    if(!Process.isIsolated())throw new SecurityException("P36_ISOLATED_ONLY");
    return workerInbox.getBinder();
  }
  @Override public void onDestroy(){
    java.lang.Process p=nodeProcess;
    if(p!=null&&p.isAlive())p.destroyForcibly();
    host=null;statusInbox=null;verifiedNodeFrame=null;token=null;session=null;
    super.onDestroy();
  }
}
