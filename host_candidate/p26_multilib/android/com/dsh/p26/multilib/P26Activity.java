package com.dsh.p26.multilib;
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
public final class P26Activity extends Activity {
  private static final String TAG="DSH_P26_SONAME";
  private boolean bound=false;
  private final Messenger reply=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message msg){
      if(msg.what!=1)return;
      Bundle b;
      try{b=msg.getData();}catch(RuntimeException bad){
        Log.e(TAG,"P26_MALFORMED_REPLY=FAIL");return;
      }
      boolean identity=Process.isIsolatedUid(msg.sendingUid)
          && msg.sendingUid!=Process.myUid()
          && msg.sendingUid==b.getInt("uid",-1)
          && b.getBoolean("isolated",false);
      Log.i(TAG,"P26_BINDER_ISOLATED_UID="+(identity?"PASS":"FAIL"));
      Log.i(TAG,"P26_EXTRACTED_THREE_NATIVE_LIBRARIES="+
          ((identity&&b.getBoolean("extractedAlias",false))?"PASS":"FAIL"));
      Log.i(TAG,"P26_NEGATIVE_MISSING_TOP_SONAME="+
          ((identity&&b.getBoolean("negativeControl",false))?"PASS":"FAIL"));
      Log.i(TAG,"P26_TWO_PRELOADS_AND_MISSING_SONAME_SQLITE_EXEC_UID="+
          ((identity&&b.getBoolean("preloadSuccess",false))?"PASS":"FAIL"));
      Log.i(TAG,"P26_REPORTED_NEGATIVE_EXIT="+b.getInt("negativeExit",-99));
      Log.i(TAG,"P26_REPORTED_PRELOAD_EXIT="+b.getInt("positiveExit",-99));
      Log.i(TAG,"P26_ORIGINAL_ARM64_NODE_EXECUTED=NO");
      Log.i(TAG,"P26_ORIGINAL_DSH_MIGRATED=NO");
      Log.i(TAG,"P26_RESULT_REPORTED=YES");
    }
  });
  private final ServiceConnection connection=new ServiceConnection(){
    @Override public void onServiceConnected(ComponentName name,IBinder binder){
      try{Message m=Message.obtain(null,1);m.replyTo=reply;new Messenger(binder).send(m);}
      catch(Exception error){Log.e(TAG,"P26_BINDER_IPC=FAIL");}
    }
    @Override public void onServiceDisconnected(ComponentName name){
      Log.i(TAG,"P26_WORKER_DISCONNECTED=YES");
    }
  };
  @Override public void onCreate(Bundle state){
    super.onCreate(state);
    TextView label=new TextView(this);
    label.setText("P26 native ELF SONAME preload proof");
    setContentView(label);
    bound=bindService(new Intent(this,P26Worker.class),connection,Context.BIND_AUTO_CREATE);
    if(!bound)Log.e(TAG,"P26_BIND_SERVICE=FAIL");
  }
  @Override public void onDestroy(){
    if(bound)unbindService(connection);
    super.onDestroy();
  }
}
