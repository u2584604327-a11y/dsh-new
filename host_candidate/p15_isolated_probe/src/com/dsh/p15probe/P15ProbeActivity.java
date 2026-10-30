package com.dsh.p15probe;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.Process;
import android.system.Os;
import android.util.Log;
import android.widget.TextView;
import java.io.File;
import java.io.FileOutputStream;

/** One-time, generated test-only Android shell for isolated UID validation. */
public final class P15ProbeActivity extends Activity {
    private static final String TAG="DSH_P15_ISOLATION";
    private File fixture;
    private boolean bound;
    private final Handler inbox=new Handler(Looper.getMainLooper()){
        @Override public void handleMessage(Message message){
            if(message.what!=1)return;
            Bundle data=message.getData();
            boolean separated=data.getBoolean("isolated") &&
                data.getInt("uid",-1)!=Process.myUid() &&
                !data.getBoolean("appCanaryReadable",true);
            boolean metadata;
            try{
                ServiceInfo service=getPackageManager().getServiceInfo(
                    new ComponentName(P15ProbeActivity.this,P15IsolatedService.class),0);
                metadata=(service.flags & ServiceInfo.FLAG_ISOLATED_PROCESS)!=0;
            }catch(Exception error){metadata=false;}
            if(separated&&metadata){
                Log.i(TAG,"P15_ISOLATED_UID_DISTINCT=PASS");
                Log.i(TAG,"P15_PRIVATE_CANARY_READ_DENIED=PASS");
                Log.i(TAG,"P15_ISOLATED_SERVICE_MANIFEST=PASS");
                Log.i(TAG,"P15_DSH_NODE_ALREADY_MIGRATED=NO");
                ((TextView)findViewById(android.R.id.content).getRootView()
                    .findViewWithTag("result")).setText("隔离服务验证 PASS（测试程序）");
            }else{
                Log.e(TAG,"P15_ISOLATED_SERVICE_TEST=FAIL");
            }
        }
    };
    private final Messenger receiver=new Messenger(inbox);
    private final ServiceConnection connection=new ServiceConnection(){
        @Override public void onServiceConnected(ComponentName name,IBinder binder){
            try{
                Message request=Message.obtain(null,1);
                request.replyTo=receiver;
                new Messenger(binder).send(request);
            }catch(Exception fail){Log.e(TAG,"P15_IPC=FAIL");}
        }
        @Override public void onServiceDisconnected(ComponentName name){}
    };
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        TextView label=new TextView(this);
        label.setTag("result");
        label.setText("隔离环境校验中");
        setContentView(label);
        try{
            fixture=new File(getFilesDir(),"p15-isolation-canary.tmp");
            try(FileOutputStream out=new FileOutputStream(fixture,false)){
                out.write(new byte[]{80,49,53});out.getFD().sync();
            }
            Os.chmod(fixture.getAbsolutePath(),0600);
            Intent intent=new Intent(this,P15IsolatedService.class);
            bound=bindService(intent,connection,Context.BIND_AUTO_CREATE);
            if(!bound)Log.e(TAG,"P15_BIND_ISOLATED=FAIL");
        }catch(Exception error){Log.e(TAG,"P15_FIXTURE_SETUP=FAIL");}
    }
    @Override public void onDestroy(){
        if(bound)try{unbindService(connection);}catch(Exception ignored){}
        if(fixture!=null)fixture.delete();
        super.onDestroy();
    }
}
