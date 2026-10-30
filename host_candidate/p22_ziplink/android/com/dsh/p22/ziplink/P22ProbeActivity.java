package com.dsh.p22.ziplink;
import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.Process;
import android.util.Log;
import android.widget.TextView;

/** Disposable emulator proof, never a DSH product class. */
public final class P22ProbeActivity extends Activity {
  private static final String TAG="DSH_P22_ZIPLINK";
  private boolean bound=false;
  private final Messenger receive=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message m){
      if(m.what!=1)return;
      boolean fromIsolated=Process.isIsolatedUid(m.sendingUid)
          && m.sendingUid!=Process.myUid();
      Bundle b;
      try {b=m.getData();} catch(RuntimeException bad){
        Log.e(TAG,"P22_UNPARSABLE_WORKER_REPLY=FAIL");return;
      }
      boolean verified=fromIsolated && b.getBoolean("isolated",false)
          && b.getInt("uid",-1)==m.sendingUid;
      if(verified)Log.i(TAG,"P22_BINDER_FRAMEWORK_ISOLATED_UID=PASS");
      else Log.e(TAG,"P22_BINDER_FRAMEWORK_ISOLATED_UID=FAIL");
      if(verified && b.getBoolean("apkExec",false))
        Log.i(TAG,"P22_EXEC_PACKAGE_EXTRACTED_ELF=PASS");
      else Log.e(TAG,"P22_EXEC_PACKAGE_EXTRACTED_ELF=FAIL");
      if(verified && b.getBoolean("directZipDlopen",false))
        Log.i(TAG,"P22_DIRECT_BIONIC_VERSIONED_ZIP_DLOPEN=PASS");
      else Log.e(TAG,"P22_DIRECT_BIONIC_VERSIONED_ZIP_DLOPEN=FAIL");
      if(verified && b.getBoolean("nativeZipDlopen",false))
        Log.i(TAG,"P22_NATIVE_BIONIC_VERSIONED_ZIP_DLOPEN=PASS");
      else Log.e(TAG,"P22_NATIVE_BIONIC_VERSIONED_ZIP_DLOPEN=FAIL");
      if(verified && b.getBoolean("versionedLibrary",false))
        Log.i(TAG,"P22_EXEC_VERSIONED_SONAME_FROM_APK_ZIP=PASS");
      else Log.e(TAG,"P22_EXEC_VERSIONED_SONAME_FROM_APK_ZIP=FAIL");
      Log.i(TAG,"P22_REAL_ARM64_NODE_EXECUTED=NO");
      Log.i(TAG,"P22_DSH_PRODUCTION_RUNTIME_MIGRATED=NO");
    }
  });
  private final ServiceConnection service=new ServiceConnection(){
    @Override public void onServiceConnected(ComponentName cn,IBinder binder){
      try {Message m=Message.obtain(null,1);m.replyTo=receive;
        new Messenger(binder).send(m);
      }catch(Exception fail){Log.e(TAG,"P22_BINDER_IPC=FAIL");}
    }
    @Override public void onServiceDisconnected(ComponentName cn){
      Log.i(TAG,"P22_TEST_SERVICE_DISCONNECTED=YES");
    }
  };
  @Override public void onCreate(Bundle state){
    super.onCreate(state);
    TextView label=new TextView(this);label.setText("P22 dynamic loader OS test");
    setContentView(label);
    bound=bindService(new Intent(this,P22ZipLinkWorker.class),
        service,Context.BIND_AUTO_CREATE);
    if(!bound)Log.e(TAG,"P22_TEST_BIND=FAIL");
  }
  @Override public void onDestroy(){
    if(bound)unbindService(service);
    super.onDestroy();
  }
}
