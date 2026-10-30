package com.dsh.p21.probe;
import android.app.Service;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.Process;
import android.util.Log;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/** P21 standalone proof only. Runs SHA-pinned original ARM64 Node with --version.
 * No scripts, shell, arbitrary args, tool plugins, credentials, or file/URL broker.
 * This class is not yet integrated with original com.dsh.android.
 */
public final class P21RealNodeService extends Service {
  private static final String TAG="DSH_P21_NODE";
  private static final String EXEC_NAME="libdshnode_p21_exec.so";
  private static final String EXPECTED_SHA=
      "a0d21a1589312919114b24a5cc520c30ab7f26f9985b3f0c643c153172ebd1e6";
  private static boolean verified(File candidate)throws Exception{
    MessageDigest h=MessageDigest.getInstance("SHA-256");
    try(InputStream stream=new FileInputStream(candidate)){
      byte[] block=new byte[65536];int n;
      while((n=stream.read(block))!=-1)h.update(block,0,n);
    }
    StringBuilder text=new StringBuilder();
    for(byte b:h.digest())text.append(String.format(Locale.ROOT,"%02x",b&0xff));
    return EXPECTED_SHA.equals(text.toString());
  }
  private final Messenger inbox=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message request){
      if(request.what!=1 || request.replyTo==null || !Process.isIsolated())return;
      // Only the installed application's normal host UID may drive the worker.
      if(request.sendingUid!=getApplicationInfo().uid)return;
      final Messenger recipient=request.replyTo;
      new Thread(()->{
        boolean pinned=false,worked=false;
        String stage="VERIFY_INSTALLER_NATIVE_DIR";
        java.lang.Process child=null;
        try{
          File nativeDir=new File(getApplicationInfo().nativeLibraryDir);
          File node=new File(nativeDir,EXEC_NAME);
          if(!nativeDir.isDirectory() || !node.isFile() || !node.canExecute())
            throw new IllegalStateException("Native executable not installer extracted");
          stage="VERIFY_ORIGINAL_NODE_SHA256";
          pinned=verified(node);
          if(!pinned)throw new SecurityException("unexpected binary bytes");
          stage="START_ORIGINAL_NODE_VERSION_ONLY";
          ProcessBuilder pb=new ProcessBuilder(node.getAbsolutePath(),"--version");
          pb.redirectErrorStream(true);
          pb.directory(new File("/"));
          Map<String,String> env=pb.environment();
          env.clear();
          env.put("PATH","/system/bin");
          // Android Bionic can resolve uncompressed/page-aligned ELF from
          // APK ZIP paths, but this is an UNVERIFIED candidate for execve
          // plus DT_NEEDED versioned sonames in an isolated UID.
          String apkLibrarySearch=getApplicationInfo().sourceDir+"!/lib/arm64-v8a";
          env.put("LD_LIBRARY_PATH",
              nativeDir.getAbsolutePath()+":"+apkLibrarySearch);
          env.put("HOME","/");
          child=pb.start();
          stage="WAIT_FOR_NODE_EXIT";
          if(!child.waitFor(15,TimeUnit.SECONDS))
            throw new IllegalStateException("Node not exited");
          int exit=child.exitValue();
          // Bounded output. No environment/command echo in the report.
          InputStream output=child.getInputStream();
          byte[] buffer=new byte[128];int size=output.read(buffer);
          String version=size<0?"":new String(buffer,0,size,
              java.nio.charset.StandardCharsets.UTF_8).trim();
          worked=exit==0 && version.matches("v[0-9]+\\.[0-9]+\\.[0-9]+(\\.[0-9]+)?");
          if(!worked)Log.e(TAG,"P21_NODE_VERSION_EXIT_OR_FORMAT=FAIL");
        }catch(Exception error){
          Log.e(TAG,"P21_REAL_ELF_STAGE_"+stage+"="+error.getClass().getSimpleName());
        }finally{
          if(child!=null && child.isAlive())child.destroyForcibly();
        }
        Bundle payload=new Bundle();
        payload.putInt("uid",Process.myUid());
        payload.putBoolean("isolated",Process.isIsolated());
        payload.putBoolean("originalShaPinned",pinned);
        payload.putBoolean("originalNodeVersionRecognized",worked);
        Message response=Message.obtain(null,1);
        response.setData(payload);
        try{recipient.send(response);}catch(Exception ignored){}
      },"p21-actual-node-version").start();
    }
  });
  @Override public IBinder onBind(Intent intent){
    if(!Process.isIsolated())throw new SecurityException("Isolated worker only");
    return inbox.getBinder();
  }
}
