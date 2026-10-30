package com.dsh.p31.nodeprobe;

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
import java.io.FileInputStream;
import java.security.MessageDigest;
import java.security.SecureRandom;

/** Host creates one private app-only canary, never sends its bytes to Node. */
public final class P31Activity extends Activity {
  private final static String HEADER =
    "DSH P31 原版 Node 安全隔离实机探测\n"
    +"独立安装包，不替换原 DSH，不上传诊断。\n"
    +"本次新增 Node 自身 ELF 可读的正向对照，再尝试本应用私有测试文件，"
    +"以及连接 127.0.0.1:9 和 198.51.100.1:443。\n"
    +"网络仅发起 TCP 连接，不发送任何聊天/用户数据。\n"
    +"点击开始才执行；只运行预设安全探测程序。\n\n";
  private TextView report;
  private Button start;
  private boolean started=false,bound=false;
  private File canary=null;
  private byte[] expectedCanaryHash=null;
  private boolean hostCanaryVerified=false;
  private String result="NOT_RUN";
  private void show(String text) {
    result=text;
    report.setText(HEADER+text);
  }
  /** Positive control: host still reads identical canary AFTER isolated Node probe. */
  private boolean canaryStable() {
    if(canary==null||expectedCanaryHash==null)return false;
    try {
      if(!canary.getCanonicalFile().getParentFile().equals(getFilesDir().getCanonicalFile())
          ||canary.length()!=32)return false;
      byte[] contents=new byte[32];
      try(FileInputStream input=new FileInputStream(canary)) {
        int offset=0,n;
        while(offset<32&&(n=input.read(contents,offset,32-offset))>0)offset+=n;
        if(offset!=32||input.read()!=-1)return false;
      }
      return MessageDigest.isEqual(expectedCanaryHash,
          MessageDigest.getInstance("SHA-256").digest(contents));
    }catch(Exception e){return false;}
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
      int trustedSender=msg.sendingUid;
      int reportedWorker=b.getInt("workerUid",-1);
      boolean isolatedUid=Process.isIsolatedUid(trustedSender)
          && trustedSender!=Process.myUid()
          && b.getBoolean("workerIsolated",false)
          && reportedWorker==trustedSender;
      boolean hostStillReadable=canaryStable();
      boolean hashPassed=b.getBoolean("allHashes",false);
      boolean childUidMatch=b.getBoolean("uidMatch",false);
      String childUid=b.getString("childUid","NOT_TESTED");
      String canaryCode=b.getString("privateFile","NOT_TESTED");
      String positive=b.getString("positiveFs","NOT_TESTED");
      String parentStat=b.getString("parentStat","NOT_TESTED");
      String fileStat=b.getString("privateStat","NOT_TESTED");
      String local=b.getString("loopback","NOT_TESTED");
      String remote=b.getString("testnet","NOT_TESTED");
      String nodeExit=b.getString("nodeExit","NOT_TESTED");
      String status=b.getString("status","BLOCKED");
      boolean networkDenied=("DENIED_EACCES".equals(local)||"DENIED_EPERM".equals(local))
          && ("DENIED_EACCES".equals(remote)||"DENIED_EPERM".equals(remote));
      boolean fileDenied="DENIED_EACCES".equals(canaryCode)
          ||"DENIED_EPERM".equals(canaryCode);
      boolean fileInvisible="OTHER_ENOENT".equals(canaryCode);
      boolean positiveOk="PASS_ELF_MAGIC".equals(positive);
      if(!isolatedUid)status="BLOCKED_BINDER_UID_NOT_AUTHENTICATED";
      else if(!hostCanaryVerified||!hostStillReadable)status="BLOCKED_HOST_CANARY_NOT_STABLE";
      else if(!hashPassed||!childUidMatch||!"0".equals(nodeExit))
        status="BLOCKED_NODE_SHA_OR_CHILD_UID_OR_EXIT";
      else if(!positiveOk)status="BLOCKED_NODE_POSITIVE_FILESYSTEM_CONTROL";
      else if(!networkDenied)status="BLOCKED_NODE_TCP_NOT_PROVEN_DENIED";
      else if(fileDenied)status="PASS_STRICT_FIXED_NODE_UID_FILE_AND_TCP_DENIAL";
      else if(fileInvisible)
        status="PASS_NARROW_NODE_FS_WORKS_HOST_PRIVATE_CANARY_INVISIBLE_NOT_ACL_DENIAL";
      else status="BLOCKED_PRIVATE_FILE_ACCESS_UNVERIFIED";
      String text="P31_STATUS="+status
          +"\nANDROID_API="+android.os.Build.VERSION.SDK_INT
          +"\nANDROID_PRIMARY_ABI="+android.os.Build.SUPPORTED_ABIS[0]
          +"\nHOST_BINDER_SENDING_UID="+trustedSender
          +"\nWORKER_REPORTED_UID="+reportedWorker
          +"\nWORKER_BINDER_ISOLATED_UID="+(isolatedUid?"PASS":"FAIL")
          +"\nHOST_PRIVATE_CANARY_CREATED="+(hostCanaryVerified?"PASS":"FAIL")
          +"\nHOST_PRIVATE_CANARY_STABLE_AFTER="+(hostStillReadable?"PASS":"FAIL")
          +"\nEXACT_ORIGINAL_NODE_11_ELF_SHA="+(isolatedUid&&hashPassed?"PASS":"FAIL_OR_NOT_TESTED")
          +"\nREAL_NODE_CHILD_UID="+childUid
          +"\nNODE_CHILD_UID_EQUALS_WORKER="+(isolatedUid&&childUidMatch?"PASS":"FAIL_OR_NOT_TESTED")
          +"\nREAL_NODE_OWN_ELF_HEADER_READ="+positive
          +"\nREAL_NODE_HOST_CANARY_PARENT_STAT="+parentStat
          +"\nREAL_NODE_HOST_CANARY_STAT="+fileStat
          +"\nREAL_NODE_PRIVATE_CANARY_READ="+canaryCode
          +"\nFILE_ACCESS_DENIED_BY_ERRNO="+(fileDenied?"PASS":"NOT_PROVEN")
          +"\nNODE_FILESYSTEM_POSITIVE_CONTROL="+(positiveOk?"PASS":"FAIL")
          +"\nFILE_NOT_VISIBLE_WHILE_HOST_CANARY_EXISTS="+(hostStillReadable&&fileInvisible?"OBSERVED":"NOT_PROVEN")
          +"\nREAL_NODE_LOOPBACK_TCP="+local
          +"\nREAL_NODE_TESTNET_TCP="+remote
          +"\nNODE_PROBE_EXIT="+nodeExit
          +"\nPHASE="+b.getString("phase","UNKNOWN")
          +"\nNOTE="+b.getString("note","NONE")
          +"\nDSH_FULL_NATIVE_HOST_INTEGRATION=NO"
          +"\nSTRONG_VM_OR_DEVICE_IMPERSONATION=NOT_PROVEN"
          +"\nV139_RELEASE=BLOCKED"
          +"\n\n仅复制本地状态；不会发送测试文件内容。";
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
    start.setText("开始文件系统正向对照和隔离验证");
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
        canary=new File(getFilesDir(),"p31_private_canary.bin").getCanonicalFile();
        if(!canary.getParentFile().equals(getFilesDir().getCanonicalFile()))
          throw new SecurityException("BAD_CANARY_PARENT");
        byte[] bytes=new byte[32];new SecureRandom().nextBytes(bytes);
        try(FileOutputStream output=new FileOutputStream(canary,false)){output.write(bytes);}
        expectedCanaryHash=MessageDigest.getInstance("SHA-256").digest(bytes);
        hostCanaryVerified=canaryStable();
        if(!hostCanaryVerified)throw new IllegalStateException("CANARY_NOT_WRITTEN");
        show("RUNNING");
        bound=bindService(new Intent(this,P31Worker.class),connection,Context.BIND_AUTO_CREATE);
        if(!bound)throw new IllegalStateException("BIND_FAILED");
      }catch(Exception e){show("BLOCKED_HOST_CANARY_OR_BIND");eraseCanary();}
    });
    copy.setOnClickListener(v->{
      ClipboardManager cb=(ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
      if(cb!=null)cb.setPrimaryClip(ClipData.newPlainText("P31 real Node boundary result",result));
    });
  }
  @Override public void onDestroy(){
    if(bound)unbindService(connection);
    eraseCanary();
    super.onDestroy();
  }
}
