package com.dsh.p17;
import java.util.HashSet;
public final class P17GateTest {
  static final class FakeClock implements P17CapabilityGate.MonotonicClock {
    long t=10000;public long nowMs(){return t;}
  }
  static void ok(boolean value,String name){if(!value)throw new AssertionError(name);}
  static void denied(Runnable block,String name){
    try{block.run();throw new AssertionError(name);}catch(IllegalArgumentException expected){}
  }
  public static void main(String[] args){
    FakeClock c=new FakeClock();P17CapabilityGate g=new P17CapabilityGate(c);
    final int workerUid=91042,hostUid=10420;
    ok(!g.consume("abc",P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid),"pregrant");
    denied(()->g.approveOnce("READ_LOG_FILE",workerUid,1000),"arbitrary file grant");
    denied(()->g.approveOnce("NETWORK_ANY",workerUid,1000),"arbitrary network grant");
    denied(()->g.approveOnce(P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid,60000),"long TTL");
    denied(()->g.approveOnce(P17CapabilityGate.SCOPE_METADATA_COUNT,-1,100),"invalid UID");
    String a=g.approveOnce(P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid,1000);
    ok(a.length()==64&&a.matches("[0-9a-f]{64}"),"cryptographic nonce");
    ok(g.outstanding()==1,"outstanding");
    ok(!g.consume(a,"READ_LOG_FILE",workerUid),"wrong scope");
    ok(!g.consume(a,P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid),"wrong scope burns grant");
    a=g.approveOnce(P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid,1000);
    ok(!g.consume(a,P17CapabilityGate.SCOPE_METADATA_COUNT,hostUid),"incorrect Binder UID");
    ok(!g.consume(a,P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid),"wrong UID burns grant");
    a=g.approveOnce(P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid,1000);
    ok(g.consume(a,P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid),"approved one shot");
    ok(!g.consume(a,P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid),"replay prevented");
    a=g.approveOnce(P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid,1000);
    c.t+=1000;
    ok(!g.consume(a,P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid),"expired denied");
    a=g.approveOnce(P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid,1000);
    g.revoke(a);
    ok(!g.consume(a,P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid),"revocation");
    a=g.approveOnce(P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid,1000);
    g.revokeAll();
    ok(!g.consume(a,P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid),"process death revocation");
    HashSet<String> unique=new HashSet<>();
    for(int i=0;i<16;i++)unique.add(g.approveOnce(P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid,1000));
    ok(unique.size()==16,"unique nonces");
    boolean full=false;
    try{g.approveOnce(P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid,1000);}
    catch(IllegalStateException e){full=true;}
    ok(full,"outstanding bound");
    c.t+=1001;
    ok(g.outstanding()==0,"expired grant cleanup");
    System.out.println("P17_SCOPE_ONLY_METADATA_COUNT=PASS");
    System.out.println("P17_UID_BINDING_AND_BURN_ON_FAILURE=PASS");
    System.out.println("P17_SINGLE_USE_REPLAY_EXPIRE_REVOKE=PASS");
    System.out.println("P17_RANDOM_TOKENS_AND_QUOTA=PASS");
    System.out.println("P17_ANDROID_BINDER_AUTHENTICATED_UID=NOT_TESTED");
    System.out.println("P17_DSH_NODE_MIGRATION=NOT_DONE");
  }
}
