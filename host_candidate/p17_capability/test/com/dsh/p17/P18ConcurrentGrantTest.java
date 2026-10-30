package com.dsh.p17;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/** Deterministic stress gate: one native-approved grant cannot authorize
 * multiple worker IPC requests even when they arrive simultaneously.
 * Source-only JVM regression, not Android Binder integration evidence.
 */
public final class P18ConcurrentGrantTest {
  static void check(boolean ok,String reason){
    if(!ok)throw new AssertionError(reason);
  }
  public static void main(String[] args)throws Exception{
    final P17CapabilityGate gate=new P17CapabilityGate(()->1000L);
    final int workerUid=91042;
    final String grant=gate.approveOnce(P17CapabilityGate.SCOPE_METADATA_COUNT,
                                       workerUid,10000L);
    final int workers=64;
    final CountDownLatch ready=new CountDownLatch(workers);
    final CountDownLatch start=new CountDownLatch(1);
    final CountDownLatch done=new CountDownLatch(workers);
    final AtomicInteger accepted=new AtomicInteger();
    final AtomicInteger unexpected=new AtomicInteger();
    for(int i=0;i<workers;i++){
      Thread t=new Thread(()->{
        try{
          ready.countDown();
          if(!start.await(10,TimeUnit.SECONDS)){
            unexpected.incrementAndGet();return;
          }
          if(gate.consume(grant,P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid))
            accepted.incrementAndGet();
        }catch(Throwable e){unexpected.incrementAndGet();}
        finally{done.countDown();}
      },"p18-grant-race-"+i);
      t.setDaemon(true);
      t.start();
    }
    check(ready.await(10,TimeUnit.SECONDS),"workers not ready");
    start.countDown();
    check(done.await(10,TimeUnit.SECONDS),"workers did not complete");
    check(unexpected.get()==0,"exceptions or timeouts in worker requests");
    check(accepted.get()==1,"replay race accepted multiple requests");
    check(gate.outstanding()==0,"consumed grant remains outstanding");

    final String second=gate.approveOnce(P17CapabilityGate.SCOPE_METADATA_COUNT,
                                         workerUid,10000L);
    check(!gate.consume(second,"READ_PRIVATE_FILES",workerUid),"scope escape");
    check(!gate.consume(second,P17CapabilityGate.SCOPE_METADATA_COUNT,workerUid),
          "invalid scope failed to burn grant");
    check(gate.outstanding()==0,"denied grant remains outstanding");
    System.out.println("P18_CONCURRENT_EXACTLY_ONE_ACCEPTED=PASS_JVM");
    System.out.println("P18_BAD_SCOPE_BURNS_GRANT=PASS_JVM");
    System.out.println("P18_ANDROID_BINDER_INTEGRATION=NOT_TESTED_JVM");
  }
}
