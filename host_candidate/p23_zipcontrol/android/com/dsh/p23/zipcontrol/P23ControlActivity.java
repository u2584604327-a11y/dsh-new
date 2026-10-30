package com.dsh.p23.zipcontrol;
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

public final class P23ControlActivity extends Activity {
  private static final String TAG="DSH_P23_ZIP";
  private boolean bound=false;
  private final Messenger inbox=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message m) {
      if(m.what!=1)return;
      Bundle b;
      try{b=m.getData();}catch(RuntimeException error){
        Log.e(TAG,"P23_REPLY_MALFORMED=FAIL");return;
      }
      boolean uid=Process.isIsolatedUid(m.sendingUid)
        && m.sendingUid!=Process.myUid()
        && b.getBoolean("isolated",false) && b.getInt("uid",-1)==m.sendingUid;
      Log.i(TAG,"P23_ISOLATED_BINDER_UID="+(uid?"PASS":"FAIL"));
      boolean archive=uid && b.getBoolean("zipReadable",false);
      boolean entries=uid && b.getBoolean("allEntriesReadable",false);
      boolean bridge=uid && b.getBoolean("bridgeLoaded",false);
      Log.i(TAG,"P23_INSTALLED_APK_READABLE="+(archive?"PASS":"FAIL"));
      Log.i(TAG,"P23_ALL_THREE_ENTRIES_READABLE="+(entries?"PASS":"FAIL"));
      Log.i(TAG,"P23_NATIVE_BRIDGE_INSTALLED="+(bridge?"PASS":"FAIL"));
      // All three result codes are observed, not inferred from Java ZIP tests.
      int asset=b.getInt("assetShort",-100),assetVersion=b.getInt("assetVersion",-100),
          nativeLib=b.getInt("nativeVersion",-100);
      Log.i(TAG,"P23_DLOPEN_ASSET_PLAIN_CODE="+asset);
      Log.i(TAG,"P23_DLOPEN_ASSET_VERSIONED_CODE="+assetVersion);
      Log.i(TAG,"P23_DLOPEN_NATIVE_VERSIONED_CODE="+nativeLib);
      Log.i(TAG,"P23_DLOPEN_ASSET_PLAIN="+(asset==22035?"PASS":"FAIL"));
      Log.i(TAG,"P23_DLOPEN_ASSET_VERSIONED="+(assetVersion==22035?"PASS":"FAIL"));
      Log.i(TAG,"P23_DLOPEN_NATIVE_VERSIONED="+(nativeLib==22035?"PASS":"FAIL"));
      Log.i(TAG,"P23_ORIGINAL_ARM64_DSH_NODE_EXECUTED=NO");
      Log.i(TAG,"P23_DSH_PRODUCTION_MIGRATION=NO");
      Log.i(TAG,"P23_DIAGNOSTIC_COMPLETED=YES");
    }
  });
  private final ServiceConnection connection=new ServiceConnection(){
    @Override public void onServiceConnected(ComponentName cn,IBinder binder){
      try{Message m=Message.obtain(null,1);m.replyTo=inbox;new Messenger(binder).send(m);}
      catch(Exception error){Log.e(TAG,"P23_IPC_SEND=FAIL");}
    }
    @Override public void onServiceDisconnected(ComponentName cn){
      Log.i(TAG,"P23_ISOLATED_DISCONNECTED=YES");
    }
  };
  @Override public void onCreate(Bundle saved){
    super.onCreate(saved);
    TextView label=new TextView(this);label.setText("P23 APK ZIP loader controls");
    setContentView(label);
    bound=bindService(new Intent(this,P23ControlWorker.class),
      connection,Context.BIND_AUTO_CREATE);
    if(!bound)Log.e(TAG,"P23_BIND_SERVICE=FAIL");
  }
  @Override public void onDestroy(){
    if(bound)unbindService(connection);
    super.onDestroy();
  }
}
