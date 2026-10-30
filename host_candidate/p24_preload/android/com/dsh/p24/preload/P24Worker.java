package com.dsh.p24.preload;
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
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/** A fixed two-run experiment: same extracted immutable native executable
 * without LD_PRELOAD, then with only its exact packaged libp24version.so.
 * Never accepts arbitrary commands, files, shell, network or real Node scripts.
 */
public final class P24Worker extends Service{
  private static final String TAG="DSH_P24_SONAME";
  private static final class Trial{
    final int exit;
    final String output;
    Trial(int code,String text){exit=code;output=text;}
  }
  private static Trial run(File executable, File alias, boolean preload)throws Exception{
    java.lang.Process child=null;
    try{
      ProcessBuilder request=new ProcessBuilder(executable.getAbsolutePath(),"--version");
      request.redirectErrorStream(true);
      request.directory(new File("/"));
      Map<String,String> env=request.environment();
      env.clear();
      env.put("PATH","/system/bin");
      env.put("HOME","/");
      env.put("LD_LIBRARY_PATH",executable.getParent());
      if(preload)env.put("LD_PRELOAD",alias.getAbsolutePath());
      child=request.start();
      if(!child.waitFor(12,TimeUnit.SECONDS))
        throw new IllegalStateException("native experiment timed out");
      // Static disposable C binary; output is tightly bounded and not logged.
      InputStream stream=child.getInputStream();
      byte[] bytes=new byte[1024];int total=0;
      while(total<bytes.length){
        int n=stream.read(bytes,total,bytes.length-total);
        if(n<0)break;
        total+=n;
      }
      return new Trial(child.exitValue(),
          new String(bytes,0,total,StandardCharsets.UTF_8));
    }finally{
      if(child!=null && child.isAlive())child.destroyForcibly();
    }
  }
  private final Messenger api=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message request){
      if(request.what!=1 || request.replyTo==null || !Process.isIsolated() ||
          request.sendingUid!=getApplicationInfo().uid)return;
      final Messenger recipient=request.replyTo;
      new Thread(()->{
        boolean aliasInstalled=false,negative=false,positive=false;
        int badExit=-99,goodExit=-99;
        String stage="GET_PACKAGE_MANAGED_DIR";
        try{
          File nativeDir=new File(getApplicationInfo().nativeLibraryDir);
          File executable=new File(nativeDir,"libp24exec.so");
          File alias=new File(nativeDir,"libp24version.so");
          File versioned=new File(nativeDir,"libp24version.so.3");
          aliasInstalled=nativeDir.isDirectory()&&executable.isFile()&&
              executable.canExecute() && alias.isFile() && alias.canRead() &&
              !versioned.exists();
          if(!aliasInstalled)throw new IllegalStateException("alias layout invalid");
          stage="RUN_NEGATIVE_CONTROL_NO_PRELOAD";
          Trial baseline=run(executable,alias,false);
          badExit=baseline.exit;
          negative=baseline.exit!=0 &&
              baseline.output.contains("CANNOT LINK EXECUTABLE") &&
              baseline.output.contains("libp24version.so.3");
          stage="RUN_POSITIVE_CONTROL_WITH_PRELOAD";
          Trial loaded=run(executable,alias,true);
          goodExit=loaded.exit;
          positive=loaded.exit==0 && loaded.output.trim().equals(
              "P24_REAL_SONAME_DEPENDENCY_UID="+Process.myUid());
          if(!negative)Log.e(TAG,"P24_NEGATIVE_CONTROL_DIAGNOSTIC_UNEXPECTED=FAIL");
          if(!positive){
            Log.e(TAG,"P24_PRELOAD_DIAGNOSTIC_LINK_ERROR="+
                loaded.output.contains("CANNOT LINK EXECUTABLE"));
            Log.e(TAG,"P24_PRELOAD_DIAGNOSTIC_MENTIONS_SONAME="+
                loaded.output.contains("libp24version.so.3"));
            Log.e(TAG,"P24_PRELOAD_DIAGNOSTIC_MENTIONS_NOT_FOUND="+
                loaded.output.contains("not found"));
          }
        }catch(Exception error){
          Log.e(TAG,"P24_STAGE_"+stage+"="+error.getClass().getSimpleName());
        }
        Bundle info=new Bundle();
        info.putInt("uid",Process.myUid());
        info.putBoolean("isolated",Process.isIsolated());
        info.putBoolean("extractedAlias",aliasInstalled);
        info.putBoolean("negativeControl",negative);
        info.putBoolean("preloadSuccess",positive);
        info.putInt("negativeExit",badExit);
        info.putInt("positiveExit",goodExit);
        Message response=Message.obtain(null,1);
        response.setData(info);
        try{recipient.send(response);}catch(Exception ignored){}
      },"p24-extracted-soname-preload-pair").start();
    }
  });
  @Override public IBinder onBind(Intent intent){
    if(!Process.isIsolated())throw new SecurityException("isolated UID required");
    return api.getBinder();
  }
}
