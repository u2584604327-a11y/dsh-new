package com.dsh.p17.probe;
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
import android.os.SystemClock;
import android.util.Log;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import com.dsh.p17.P17CapabilityGate;
/** Test-only Android shell: a real UI click grants exactly one count.
 * Uses Messenger's framework-attested Message.sendingUid; never trusts a
 * client-supplied uid field. Never exposes files, URLs, shell or network.
 */
public final class P17BrokerProbeActivity extends Activity {
  private static final String TAG="DSH_P17_BROKER";
  private final P17CapabilityGate gate=new P17CapabilityGate(SystemClock::elapsedRealtime);
  private final Messenger broker=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message m) {
      if(m.what==IsolatedCountWorker.HELLO) {
        // A HELLO is valid only once for the current, explicitly bound worker.
        // A second HELLO cannot silently swap the UID while a grant is live.
        final int reportedUid=m.sendingUid;
        boolean claimedIsolated=false;
        try { claimedIsolated=m.getData().getBoolean("isolated",false); }
        catch(RuntimeException invalid){ denyPending("BAD_HELLO");return; }
        if(remote==null || !bound || workerUid!=-1 || attempts!=0 ||
           reportedUid==Process.myUid() || !Process.isIsolatedUid(reportedUid) ||
           !claimedIsolated) {
          Log.e(TAG,"P17_REAL_BINDER_UID=FAIL");
          denyPending("INVALID_HELLO");
          return;
        }
        workerUid=reportedUid;
        Log.i(TAG,"P17_REAL_BINDER_UID=PASS");
        send(IsolatedCountWorker.TEST_UNGRANTED,null);
      }else if(m.what==IsolatedCountWorker.QUERY) {
        if(m.sendingUid!=workerUid||!Process.isIsolatedUid(m.sendingUid)) {
          Log.e(TAG,"P17_UNAUTHENTICATED_UID=DENIED");return;
        }
        String scope,token;
        try {
          scope=m.getData().getString("scope","");
          token=m.getData().getString("token","");
        } catch(RuntimeException invalid) {
          denyPending("MALFORMED_IPC");
          return;
        }
        boolean approved=gate.consume(token,scope,m.sendingUid);
        attempts++;
        if(attempts==1) {
          if(!approved){
            Log.i(TAG,"P17_PREGRANT_DENIED=PASS");
            readyForGrant=true;
            button.setEnabled(true);
          } else {
            Log.e(TAG,"P17_PREGRANT_DENIED=FAIL");
            denyPending("UNGRANTED_ACCEPTED");
          }
        }else if(attempts==2) {
          if(approved)Log.i(TAG,"P17_ONE_SHOT_APPROVED=PASS");
          else Log.e(TAG,"P17_ONE_SHOT_APPROVED=FAIL");
        }else if(attempts==3) {
          if(!approved)Log.i(TAG,"P17_REPLAY_DENIED=PASS");
          else Log.e(TAG,"P17_REPLAY_DENIED=FAIL");
        }else if(attempts==4) {
          if(!approved && "READ_PRIVATE_FILES".equals(scope))
            Log.i(TAG,"P17_ARBITRARY_FILE_SCOPE_DENIED=PASS");
          else Log.e(TAG,"P17_ARBITRARY_FILE_SCOPE_DENIED=FAIL");
          Log.i(TAG,"P17_DSH_NODE_MIGRATED=NO");
        }
      }
    }
  });
  private int workerUid=-1,attempts=0;
  private boolean readyForGrant=false;
  private Messenger remote;
  private Button button;
  private boolean bound=false;
  private final ServiceConnection connection=new ServiceConnection() {
    @Override public void onServiceConnected(ComponentName n,IBinder b) {
      denyPending("NEW_BINDING");
      remote=new Messenger(b);
      send(IsolatedCountWorker.HELLO,null);
    }
    @Override public void onServiceDisconnected(ComponentName n){
      remote=null;
      denyPending("DISCONNECTED");
    }
    @Override public void onBindingDied(ComponentName n){
      remote=null;
      denyPending("BINDING_DIED");
    }
    @Override public void onNullBinding(ComponentName n){
      remote=null;
      denyPending("NULL_BINDING");
    }
  };
  private void denyPending(String reason) {
    gate.revokeAll();
    workerUid=-1;
    attempts=0;
    readyForGrant=false;
    if(button!=null)button.setEnabled(false);
    Log.i(TAG,"P18_ALL_GRANTS_REVOKED="+reason);
  }
  private boolean send(int code,String grant) {
    if(remote==null)return false;
    try {
      Message m=Message.obtain(null,code);
      m.replyTo=broker;
      if(grant!=null){Bundle b=new Bundle();b.putString("token",grant);m.setData(b);}
      remote.send(m);
      return true;
    }catch(Exception error){
      Log.e(TAG,"P17_IPC_SEND=FAIL");
      return false;
    }
  }
  @Override public void onCreate(Bundle b) {
    super.onCreate(b);
    LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);
    TextView heading=new TextView(this);heading.setText("一次性计数授权（安全隔离测试）");
    root.addView(heading,new LinearLayout.LayoutParams(-1,90));
    button=new Button(this);button.setText("批准一次计数");
    button.setContentDescription("P17_APPROVE_ONCE"); // stable test-only a11y locator
    button.setEnabled(false);
    root.addView(button,new LinearLayout.LayoutParams(-1,140));
    setContentView(root);
    button.setOnClickListener(v->{
      Log.i(TAG,"P18_USER_CLICK_RECEIVED=YES");
      if(!bound||remote==null||!readyForGrant||
         workerUid<0||!Process.isIsolatedUid(workerUid)||attempts!=1) {
        Log.e(TAG,"P17_GESTURE_PRECONDITION=DENIED");
        return;
      }
      button.setEnabled(false);
      readyForGrant=false;
      String token;
      try {
        token=gate.approveOnce(P17CapabilityGate.SCOPE_METADATA_COUNT,
                               workerUid,20000);
      } catch(RuntimeException denied) {
        denyPending("GRANT_REJECTED");
        return;
      }
      if(send(IsolatedCountWorker.GRANT,token)){
        Log.i(TAG,"P17_TRUSTED_UI_GRANT=PASS");
      } else {
        gate.revoke(token);
        Log.e(TAG,"P17_TRUSTED_UI_GRANT=FAIL");
      }
    });
    bound=bindService(new Intent(this,IsolatedCountWorker.class),connection,Context.BIND_AUTO_CREATE);
    if(!bound)Log.e(TAG,"P17_BIND_FAILED");
  }
  @Override protected void onStop(){
    // A pending grant may not survive losing the visible trusted UI.
    denyPending("UI_BACKGROUND");
    super.onStop();
  }
  @Override public void onDestroy(){
    denyPending("ACTIVITY_DESTROY");
    if(bound)unbindService(connection);
    bound=false;
    remote=null;
    super.onDestroy();
  }
}
