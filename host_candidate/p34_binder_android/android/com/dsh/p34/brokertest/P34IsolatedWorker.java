package com.dsh.p34.brokertest;

import android.app.Service;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.Process;
import android.util.Log;
import com.dsh.p32.P32AndroidBinderPort;

/** Real Android isolated UID and real Messenger, only synthetic fixed frame.
 * This class does not claim execution of actual original Node on x86 emulator.
 */
public final class P34IsolatedWorker extends Service {
  public static final int INIT=991;
  private static final String TAG="P34_BINDER_LAB";
  private static final String FRAME="{\"op\":\"METADATA_COUNT\",\"limit\":3}";
  private Messenger host=null;
  private int hostUid=-1;
  private String session=null;
  private String token=null;
  private int phase=0;
  private final Messenger workerInbox=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message m){
      try{
        if(m.what==INIT){
          if(host!=null||!Process.isIsolated()||m.replyTo==null||
             Process.isIsolatedUid(m.sendingUid)||
             m.sendingUid!=getApplicationInfo().uid)return;
          hostUid=m.sendingUid;
          host=m.replyTo;
          Message hello=Message.obtain(null,P32AndroidBinderPort.HELLO);
          hello.replyTo=workerInbox;
          host.send(hello);
          return;
        }
        if(host==null||m.sendingUid!=hostUid)return;
        if(m.what==P32AndroidBinderPort.HELLO_REPLY){
          session=m.getData().getString("session");
          if(session==null||session.length()!=64)return;
          phase=0;
          sendRequest(null);
        }else if(m.what==P32AndroidBinderPort.GRANT){
          if(phase!=1)return;
          Bundle d=m.getData();
          if(!session.equals(d.getString("session")) ||
             !"METADATA_COUNT".equals(d.getString("scope")))return;
          token=d.getString("grant");
          if(token==null||token.length()!=64)return;
          phase=2;
          sendRequest(token);
        }else if(m.what==P32AndroidBinderPort.REQUEST_REPLY){
          String state=m.getData().getString("result","");
          if(phase==0){
            if(!"DENY_NO_GRANT".equals(state)){
              Log.e(TAG,"P34_PREGRANT_DENIAL=FAIL");
              return;
            }
            Log.i(TAG,"P34_PREGRANT_DENIAL=PASS");
            Log.i(TAG,"P34_WORKER_ISOLATED_UID="+Process.myUid());
            phase=1;
          }else if(phase==2){
            int synthetic=m.getData().getInt("syntheticCount",-1);
            if(!"ALLOW_COUNT".equals(state)||synthetic!=3){
              Log.e(TAG,"P34_REAL_BINDER_APPROVED_ONCE=FAIL");
              return;
            }
            Log.i(TAG,"P34_REAL_BINDER_APPROVED_ONCE=PASS");
            phase=3;
            sendRequest(token);
          }else if(phase==3){
            if(!"DENY_NO_GRANT".equals(state)){
              Log.e(TAG,"P34_REAL_BINDER_REPLAY_DENIAL=FAIL");
              return;
            }
            Log.i(TAG,"P34_REAL_BINDER_REPLAY_DENIAL=PASS");
            Log.i(TAG,"P34_REAL_ISOLATED_UID_AND_NATIVE_CONSENT_E2E=PASS");
            Log.i(TAG,"P34_ORIGINAL_ARM64_NODE_RUNTIME_PRESENT=NO");
            phase=4;
          }
        }
      }catch(Exception e){
        Log.e(TAG,"P34_REAL_BINDER_PROTOCOL=FAIL_"+e.getClass().getSimpleName());
      }
    }
    private void sendRequest(String grant)throws Exception{
      Message q=Message.obtain(null,P32AndroidBinderPort.REQUEST);
      q.replyTo=workerInbox;
      Bundle b=new Bundle();
      b.putString("session",session);
      if(grant!=null)b.putString("grant",grant);
      b.putString("nodeFrame",FRAME);
      q.setData(b);
      host.send(q);
    }
  });
  @Override public IBinder onBind(Intent intent){
    if(!Process.isIsolated())throw new SecurityException("requires real isolatedProcess");
    return workerInbox.getBinder();
  }
  @Override public void onDestroy(){
    host=null;token=null;session=null;phase=0;hostUid=-1;
    super.onDestroy();
  }
}
