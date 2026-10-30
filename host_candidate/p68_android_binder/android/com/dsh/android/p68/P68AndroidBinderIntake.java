package com.dsh.android.p68;
import android.os.Bundle;
import android.os.Message;
import com.dsh.android.p53.P53StartOrder;
import com.dsh.android.p67.P67AuthenticatedHandoff;
import com.dsh.p37.P37RemoteProcess;
import java.util.Set;

/** Android framework sendingUid -> P67 ordered child-start -> P37 Process.
 * Test fixture only. HELLO never creates or hands out Process; no engine READY.
 */
public final class P68AndroidBinderIntake {
  public enum Result { HELLO, CHILD_STARTED, STDOUT, STDERR, EXIT, FAIL, REJECTED }
  private static final int MAX_FIXTURE_BYTES=128;
  private final String trustedSession;
  private final P37RemoteProcess.RemoteControl controls;
  private P67AuthenticatedHandoff handoff;
  private int isolatedUid=-1;
  private boolean invalid;
  public P68AndroidBinderIntake(String hostGeneratedSession,
                                 P37RemoteProcess.RemoteControl stopControls) {
    if(stopControls==null || hostGeneratedSession==null ||
       !hostGeneratedSession.matches("[a-f0-9]{64}"))
      throw new IllegalArgumentException("P68_TRUSTED_HOST_SESSION_REQUIRED");
    trustedSession=hostGeneratedSession;
    controls=stopControls;
  }
  private static boolean exactShape(Bundle b,int kind) {
    if(b==null || !b.containsKey("session") || !b.containsKey("seq"))return false;
    Set<String> keys=b.keySet();
    for(String key:keys){
      if("session".equals(key)||"seq".equals(key))continue;
      if("data".equals(key) &&
         (kind==P53StartOrder.STDOUT||kind==P53StartOrder.STDERR))continue;
      if("exitCode".equals(key)&&kind==P53StartOrder.EXIT)continue;
      return false;
    }
    if(kind==P53StartOrder.EXIT)
      return b.containsKey("exitCode")&&!b.containsKey("data");
    if(kind==P53StartOrder.STDOUT||kind==P53StartOrder.STDERR)
      return b.containsKey("data")&&!b.containsKey("exitCode");
    return (kind==P53StartOrder.HELLO||
            kind==P53StartOrder.CHILD_STARTED||
            kind==P53StartOrder.FAIL)&&
            !b.containsKey("data")&&!b.containsKey("exitCode");
  }
  private Result reject() {
    invalid=true;
    if(handoff!=null)handoff.onTransportLost();
    return Result.REJECTED;
  }
  public synchronized Result accept(Message msg) {
    if(invalid || (handoff!=null&&handoff.isTerminal()) || msg==null)
      return Result.REJECTED;
    try {
      int sender=msg.sendingUid;
      if(sender<0 || sender==android.os.Process.myUid() ||
         !android.os.Process.isIsolatedUid(sender))return reject();
      Bundle b=msg.getData();
      if(!exactShape(b,msg.what))return reject();
      String session=b.getString("session");
      long sequence=b.getLong("seq",Long.MIN_VALUE);
      if(!trustedSession.equals(session))return reject();
      if(handoff==null) {
        if(msg.what!=P53StartOrder.HELLO||sequence!=0)return reject();
        isolatedUid=sender;
        handoff=new P67AuthenticatedHandoff(
            isolatedUid,trustedSession,android.os.Process::isIsolatedUid,
            controls);
      }else if(sender!=isolatedUid)return reject();
      byte[] data=null;
      if(msg.what==P53StartOrder.STDOUT||msg.what==P53StartOrder.STDERR){
        data=b.getByteArray("data");
        if(data==null||data.length<1||data.length>MAX_FIXTURE_BYTES)
          return reject();
      }
      int code=msg.what==P53StartOrder.EXIT?
          b.getInt("exitCode",P37RemoteProcess.SUPERVISOR_FAILURE_EXIT_CODE):0;
      if(!handoff.onAuthenticatedFrame(sender,session,msg.what,sequence,data,code))
        return reject();
      if(msg.what==P53StartOrder.HELLO)return Result.HELLO;
      if(msg.what==P53StartOrder.CHILD_STARTED)return Result.CHILD_STARTED;
      if(msg.what==P53StartOrder.STDOUT)return Result.STDOUT;
      if(msg.what==P53StartOrder.STDERR)return Result.STDERR;
      if(msg.what==P53StartOrder.EXIT)return Result.EXIT;
      if(msg.what==P53StartOrder.FAIL)return Result.FAIL;
      return reject();
    }catch(RuntimeException invalidFrame){return reject();}
  }
  public synchronized int isolatedUid(){return isolatedUid;}
  public synchronized Process processAfterAuthenticatedChildStart(){
    return !invalid && handoff!=null && handoff.hasVerifiedChildStart() ?
        handoff.processAfterVerifiedChildStart():null;
  }
  public synchronized boolean engineReady(){
    return handoff!=null && handoff.hasVerifiedOriginalEngineReady();
  }
  public synchronized boolean isTerminal(){
    return invalid || (handoff!=null&&handoff.isTerminal());
  }
  public synchronized void disconnected(){reject();}
}
