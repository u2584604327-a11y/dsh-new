package com.dsh.p32;

import com.dsh.p17.P17CapabilityGate;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/** Deterministic JDK-only native host policy regressions (not OS Binder). */
public final class P32NodeIpcBrokerTest {
  static final class Clock implements P17CapabilityGate.MonotonicClock {
    final AtomicLong time=new AtomicLong(123_000);
    @Override public long nowMs(){return time.get();}
    void advance(long n){time.addAndGet(n);}
  }
  private static final int WORKER_UID=99055;
  private static final int HOST_UID=10234;
  private static final String GOOD="{\"op\":\"METADATA_COUNT\",\"limit\":3}";
  private static void eq(Object actual,Object expected,String label){
    if(!java.util.Objects.equals(expected,actual))
      throw new AssertionError(label+": "+actual+" != "+expected);
  }
  private static void yes(boolean b,String label){
    if(!b)throw new AssertionError(label);
  }
  private static P32NodeIpcBroker fresh(Clock clk){
    return new P32NodeIpcBroker(clk,uid->uid>=99000&&uid<=99999);
  }
  private static void malformedBurn(P32NodeIpcBroker b,String session,String payload){
    String token=b.approveOneSyntheticCountOnTrustedUiClick();
    yes(token!=null,"trusted click token");
    eq(b.receiveAuthenticatedWorkerRequest(WORKER_UID,session,token,payload).outcome,
       P32NodeIpcBroker.Outcome.DENY_BAD_FRAME,"invalid frame");
    eq(b.receiveAuthenticatedWorkerRequest(WORKER_UID,session,token,GOOD).outcome,
       P32NodeIpcBroker.Outcome.DENY_NO_GRANT,"burn invalid frame");
  }
  private static void run()throws Exception {
    Clock c=new Clock();
    P32NodeIpcBroker b=fresh(c);
    eq(b.bindAuthenticatedWorker(HOST_UID),null,"host cannot pretend isolated");
    eq(b.approveOneSyntheticCountOnTrustedUiClick(),null,"no grant before binding");
    String session=b.bindAuthenticatedWorker(WORKER_UID);
    yes(session!=null&&session.length()==64,"host minted session");
    eq(b.receiveAuthenticatedWorkerRequest(WORKER_UID,session,null,GOOD).outcome,
      P32NodeIpcBroker.Outcome.DENY_NO_GRANT,"no silent preapproval");
    String token=b.approveOneSyntheticCountOnTrustedUiClick();
    yes(token!=null&&token.length()==64,"one-shot grant");
    eq(b.outstandingForTests(),1,"grant stored only in host");
    P32NodeIpcBroker.Decision ok=b.receiveAuthenticatedWorkerRequest(WORKER_UID,session,token,GOOD);
    eq(ok.outcome,P32NodeIpcBroker.Outcome.ALLOW_COUNT,"approved fixed count");
    eq(ok.count,3,"synthetic metadata count");
    eq(b.outstandingForTests(),0,"grant fully burned");
    eq(b.receiveAuthenticatedWorkerRequest(WORKER_UID,session,token,GOOD).outcome,
      P32NodeIpcBroker.Outcome.DENY_NO_GRANT,"replay denied");
    malformedBurn(b,session,"{\"op\":\"FILE_READ\",\"limit\":3}");
    malformedBurn(b,session,"{\"op\":\"METADATA_COUNT\",\"limit\":3,\"url\":\"file:///data/data\"}");
    malformedBurn(b,session,"{\"op\":\"METADATA_COUNT\",\"limit\":0}");
    malformedBurn(b,session,"{\"op\":\"METADATA_COUNT\",\"limit\":9}");
    malformedBurn(b,session,"{\"op\":\"METADATA_COUNT\",\"limit\":03}");
    malformedBurn(b,session,GOOD+" ");
    malformedBurn(b,session,GOOD+GOOD+GOOD+GOOD);
    malformedBurn(b,session,"[{\"op\":\"METADATA_COUNT\",\"limit\":3}]");
    malformedBurn(b,session,"{\"op\":\"METADATA_COUNT\",\"limit\":3}\n{\"op\":\"METADATA_COUNT\",\"limit\":3}");

    String t=b.approveOneSyntheticCountOnTrustedUiClick();
    c.advance(10_001);
    eq(b.receiveAuthenticatedWorkerRequest(WORKER_UID,session,t,GOOD).outcome,
       P32NodeIpcBroker.Outcome.DENY_NO_GRANT,"grant TTL monotonic expiration");
    c.advance(1);

    t=b.approveOneSyntheticCountOnTrustedUiClick();
    eq(b.receiveAuthenticatedWorkerRequest(HOST_UID,session,t,GOOD).outcome,
       P32NodeIpcBroker.Outcome.DENY_UNTRUSTED_SENDER,"nonisolated host forged sender");
    eq(b.receiveAuthenticatedWorkerRequest(WORKER_UID,session,t,GOOD).outcome,
       P32NodeIpcBroker.Outcome.DENY_NOT_BOUND,"wrong UID burns and unbinds");
    session=b.bindAuthenticatedWorker(WORKER_UID);
    t=b.approveOneSyntheticCountOnTrustedUiClick();
    eq(b.receiveAuthenticatedWorkerRequest(WORKER_UID,"wrong-session",t,GOOD).outcome,
       P32NodeIpcBroker.Outcome.DENY_WRONG_SESSION,"session mismatch");
    eq(b.receiveAuthenticatedWorkerRequest(WORKER_UID,session,t,GOOD).outcome,
       P32NodeIpcBroker.Outcome.DENY_NOT_BOUND,"wrong session revokes whole binding");
    session=b.bindAuthenticatedWorker(WORKER_UID);

    t=b.approveOneSyntheticCountOnTrustedUiClick();
    b.onTrustedUiBackground();
    eq(b.receiveAuthenticatedWorkerRequest(WORKER_UID,session,t,GOOD).outcome,
       P32NodeIpcBroker.Outcome.DENY_NOT_BOUND,"UI background revocation");
    eq(b.outstandingForTests(),0,"UI background grant cleared");

    session=b.bindAuthenticatedWorker(WORKER_UID);
    t=b.approveOneSyntheticCountOnTrustedUiClick();
    b.onWorkerServiceDisconnected();
    eq(b.receiveAuthenticatedWorkerRequest(WORKER_UID,session,t,GOOD).outcome,
       P32NodeIpcBroker.Outcome.DENY_NOT_BOUND,"worker death revocation");
    session=b.bindAuthenticatedWorker(WORKER_UID);
    t=b.approveOneSyntheticCountOnTrustedUiClick();
    b.onBinderDeath();
    eq(b.receiveAuthenticatedWorkerRequest(WORKER_UID,session,t,GOOD).outcome,
       P32NodeIpcBroker.Outcome.DENY_NOT_BOUND,"binder death revocation");

    String first=b.bindAuthenticatedWorker(WORKER_UID);
    String oldGrant=b.approveOneSyntheticCountOnTrustedUiClick();
    String second=b.bindAuthenticatedWorker(WORKER_UID);
    yes(!first.equals(second),"session minted unique per binder");
    eq(b.receiveAuthenticatedWorkerRequest(WORKER_UID,first,oldGrant,GOOD).outcome,
       P32NodeIpcBroker.Outcome.DENY_WRONG_SESSION,"old session rejected");

    eq(b.approveOneSyntheticCountOnTrustedUiClick(),null,
       "stale session requires trusted fresh handshake");
    String third=b.bindAuthenticatedWorker(WORKER_UID);
    yes(!third.equals(second),"new bind after mismatch");
    String current=b.approveOneSyntheticCountOnTrustedUiClick();
    eq(b.receiveAuthenticatedWorkerRequest(WORKER_UID,third,current,
        "{\"op\":\"METADATA_COUNT\",\"limit\":8}").count,8,
        "upper allowed bound");

    // Concurrent spoofed duplicate calls cannot spend same grant twice.
    final String parallelSession=b.bindAuthenticatedWorker(WORKER_UID);
    final String parallelToken=b.approveOneSyntheticCountOnTrustedUiClick();
    final CountDownLatch ready=new CountDownLatch(20);
    final CountDownLatch fire=new CountDownLatch(1);
    ExecutorService pool=Executors.newFixedThreadPool(20);
    List<Future<P32NodeIpcBroker.Outcome>> futures=new ArrayList<>();
    for(int i=0;i<20;i++){
      futures.add(pool.submit(new Callable<P32NodeIpcBroker.Outcome>(){
        @Override public P32NodeIpcBroker.Outcome call()throws Exception{
          ready.countDown();
          if(!fire.await(4,TimeUnit.SECONDS))
            throw new AssertionError("parallel test barrier timeout");
          return b.receiveAuthenticatedWorkerRequest(WORKER_UID,
            parallelSession,parallelToken,GOOD).outcome;
        }
      }));
    }
    yes(ready.await(4,TimeUnit.SECONDS),"parallel clients reached gate");
    fire.countDown();
    int allowed=0,denied=0;
    for(Future<P32NodeIpcBroker.Outcome> f:futures){
      P32NodeIpcBroker.Outcome o=f.get(4,TimeUnit.SECONDS);
      if(o==P32NodeIpcBroker.Outcome.ALLOW_COUNT)allowed++;
      else if(o==P32NodeIpcBroker.Outcome.DENY_NO_GRANT)denied++;
      else throw new AssertionError("Unexpected parallel outcome:"+o);
    }
    pool.shutdownNow();
    eq(allowed,1,"single allowed concurrent request");
    eq(denied,19,"other 19 replays denied");
    eq(b.outstandingForTests(),0,"no residual grant");
    System.out.println("P32_ONE_SHOT_BINDER_POLICY_SYNTHETIC_TESTS=PASS");
    System.out.println("P32_NO_AUTHORIZATION_WITHOUT_TRUSTED_UI=PASS");
    System.out.println("P32_SCOPE_STRICT_NODE_STDOUT_AND_SIZE_BOUND=PASS");
    System.out.println("P32_TOKEN_EXPIRY_AND_LIFECYCLE_REVOKE=PASS");
    System.out.println("P32_PARALLEL_ONESHOT_1_OF_20=PASS");
    System.out.println("P32_ACTUAL_DSH_HOST_RUNTIME_CONNECTION=NOT_IMPLEMENTED");
    System.out.println("P32_RELEASE=BLOCKED");
  }
  public static void main(String[] args)throws Exception{run();}
}
