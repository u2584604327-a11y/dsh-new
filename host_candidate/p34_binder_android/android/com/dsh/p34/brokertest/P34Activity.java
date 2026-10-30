package com.dsh.p34.brokertest;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Bundle;
import android.os.IBinder;
import android.os.Message;
import android.os.Messenger;
import android.util.Log;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import com.dsh.p32.P32AndroidBinderPort;

/** Android emulator real OS Binder transport test. No actual original Node. */
public final class P34Activity extends Activity {
  private static final String TAG="P34_BINDER_LAB";
  private final P32AndroidBinderPort trusted=new P32AndroidBinderPort();
  private Messenger isolated;
  private boolean bound=false;
  private Button approve;
  private final ServiceConnection connection=new ServiceConnection(){
    @Override public void onServiceConnected(ComponentName name,IBinder binder){
      isolated=new Messenger(binder);
      try{
        Message init=Message.obtain(null,P34IsolatedWorker.INIT);
        init.replyTo=trusted.getTrustedHostInbox();
        isolated.send(init);
      }catch(Exception e){Log.e(TAG,"P34_REAL_IPC_HANDSHAKE=FAIL");}
    }
    @Override public void onServiceDisconnected(ComponentName name){
      isolated=null;
      trusted.onWorkerDisconnect();
    }
    @Override public void onBindingDied(ComponentName name){
      isolated=null;
      trusted.onBinderDeath();
    }
    @Override public void onNullBinding(ComponentName name){
      isolated=null;
      trusted.onWorkerDisconnect();
    }
  };
  @Override public void onCreate(Bundle state){
    super.onCreate(state);
    // The entire Activity content is the trusted native button, so a
    // single center-screen adb input tap hits it without UIAutomator.
    // No hidden auto-approval or programmatic Button.performClick().
    approve=new Button(this);
    approve.setText("批准一次合成计数（可信原生 UI）");
    approve.setContentDescription("P34_NATIVE_APPROVE_ONCE");
    setContentView(approve);
    approve.setOnClickListener(v->{
      boolean sent=trusted.onTrustedUiApproveOnceClick();
      Log.i(TAG,"P34_NATIVE_UI_CLICK_GRANT_SENT="+(sent?"YES":"NO"));
      approve.setEnabled(false);  // cannot silently approve again
    });
    trusted.onTrustedServiceBindingInitiated();
    bound=bindService(new Intent(this,P34IsolatedWorker.class),
      connection,Context.BIND_AUTO_CREATE);
    if(!bound)Log.e(TAG,"P34_REAL_SERVICE_BIND=FAIL");
  }
  @Override protected void onStop(){
    trusted.onTrustedUiBackground();
    Log.i(TAG,"P34_HOST_BACKGROUND_REVOKE_INVOKED=PASS");
    super.onStop();
  }
  @Override public void onDestroy(){
    trusted.onWorkerDisconnect();
    if(bound)unbindService(connection);
    bound=false;isolated=null;
    super.onDestroy();
  }
}
