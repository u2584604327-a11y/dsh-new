package com.dsh.p28.nodeprobe;

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

/** Separate-package local test UI. No node execution until user clicks. */
public final class P28Activity extends Activity {
  private TextView report;
  private Button run;
  private boolean bound=false;
  private String reportText="P28 尚未运行";
  private static final String HEADER=
      "DSH P28 原版 ARM64 Node 离线验证\n"
      +"这不是 DSH v139，不会替换已有 DSH。\n"
      +"没有网络或存储权限，不上传数据。\n"
      +"只会执行原版 Node 的 --version，不运行 JS。\n"
      +"点击下方按钮才启动测试。\n\n";
  private final Messenger reply=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message msg) {
      if(msg.what!=1)return;
      boolean frameworkUid=Process.isIsolatedUid(msg.sendingUid)
          && msg.sendingUid!=Process.myUid();
      Bundle payload;
      try{payload=msg.getData();}catch(RuntimeException bad){
        show("结果无效：Binder 数据无法读取");return;
      }
      boolean proven=frameworkUid
          && msg.sendingUid==payload.getInt("isolatedUid",-1)
          && payload.getBoolean("workerIsolated",false);
      String status=payload.getString("status","UNKNOWN");
      String phase=payload.getString("phase","UNKNOWN");
      String version=payload.getString("version","-");
      String note=payload.getString("note","-");
      if(!proven)status="BLOCKED_BINDER_UID_NOT_VERIFIED";
      String text="验证状态："+status
          +"\nAndroid API："+android.os.Build.VERSION.SDK_INT
          +"\n设备 ABI："+android.os.Build.SUPPORTED_ABIS[0]
          +"\n真实隔离 Service UID 验证："+(proven?"PASS":"FAIL")
          +"\n原版 Node 和 10 个库 SHA256："+(proven && payload.getBoolean("allHashes",false)?"PASS":"FAIL_OR_NOT_TESTED")
          +"\nNode --version 返回："+(proven && payload.getBoolean("versionPassed",false)?"PASS":"FAIL_OR_NOT_TESTED")
          +"\n检测到的 Node 版本："+version
          +"\n阶段："+phase
          +"\n说明："+note
          +"\n子进程 UID 独立测量：NOT_TESTED（只有隔离 Worker 的 Binder UID 已验证）"
          +"\nNode 网络与私人文件主动攻击测试：NOT_TESTED"
          +"\n原版 DSH 功能集成：NO；v139 发布：BLOCKED"
          +"\n\n本报告仅保存在屏幕上；点击复制后可手动发送。";
      show(text);
    }
  });
  private final ServiceConnection connection=new ServiceConnection(){
    @Override public void onServiceConnected(ComponentName cn,IBinder binder){
      try{
        Message m=Message.obtain(null,1);m.replyTo=reply;
        new Messenger(binder).send(m);
      }catch(Exception error){show("BLOCKED：无法向隔离服务发送测试请求");}
    }
    @Override public void onServiceDisconnected(ComponentName cn){
      if(reportText.startsWith("正在"))show("BLOCKED：独立 Service 连接中断");
    }
  };
  private void show(String body){
    reportText=body;
    report.setText(HEADER+body);
    run.setEnabled(true);
  }
  @Override public void onCreate(Bundle saved){
    super.onCreate(saved);
    LinearLayout pane=new LinearLayout(this);
    pane.setPadding(28,24,28,24);
    pane.setOrientation(LinearLayout.VERTICAL);
    TextView text=new TextView(this);
    text.setTextSize(15);
    report=text;
    ScrollView scroller=new ScrollView(this);
    scroller.addView(text);
    pane.addView(scroller,new LinearLayout.LayoutParams(-1,0,1));
    Button start=new Button(this);
    start.setText("开始离线检测（原版 Node --version）");
    run=start;
    pane.addView(start);
    Button copy=new Button(this);
    copy.setText("复制本地检测结果");
    pane.addView(copy);
    setContentView(pane);
    show("P28 尚未运行。点击“开始离线检测”才会启动。");
    start.setOnClickListener(v->{
      if(bound){show("检测已经发起，避免重复启动；返回后可重新打开测试应用。");return;}
      reportText="正在通过独立 UID 验证原版 Node，请勿重复点击。";
      text.setText(HEADER+reportText);
      start.setEnabled(false);
      try{
        bound=bindService(new Intent(this,P28Worker.class),connection,Context.BIND_AUTO_CREATE);
        if(!bound)show("BLOCKED：系统未创建隔离 Service");
      }catch(RuntimeException error){show("BLOCKED：无法绑定隔离 Service");}
    });
    copy.setOnClickListener(v->{
      ClipboardManager cb=(ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
      if(cb!=null)cb.setPrimaryClip(ClipData.newPlainText("P28 result",reportText));
    });
  }
  @Override public void onDestroy(){
    if(bound)unbindService(connection);
    super.onDestroy();
  }
}
