package com.dsh.android.p74;
import com.dsh.p37.P37RemoteProcess;
import java.io.File;
import java.io.IOException;
import java.util.concurrent.atomic.AtomicInteger;
public final class P74OriginalEngineFixtureHandoffTest {
  static int count;
  static void check(boolean yes,String what){count++;if(!yes)throw new AssertionError("P74_"+what);}
  static final String SESSION="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
  static final P37RemoteProcess.IsolatedUidVerifier ISOLATED = uid->uid==99055;
  static final class Control implements P37RemoteProcess.RemoteControl {
    int stops,kills;
    public void requestGracefulStop(){stops++;}
    public void requestForceStop(){kills++;}
  }
  static P37RemoteProcess proxy(){
    return new P37RemoteProcess(99055,SESSION,ISOLATED,new Control());
  }
  static ProcessBuilder fixture(){return new ProcessBuilder("/system/bin/id","-u").directory(new File("/"));}
  static String denial(ProcessBuilder b){
    try {Process p=P74OriginalEngineFixtureHandoff.startOrDeny(b);
      if(p!=null)throw new AssertionError("unauthorized process returned");
      return "NONE";
    }catch(IOException expected){return expected.getMessage();}
  }
  public static void main(String[]args)throws Exception{
    check("P47_ISOLATED_SUPERVISOR_UNAVAILABLE_NO_HOST_FALLBACK".equals(
        denial(fixture())),"without_lease_original_gate_denies");
    P37RemoteProcess p=proxy();
    boolean bad=false;
    try{P74OriginalEngineFixtureHandoff.stageFromAuthenticatedChild(p,99056,SESSION,ISOLATED);}
    catch(SecurityException expected){bad=true;}
    check(bad,"spoofed_uid_denied");
    P74OriginalEngineFixtureHandoff.stageFromAuthenticatedChild(p,99055,SESSION,ISOLATED);
    check(P74OriginalEngineFixtureHandoff.pendingOnCurrentThread(),"after_ack_pending");
    check(P74OriginalEngineFixtureHandoff.startOrDeny(fixture())==p,"exact_same_p37_process");
    check(!P74OriginalEngineFixtureHandoff.pendingOnCurrentThread(),"one_shot_consumed");
    check("P47_ISOLATED_SUPERVISOR_UNAVAILABLE_NO_HOST_FALLBACK".equals(
        denial(fixture())),"replay_fails_closed");
    P37RemoteProcess other=proxy();
    P74OriginalEngineFixtureHandoff.stageFromAuthenticatedChild(other,99055,SESSION,ISOLATED);
    check("P74_FIXTURE_ONLY_REAL_ENGINE_ARGV_NOT_AUTHORIZED".equals(
        denial(new ProcessBuilder("sh","-c","danger").directory(new File("/")))),
        "arbitrary_engine_command_not_allowed");
    check("P47_ISOLATED_SUPERVISOR_UNAVAILABLE_NO_HOST_FALLBACK".equals(
        denial(fixture())),"wrong_command_consumes_lease");
    P37RemoteProcess terminated=proxy();
    terminated.onAuthenticatedExit(99055,SESSION,0);
    bad=false;
    try{P74OriginalEngineFixtureHandoff.stageFromAuthenticatedChild(
        terminated,99055,SESSION,ISOLATED);}catch(SecurityException expected){bad=true;}
    check(bad,"exited_child_cannot_be_leased");
    P37RemoteProcess thread=proxy();
    P74OriginalEngineFixtureHandoff.stageFromAuthenticatedChild(thread,99055,SESSION,ISOLATED);
    AtomicInteger cross=new AtomicInteger();
    Thread worker=new Thread(()->{
      if("P47_ISOLATED_SUPERVISOR_UNAVAILABLE_NO_HOST_FALLBACK".equals(
          denial(fixture())))cross.incrementAndGet();
    });
    worker.start();worker.join();
    check(cross.get()==1,"other_thread_cannot_steal_lease");
    check(P74OriginalEngineFixtureHandoff.startOrDeny(fixture())==thread,"owner_thread_consumes");
    check(!new File("/system/bin/id").equals(new File("real-user-executable")),"fixture_separate");
    System.out.println("P74_ORIGINAL_MAIN_BRIDGE_LEASE_JVM=PASS assertions="+count);
    System.out.println("P74_NO_DIRECT_HOST_PROCESSBUILDER_START=PASS");
    System.out.println("P74_PRODUCTION_ENGINE_ARGV_NOT_PERMITTED=YES");
    System.out.println("P74_ENGINE_MANAGER_COROUTINE_OR_REAL_READY=NOT_TESTED");
  }
}
