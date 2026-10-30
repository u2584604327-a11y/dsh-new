package com.dsh.p17.probe;
import android.app.Service;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.Process;
/** No permissions. Only sends fixed protocol requests to trusted host. */
public final class IsolatedCountWorker extends Service {
  public static final int HELLO=1, TEST_UNGRANTED=2, GRANT=3, QUERY=4;
  private Messenger host;
  private int authenticatedHostUid=-1;
  private final Messenger work=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message m) {
      if(m.replyTo==null||!Process.isIsolated())return;
      // The initial HELLO comes through the non-exported, explicit bound
      // service. Subsequent messages must be from that same framework UID
      // and the same host Messenger endpoint.
      if(m.what==HELLO) {
        if(host!=null || m.sendingUid<0 ||
           Process.isIsolatedUid(m.sendingUid))return;
        authenticatedHostUid=m.sendingUid;
        host=m.replyTo;
      } else if(host==null || m.sendingUid!=authenticatedHostUid ||
                m.replyTo.getBinder()!=host.getBinder())return;
      try{
        if(m.what==HELLO) {
          Message hello=Message.obtain(null,HELLO);
          Bundle b=new Bundle();b.putBoolean("isolated",Process.isIsolated());
          hello.setData(b);host.send(hello);
        }else if(m.what==TEST_UNGRANTED) {
          request("invalid-nonce","METADATA_COUNT");
        }else if(m.what==GRANT) {
          String token=m.getData().getString("token","");
          request(token,"METADATA_COUNT");
          request(token,"METADATA_COUNT");
          request(token,"READ_PRIVATE_FILES");
        }
      }catch(Exception ignored){}
    }
    private void request(String token,String scope)throws Exception{
      Message q=Message.obtain(null,QUERY);
      Bundle b=new Bundle();b.putString("token",token);b.putString("scope",scope);
      q.setData(b);host.send(q);
    }
  });
  @Override public IBinder onBind(Intent intent){
    if(!Process.isIsolated())throw new SecurityException("P18 requires isolated UID");
    return work.getBinder();
  }
  @Override public boolean onUnbind(Intent intent){
    host=null;
    authenticatedHostUid=-1;
    return super.onUnbind(intent);
  }
  @Override public void onDestroy(){
    host=null;
    authenticatedHostUid=-1;
    super.onDestroy();
  }
}
