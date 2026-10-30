package com.dsh.p36.nodebridge;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.Process;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import com.dsh.p32.P32AndroidBinderPort;

/** Trusted native host of one SHA-pinned original Node -> Binder capability.
 * Separate package. NOT the real DSH MainActivity or v139 host.
 */
public final class P36Activity extends Activity {
  private static final String HEADER=
      "DSH P36 原版 Node → Binder → 原生授权端到端验证\n"
      +"独立测试 APK，不替换原版 DSH、没有文件/网络/诊断发送权限。\n"
      +"真正的原版 ARM64 Node 只生成固定 METADATA_COUNT:3 消息。\n"
      +"先点“启动原版 Node”，出现 PREGRANT_DENIED 后才可点击“授权一次”。\n"
      +"不会自动申请或批准。仅供单次测试；不是完整 DSH 宿主集成。\n\n";
  private final P32AndroidBinderPort trusted=new P32AndroidBinderPort();
  private Messenger isolated;
  private Button start,approve;
  private TextView report;
  private boolean bound=false,started=false,verified=false,pregrant=false,
      approved=false,replayed=false,failed=false;
  private int authenticatedWorkerUid=-1,nodeUid=-1;
  private String failure="NONE",status="NOT_STARTED";
  private void render(){
    String outcome=failed?"BLOCKED":
       (replayed&&approved&&pregrant&&verified?"PASS_REAL_NODE_TO_TRUSTED_BINDER_ONE_SHOT":"INCOMPLETE");
    String text="P36_STATUS="+outcome
        +"\nANDROID_API="+Build.VERSION.SDK_INT
        +"\nPRIMARY_ABI="+Build.SUPPORTED_ABIS[0]
        +"\nREAL_WORKER_BINDER_UID="+authenticatedWorkerUid
        +"\nREAL_NODE_GETUID="+nodeUid
        +"\nORIGINAL_NODE_HASH_AND_10_LIBS="+(verified?"PASS":"NOT_VERIFIED")
        +"\nNODE_UID_EQUALS_ISOLATED_WORKER="+(verified?"PASS":"NOT_VERIFIED")
        +"\nREAL_NODE_CANONICAL_STDOUT_TO_BINDER="+(verified?"PASS":"NOT_VERIFIED")
        +"\nUNAPPROVED_REQUEST_DENIED="+(pregrant?"PASS":"NOT_VERIFIED")
        +"\nEXPLICIT_NATIVE_UI_APPROVAL="+(approved?"PASS":"NOT_VERIFIED")
        +"\nONE_TIME_GRANT_SUCCESS="+(approved?"PASS":"NOT_VERIFIED")
        +"\nREPLAY_REQUEST_DENIED="+(replayed?"PASS":"NOT_VERIFIED")
        +"\nFAILURE="+failure
        +"\nPHASE="+status
        +"\nORIGINAL_DSH_MAINACTIVITY_WIRED=NO"
        +"\nORIGINAL_ENGINEMANAGER_ISOLATED=NO"
        +"\nARBITRARY_NODE_TOOL_PERMISSION=NOT_TESTED"
        +"\nV139_RELEASE=BLOCKED"
        +"\n\n只复制固定测试状态，不包含密钥、文件内容或 Node 原始输出。";
    report.setText(HEADER+text);
  }
  private void fail(String why){
    failed=true;failure=why;approve.setEnabled(false);render();
  }
  private final Messenger statusReceiver=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message m){
      if(m.what!=202 || failed)return;
      int uid=m.sendingUid;
      if(!Process.isIsolatedUid(uid)||uid==Process.myUid()){
        fail("INVALID_REAL_BINDER_SENDER");return;
      }
      if(authenticatedWorkerUid!=-1 && uid!=authenticatedWorkerUid){
        fail("WORKER_UID_CHANGED");return;
      }
      authenticatedWorkerUid=uid;
      Bundle b;
      try{b=m.getData();}catch(RuntimeException e){fail("INVALID_STATUS_BUNDLE");return;}
      if(b.getInt("workerUid",-1)!=uid){
        fail("WORKER_UID_REPORTED_MISMATCH");return;
      }
      String phase=b.getString("state","");
      if(phase.startsWith("BLOCKED_")){fail(phase);return;}
      if("ORIGINAL_NODE_FRAME_VERIFIED".equals(phase)){
        nodeUid=b.getInt("childUid",-1);
        if(verified || nodeUid!=uid || !b.getBoolean("allHashes",false) ||
           !b.getBoolean("childMatch",false)){fail("NODE_SHA_OR_UID_PROOF");return;}
        verified=true;status="ORIGINAL_NODE_FRAME_VERIFIED";
      }else if("PREGRANT_DENIED".equals(phase)){
        if(!verified || pregrant){fail("PREGRANT_OUT_OF_ORDER");return;}
        pregrant=true;status="AWAITING_TRUSTED_NATIVE_APPROVAL";
        approve.setEnabled(true);
      }else if("ONE_APPROVED".equals(phase)){
        if(!pregrant||approved){fail("APPROVED_OUT_OF_ORDER");return;}
        approved=true;status="ONE_APPROVED";
      }else if("REPLAY_DENIED_COMPLETE".equals(phase)){
        if(!approved||replayed){fail("REPLAY_OUT_OF_ORDER");return;}
        replayed=true;status="REAL_NODE_TO_BINDER_DONE";
        approve.setEnabled(false);
      }else{fail("UNEXPECTED_WORKER_STATUS");return;}
      render();
    }
  });
  private final ServiceConnection connection=new ServiceConnection(){
    @Override public void onServiceConnected(ComponentName name, IBinder raw){
      try{
        isolated=new Messenger(raw);
        Message init=Message.obtain(null,P36IsolatedNodeWorker.INIT);
        init.replyTo=trusted.getTrustedHostInbox();
        Bundle d=new Bundle();
        d.putBinder("statusReceiver",statusReceiver.getBinder());
        init.setData(d);
        isolated.send(init);
      }catch(Exception e){fail("IPC_INIT_SEND_FAILED");}
    }
    @Override public void onServiceDisconnected(ComponentName name){
      isolated=null;trusted.onWorkerDisconnect();
      if(!replayed)fail("WORKER_DISCONNECTED");
    }
    @Override public void onBindingDied(ComponentName name){
      isolated=null;trusted.onBinderDeath();
      if(!replayed)fail("WORKER_BINDING_DIED");
    }
    @Override public void onNullBinding(ComponentName name){
      isolated=null;trusted.onWorkerDisconnect();
      fail("WORKER_NULL_BINDING");
    }
  };
  @Override public void onCreate(Bundle state){
    super.onCreate(state);
    LinearLayout root=new LinearLayout(this);
    root.setOrientation(LinearLayout.VERTICAL);
    root.setPadding(18,18,18,18);
    report=new TextView(this);report.setTextSize(14);
    ScrollView scroll=new ScrollView(this);scroll.addView(report);
    root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
    start=new Button(this);start.setText("启动原版 Node 隔离测试");
    root.addView(start);
    approve=new Button(this);approve.setText("原生 UI：批准一次固定合成计数");
    approve.setEnabled(false);root.addView(approve);
    Button copy=new Button(this);copy.setText("复制完整测试报告");root.addView(copy);
    setContentView(root);
    render();
    start.setOnClickListener(v->{
      if(started)return;
      started=true;start.setEnabled(false);
      status="BINDING_REAL_ISOLATED_WORKER";render();
      trusted.onTrustedServiceBindingInitiated();
      bound=bindService(new Intent(this,P36IsolatedNodeWorker.class),
          connection,Context.BIND_AUTO_CREATE);
      if(!bound)fail("REAL_ANDROID_SERVICE_BIND_FAILED");
    });
    approve.setOnClickListener(v->{
      if(!pregrant||approved||failed||!verified){
        fail("PREAPPROVAL_NOT_AUTHORIZED");return;
      }
      approve.setEnabled(false);
      if(!trusted.onTrustedUiApproveOnceClick()){
        fail("NATIVE_GRANT_NOT_SENT");return;
      }
      status="TRUSTED_NATIVE_APPROVAL_SENT";render();
    });
    copy.setOnClickListener(v->{
      ClipboardManager cb=(ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
      if(cb!=null)cb.setPrimaryClip(ClipData.newPlainText(
          "P36 real original Node Binder result",report.getText().toString()));
    });
  }
  @Override protected void onStop(){
    trusted.onTrustedUiBackground();
    approve.setEnabled(false);
    if(started&&!replayed&&!failed)fail("TRUSTED_HOST_BACKGROUNDED_AND_REVOKED");
    super.onStop();
  }
  @Override protected void onDestroy(){
    trusted.onWorkerDisconnect();
    if(bound)unbindService(connection);
    super.onDestroy();
  }
}
