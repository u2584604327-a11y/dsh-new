package com.dsh.p21.probe;
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

/** Disposable proof only. Android Binder-authenticated sender UID is checked. */
public final class P21ProbeActivity extends Activity {
  private static final String TAG="DSH_P21_NODE";
  private boolean bound=false;
  private final Messenger inbox=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message m){
      if(m.what!=1)return;
      boolean sender=Process.isIsolatedUid(m.sendingUid) && m.sendingUid!=Process.myUid();
      Bundle result;
      try{result=m.getData();}catch(RuntimeException error){
        Log.e(TAG,"P21_REPLY_MALFORMED=FAIL");return;
      }
      boolean identity=sender && result.getInt("uid",-1)==m.sendingUid &&
          result.getBoolean("isolated",false);
      boolean pinned=result.getBoolean("originalShaPinned",false);
      boolean version=result.getBoolean("originalNodeVersionRecognized",false);
      if(identity)Log.i(TAG,"P21_REAL_WORKER_ISOLATED_UID=PASS");
      else Log.e(TAG,"P21_REAL_WORKER_ISOLATED_UID=FAIL");
      if(identity && pinned && version)
        Log.i(TAG,"P21_ORIGINAL_ARM64_NODE_ISOLATED_UID_VERSION=PASS");
      else Log.e(TAG,"P21_ORIGINAL_ARM64_NODE_ISOLATED_UID_VERSION=FAIL");
      Log.i(TAG,"P21_ORIGINAL_DSH_APP_NODE_MIGRATED=NO");
      Log.i(TAG,"P21_PLUGIN_NETWORK_FS_GATE_CLOSED=NOT_TESTED");
    }
  });
  private final ServiceConnection connection=new ServiceConnection(){
    @Override public void onServiceConnected(ComponentName component,IBinder binder){
      try{Message m=Message.obtain(null,1);m.replyTo=inbox;
        new Messenger(binder).send(m);
      }catch(Exception error){Log.e(TAG,"P21_IPC_REQUEST=FAIL");}
    }
    @Override public void onServiceDisconnected(ComponentName component){
      Log.i(TAG,"P21_ISOLATED_WORKER_DISCONNECTED=YES");
    }
  };
  @Override public void onCreate(Bundle state){
    super.onCreate(state);
    TextView view=new TextView(this);
    view.setText("P21 real Node isolated UID smoke test");
    setContentView(view);
    bound=bindService(new Intent(this,P21RealNodeService.class),
        connection,Context.BIND_AUTO_CREATE);
    if(!bound)Log.e(TAG,"P21_BIND_ISOLATED=FAIL");
  }
  @Override public void onDestroy(){
    if(bound)unbindService(connection);
    super.onDestroy();
  }
}
