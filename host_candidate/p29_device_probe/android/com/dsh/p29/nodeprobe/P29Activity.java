package com.dsh.p29.nodeprobe;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
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
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.File;
import java.io.FileOutputStream;
import java.security.SecureRandom;

/** Host creates one private app-only canary, never sends its bytes to Node. */
public final class P29Activity extends Activity {
  private final static String HEADER =
    "DSH P29 原版 Node 安全隔离实机探测\n"
    +"独立安装包，不替换原 DSH，不上传诊断。\n"
    +"此测试会尝试读取本应用临时私有测试文件，"
    +"以及连接 127.0.0.1:9 和 198.51.100.1:443。\n"
    +"网络仅发起 TCP 连接，不发送任何聊天/用户数据。\n"
    +"点击开始才执行；只运行预设安全探测程序。\n\n";
  private TextView report;
  private Button start;
  private boolean started=false,bound=false;
  private File canary=null;
  private boolean hostCanaryVerified=false;
  private String result="NOT_RUN";
  private void show(String text) {
    result=text;
    report.setText(HEADER+text);
  }
  private void eraseCanary(){
    if(canary!=null){try{canary.delete();}catch(Exception ignored){}}
  }
  private final Messenger receiver=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message msg){
      if(msg.what!=1)return;
      Bundle b;
      try{b=msg.getData();}catch(RuntimeException e){
        show("BLOCKED_MALFORMED_BINDER_RESULT");eraseCanary();return;
      }
      boolean isolatedUid=Process.isIsolatedUid(msg.sendingUid)
          && msg.sendingUid!=Process.myUid()
          && b.getBoolean("workerIsolated",false)
          && b.getInt("workerUid",-1)==msg.sendingUid;
      String status=b.getString("status","BLOCKED");
      if(!isolatedUid || !hostCanaryVerified)status="BLOCKED_IDENTITY_OR_CANARY";
      String text="P29_STATUS="+status
          +"\nANDROID_API="+android.os.Build.VERSION.SDK_INT
          +"\nANDROID_PRIMARY_ABI="+android.os.Build.SUPPORTED_ABIS[0]
          +"\nWORKER_BINDER_ISOLATED_UID="+(isolatedUid?"PASS":"FAIL")
          +"\nHOST_PRIVATE_CANARY_CREATED="+(hostCanaryVerified?"PASS":"FAIL")
          +"\nEXACT_ORIGINAL_NODE_11_ELF_SHA="+(isolatedUid && b.getBoolean("allHashes",false)?"PASS":"FAIL_OR_NOT_TESTED")
          +"\nREAL_NODE_CHILD_UID="+b.getString("childUid","NOT_TESTED")
          +"\nNODE_CHILD_UID_EQUALS_WORKER="+(isolatedUid && b.getBoolean("uidMatch",false)?"PASS":"FAIL_OR_NOT_TESTED")
          +"\nREAL_NODE_PRIVATE_CANARY_READ="+b.getString("privateFile","NOT_TESTED")
          +"\nREAL_NODE_LOOPBACK_TCP="+b.getString("loopback","NOT_TESTED")
          +"\nREAL_NODE_TESTNET_TCP="+b.getString("testnet","NOT_TESTED")
          +"\nNODE_PROBE_EXIT="+b.getString("nodeExit","NOT_TESTED")
          +"\nPHASE="+b.getString("phase","UNKNOWN")
          +"\nNOTE="+b.getString("note","NONE")
          +"\nDSH_FULL_NATIVE_HOST_INTEGRATION=NO"
          +"\nSTRONG_VM_OR_DEVICE_IMPERSONATION=NOT_PROVEN"
          +"\nV139_RELEASE=BLOCKED"
          +"\n\n只需复制这段文字给 ChatGPT；不含真实私人文件内容。";
      eraseCanary();
      show(text);
      start.setEnabled(false);
    }
  });
  private final ServiceConnection connection=new ServiceConnection(){
    @Override public void onServiceConnected(ComponentName cn, IBinder raw){
      try {
        if(canary==null || !canary.isFile() || canary.length()!=32) {
          show("BLOCKED_CANARY_MISSING_BEFORE_BINDER");return;
        }
        Message m=Message.obtain(null,1);
        m.replyTo=receiver;
        Bundle d=new Bundle();
        d.putString("canaryPath",canary.getAbsolutePath());
        m.setData(d);
        new Messenger(raw).send(m);
      } catch(Exception e) {
        show("BLOCKED_IPC_SEND");
        eraseCanary();
      }
    }
    @Override public void onServiceDisconnected(ComponentName cn){
      if(result.equals("RUNNING")){show("BLOCKED_WORKER_DISCONNECTED");eraseCanary();}
    }
  };
  @Override public void onCreate(Bundle state) {
    super.onCreate(state);
    LinearLayout pane=new LinearLayout(this);
    pane.setOrientation(LinearLayout.VERTICAL);
    pane.setPadding(26,24,26,24);
    report=new TextView(this);
    report.setTextSize(15);
    ScrollView scroll=new ScrollView(this);
    scroll.addView(report);
    pane.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
    start=new Button(this);
    start.setText("开始安全隔离实测（固定 Node 诊断）");
    pane.addView(start);
    Button copy=new Button(this);
    copy.setText("复制测试报告");
    pane.addView(copy);
    setContentView(pane);
    show("NOT_RUN");
    start.setOnClickListener(v->{
      if(started)return;
      started=true;start.setEnabled(false);
      try{
        canary=new File(getFilesDir(),"p29_private_canary.bin").getCanonicalFile();
        if(!canary.getParentFile().equals(getFilesDir().getCanonicalFile()))
          throw new SecurityException("BAD_CANARY_PARENT");
        byte[] bytes=new byte[32];new SecureRandom().nextBytes(bytes);
        try(FileOutputStream output=new FileOutputStream(canary,false)){output.write(bytes);}
        hostCanaryVerified=canary.isFile()&&canary.length()==32;
        if(!hostCanaryVerified)throw new IllegalStateException("CANARY_NOT_WRITTEN");
        show("RUNNING");
        bound=bindService(new Intent(this,P29Worker.class),connection,Context.BIND_AUTO_CREATE);
        if(!bound)throw new IllegalStateException("BIND_FAILED");
      }catch(Exception e){show("BLOCKED_HOST_CANARY_OR_BIND");eraseCanary();}
    });
    copy.setOnClickListener(v->{
      ClipboardManager cb=(ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
      if(cb!=null)cb.setPrimaryClip(ClipData.newPlainText("P29 real Node boundary result",result));
    });
  }
  @Override public void onDestroy(){
    if(bound)unbindService(connection);
    eraseCanary();
    super.onDestroy();
  }
}
