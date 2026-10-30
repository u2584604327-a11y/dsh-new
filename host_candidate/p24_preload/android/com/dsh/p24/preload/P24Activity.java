package com.dsh.p24.preload;
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

/** Trust Binder framework sendingUid, not a child-provided UID alone. */
public final class P24Activity extends Activity {
  private static final String TAG="DSH_P24_SONAME";
  private boolean bound=false;
  private final Messenger reply=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message msg){
      if(msg.what!=1)return;
      Bundle b;
      try{b=msg.getData();}catch(RuntimeException bad){
        Log.e(TAG,"P24_MALFORMED_REPLY=FAIL");return;
      }
      boolean identity=Process.isIsolatedUid(msg.sendingUid)
          && msg.sendingUid!=Process.myUid()
          && msg.sendingUid==b.getInt("uid",-1)
          && b.getBoolean("isolated",false);
      Log.i(TAG,"P24_BINDER_ISOLATED_UID="+(identity?"PASS":"FAIL"));
      Log.i(TAG,"P24_EXTRACTED_UNVERSIONED_ALIAS="+
          ((identity&&b.getBoolean("extractedAlias",false))?"PASS":"FAIL"));
      Log.i(TAG,"P24_NO_PRELOAD_VERSIONED_DEPENDENCY_MISSING="+
          ((identity&&b.getBoolean("negativeControl",false))?"PASS":"FAIL"));
      Log.i(TAG,"P24_PRELOAD_VERSIONED_SONAME_EXEC_AND_CHILD_UID="+
          ((identity&&b.getBoolean("preloadSuccess",false))?"PASS":"FAIL"));
      Log.i(TAG,"P24_REPORTED_NEGATIVE_EXIT="+b.getInt("negativeExit",-99));
      Log.i(TAG,"P24_REPORTED_PRELOAD_EXIT="+b.getInt("positiveExit",-99));
      Log.i(TAG,"P24_ORIGINAL_ARM64_NODE_EXECUTED=NO");
      Log.i(TAG,"P24_ORIGINAL_DSH_MIGRATED=NO");
      Log.i(TAG,"P24_RESULT_REPORTED=YES");
    }
  });
  private final ServiceConnection connection=new ServiceConnection(){
    @Override public void onServiceConnected(ComponentName name,IBinder binder){
      try{Message m=Message.obtain(null,1);m.replyTo=reply;new Messenger(binder).send(m);}
      catch(Exception error){Log.e(TAG,"P24_BINDER_IPC=FAIL");}
    }
    @Override public void onServiceDisconnected(ComponentName name){
      Log.i(TAG,"P24_WORKER_DISCONNECTED=YES");
    }
  };
  @Override public void onCreate(Bundle state){
    super.onCreate(state);
    TextView label=new TextView(this);
    label.setText("P24 native ELF SONAME preload proof");
    setContentView(label);
    bound=bindService(new Intent(this,P24Worker.class),connection,Context.BIND_AUTO_CREATE);
    if(!bound)Log.e(TAG,"P24_BIND_SERVICE=FAIL");
  }
  @Override public void onDestroy(){
    if(bound)unbindService(connection);
    super.onDestroy();
  }
}
