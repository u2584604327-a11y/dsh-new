package com.dsh.p23.zipcontrol;
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
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/** P23: own disposable APK ZipFile positive control followed by three
 * identical-ELF direct Bionic ZIP loading experiments in an isolated UID.
 * Absolutely no production DSH/Node, network, shell, arbitrary file or URL.
 */
public final class P23ControlWorker extends Service {
  private static final String TAG="DSH_P23_ZIP";
  private static native int probeNativeZipDlopen(String ownApk, int which);
  private static final String[] ENTRIES={
      "assets/p23control.so",
      "assets/p23control.so.3",
      "lib/x86_64/libp22version.so.3"};
  private static byte[] entrySha(ZipFile zip, String name)throws Exception{
    ZipEntry e=zip.getEntry(name);
    if(e==null || e.getMethod()!=ZipEntry.STORED ||
       e.getSize()<4096 || e.getSize()>1024*1024)return null;
    MessageDigest sha=MessageDigest.getInstance("SHA-256");
    long bytes=0;
    try(InputStream in=zip.getInputStream(e)){
      byte[] block=new byte[8192];int n;
      while((n=in.read(block))!=-1){
        if(bytes==0 && (n<4 || block[0]!=0x7f || block[1]!='E' ||
                        block[2]!='L' || block[3]!='F'))return null;
        sha.update(block,0,n);
        bytes+=n;
        if(bytes>1024*1024)return null;
      }
    }
    return bytes==e.getSize()?sha.digest():null;
  }
  private final Messenger service=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message request){
      if(request.what!=1 || request.replyTo==null ||
         !Process.isIsolated() || request.sendingUid!=getApplicationInfo().uid)return;
      final Messenger response=request.replyTo;
      new Thread(()->{
        boolean readable=false,entries=false,bridge=false;
        int first=-100,second=-100,third=-100;
        String stage="VALIDATE_OWN_APK_PATH";
        try{
          String apk=getApplicationInfo().sourceDir;
          if(apk==null || !apk.endsWith(".apk"))
            throw new IllegalStateException("invalid platform sourceDir");
          File source=new File(apk);
          readable=source.isFile()&&source.canRead();
          if(readable){
            stage="VERIFY_ALL_THREE_ZIP_ENTRIES_AND_BYTES";
            try(ZipFile zip=new ZipFile(source)){
              byte[][] all=new byte[3][];
              for(int i=0;i<3;i++)all[i]=entrySha(zip,ENTRIES[i]);
              entries=all[0]!=null && all[1]!=null && all[2]!=null &&
                      Arrays.equals(all[0],all[1]) &&
                      Arrays.equals(all[1],all[2]);
            }
          }
          if(!readable || !entries)
            throw new IllegalStateException("own APK unavailable/inconsistent");
          stage="LOAD_INSTALLED_NATIVE_JNI_BRIDGE";
          System.loadLibrary("p23bridge");
          bridge=true;
          stage="DLOPEN_ALL_THREE_IDENTICAL_ELF_PATHS";
          first=probeNativeZipDlopen(apk,1);
          second=probeNativeZipDlopen(apk,2);
          third=probeNativeZipDlopen(apk,3);
        }catch(UnsatisfiedLinkError | SecurityException error){
          Log.e(TAG,"P23_STAGE_"+stage+"="+error.getClass().getSimpleName());
        }catch(Exception error){
          Log.e(TAG,"P23_STAGE_"+stage+"="+error.getClass().getSimpleName());
        }
        Bundle result=new Bundle();
        result.putBoolean("zipReadable",readable);
        result.putBoolean("allEntriesReadable",entries);
        result.putBoolean("bridgeLoaded",bridge);
        result.putBoolean("isolated",Process.isIsolated());
        result.putInt("uid",Process.myUid());
        result.putInt("assetShort",first);
        result.putInt("assetVersion",second);
        result.putInt("nativeVersion",third);
        Message reply=Message.obtain(null,1);reply.setData(result);
        try{response.send(reply);}catch(Exception ignored){}
      },"p23-own-apk-zip-load-controls").start();
    }
  });
  @Override public IBinder onBind(Intent intent){
    if(!Process.isIsolated())throw new SecurityException("worker requires isolatedProcess");
    return service.getBinder();
  }
}
