package com.dsh.p32;

import com.dsh.p17.P17CapabilityGate;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.Process;
import android.os.RemoteException;
import android.os.SystemClock;

/**
 * Trusted Android HOST-side Binder/Messenger adapter. NOT installed into DSH.
 *
 * Install only in trusted native host process. Do not expose from WebView,
 * plugin, JS or Node. The Node child's bounded structured stdout must be
 * validated by an isolated Worker before it sends FRAME; host still applies
 * strict exact frame parse + UID/session/grant checks.
 */
public final class P32AndroidBinderPort {
  public static final int HELLO=1;
  public static final int REQUEST=2;
  public static final int HELLO_REPLY=101;
  public static final int REQUEST_REPLY=102;
  public static final int GRANT=103;
  private final P32NodeIpcBroker broker=new P32NodeIpcBroker(
      new P17CapabilityGate.MonotonicClock(){
        @Override public long nowMs(){return SystemClock.elapsedRealtime();}
      },new P32NodeIpcBroker.IsolatedUidVerifier(){
        @Override public boolean isIsolatedUid(int uid){
          return Process.isIsolatedUid(uid);
        }
      });
  private final Messenger hostInbox=new Messenger(new Handler(Looper.getMainLooper()){
    @Override public void handleMessage(Message incoming){
      switch(incoming.what){
        case HELLO:receiveHello(incoming);break;
        case REQUEST:receiveRequest(incoming);break;
        default:break; // unknown op always denied, no fallback broker.
      }
    }
  });
  private Messenger isolatedReply=null;
  private int isolatedUid=-1;
  private String currentSession=null;
  private boolean awaitingOneHello=false;

  /** Called only from trusted Activity upon actual non-exported bindService startup.
   * This arms exactly one framework-authenticated HELLO; unsolicited or
   * duplicate HELLO cannot replace a live approved worker session. */
  public void onTrustedServiceBindingInitiated(){
    onWorkerDisconnect();
    awaitingOneHello=true;
  }
  /** The binder is only offered to a non-exported same-package service. */
  public Messenger getTrustedHostInbox(){return hostInbox;}

  private static String bounded(Bundle b,String key,int max){
    if(b==null)return null;
    String s=b.getString(key);
    return s!=null&&s.length()<=max?s:null;
  }
  private boolean send(Messenger dest,int code,Bundle fields){
    if(dest==null)return false;
    Message m=Message.obtain(null,code);
    m.setData(fields);
    try{dest.send(m);return true;}catch(RemoteException fail){
      onWorkerDisconnect();
      return false;
    }
  }
  private void receiveHello(Message request){
    final int frameworkUid=request.sendingUid; // actual Android Binder identity
    if(!awaitingOneHello||request.replyTo==null||
        !Process.isIsolatedUid(frameworkUid))return;
    // A HELLO is always a new worker lifecycle; old grant is revoked.
    onWorkerDisconnect();
    String session=broker.bindAuthenticatedWorker(frameworkUid);
    if(session==null)return;
    currentSession=session;
    awaitingOneHello=false;
    isolatedUid=frameworkUid;
    isolatedReply=request.replyTo;
    Bundle reply=new Bundle();
    reply.putString("session",session);
    reply.putString("result","BOUND_NOT_APPROVED");
    send(isolatedReply,HELLO_REPLY,reply);
  }
  private void receiveRequest(Message request){
    if(request.replyTo==null)return;
    Bundle frame;
    try{frame=request.getData();}catch(RuntimeException bad){
      return; // malformed Parcel must not cause success.
    }
    final int frameworkUid=request.sendingUid; // never caller's JSON uid
    String session=bounded(frame,"session",64);
    String token=bounded(frame,"grant",64);
    String nodeFrame=bounded(frame,"nodeFrame",64);
    P32NodeIpcBroker.Decision result=broker.receiveAuthenticatedWorkerRequest(
        frameworkUid,session,token,nodeFrame);
    Bundle reply=new Bundle();
    reply.putString("result",result.outcome.name());
    if(result.allowed())reply.putInt("syntheticCount",result.count);
    // Never reply with raw node frame/token/path/secrets.
    send(request.replyTo,REQUEST_REPLY,reply);
  }
  /** Call ONLY from the trusted Activity's explicit user click handler.
   * Neither worker nor Node can call this method through Binder. */
  public boolean onTrustedUiApproveOnceClick(){
    if(currentSession==null||isolatedReply==null||isolatedUid<0)
      return false;
    String token=broker.approveOneSyntheticCountOnTrustedUiClick();
    if(token==null)return false;
    Bundle command=new Bundle();
    command.putString("session",currentSession);
    command.putString("grant",token);
    command.putString("scope",P17CapabilityGate.SCOPE_METADATA_COUNT);
    return send(isolatedReply,GRANT,command);
  }
  /** Trusted Activity onStop(), worker onServiceDisconnected/nullBinding/death */
  public void onTrustedUiBackground(){onWorkerDisconnect();}
  public void onBinderDeath(){onWorkerDisconnect();}
  public void onWorkerDisconnect(){
    broker.onWorkerServiceDisconnected();
    isolatedReply=null;isolatedUid=-1;currentSession=null;
    awaitingOneHello=false;
  }
}
