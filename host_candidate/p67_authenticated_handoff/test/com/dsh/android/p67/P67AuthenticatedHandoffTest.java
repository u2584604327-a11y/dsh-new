package com.dsh.android.p67;

import com.dsh.android.p53.P53StartOrder;
import com.dsh.p37.P37RemoteProcess;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

/** JVM-only malicious, early-exit, identity and stream boundary regression. */
public final class P67AuthenticatedHandoffTest {
  private static int checks;
  private static final int UID = 99055;
  private static final String SESSION =
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
  private static final P37RemoteProcess.IsolatedUidVerifier VERIFIER =
      frameworkUid -> frameworkUid == UID;
  private static void check(boolean pass, String label) {
    ++checks;
    if (!pass) throw new AssertionError("P67_" + label);
  }
  private static final class Control implements P37RemoteProcess.RemoteControl {
    int soft, hard;
    @Override public void requestGracefulStop(){soft++;}
    @Override public void requestForceStop(){hard++;}
  }
  private static P67AuthenticatedHandoff create(Control c) {
    return new P67AuthenticatedHandoff(UID, SESSION, VERIFIER, c);
  }
  private static boolean send(P67AuthenticatedHandoff h,int kind,long seq) {
    return h.onAuthenticatedFrame(UID, SESSION, kind, seq, null, 0);
  }
  private static boolean sendBytes(P67AuthenticatedHandoff h,int kind,long seq,byte[] payload) {
    return h.onAuthenticatedFrame(UID, SESSION, kind, seq, payload, 0);
  }
  public static void main(String[] args) throws Exception {
    Control control = new Control();
    P67AuthenticatedHandoff h = create(control);
    check(h.processAfterVerifiedChildStart()==null,"proxy_must_not_exist_initially");
    check(send(h,P53StartOrder.HELLO,0),"hello_accepted");
    check(h.processAfterVerifiedChildStart()==null,"hello_cannot_handoff");
    check(!h.hasVerifiedOriginalEngineReady(),"hello_cannot_ready");
    check(send(h,P53StartOrder.CHILD_STARTED,1),"verified_child_start");
    check(h.processAfterVerifiedChildStart()!=null,"proxy_after_real_ack");
    check(!h.hasVerifiedOriginalEngineReady(),"child_ack_not_ready");
    byte[] ordinaryStdout="some text, not a READY predicate".getBytes(StandardCharsets.US_ASCII);
    check(sendBytes(h,P53StartOrder.STDOUT,2,ordinaryStdout),"stdout");
    check(!h.hasVerifiedOriginalEngineReady(),"stdout_not_automatically_ready");
    Process p=h.processAfterVerifiedChildStart();
    byte[] actual=new byte[ordinaryStdout.length];
    check(p.getInputStream().read(actual)==actual.length,"exact_stdout_length");
    check(java.util.Arrays.equals(actual,ordinaryStdout),"exact_stdout_bytes");
    check(send(h,P53StartOrder.EXIT,3),"exit_allowed_before_ready");
    check(p.waitFor(0,TimeUnit.MILLISECONDS),"process_terminal");
    check(p.exitValue()==0,"exact_exit_code");
    check(!p.isAlive(),"no_phantom_running_process");
    check(!h.hasVerifiedOriginalEngineReady(),"exit_never_ready");
    check(!sendBytes(h,P53StartOrder.STDOUT,4,new byte[]{65}),"after_exit_denied");

    P67AuthenticatedHandoff early=create(new Control());
    check(send(early,P53StartOrder.HELLO,0),"early_hello");
    check(!sendBytes(early,P53StartOrder.STDOUT,1,new byte[]{1}),"stdout_before_start_denied");
    check(early.processAfterVerifiedChildStart()==null,"no_proxy_after_early_stream");
    check(early.isTerminal(),"early_stream_terminal");
    check(!send(early,P53StartOrder.CHILD_STARTED,1),"no_recovery_after_bad_order");

    Control mismatchControl=new Control();
    P67AuthenticatedHandoff mismatch=create(mismatchControl);
    check(send(mismatch,P53StartOrder.HELLO,0),"mismatch_hello");
    check(send(mismatch,P53StartOrder.CHILD_STARTED,1),"mismatch_started");
    Process remote=mismatch.processAfterVerifiedChildStart();
    check(!mismatch.onAuthenticatedFrame(UID+1,SESSION,P53StartOrder.STDOUT,
                                       2,new byte[]{9},0),"spoof_uid_denied");
    check(mismatch.isTerminal(),"identity_failure_terminal");
    check(remote.waitFor(0,TimeUnit.MILLISECONDS),"identity_failure_proxy_terminated");
    check(remote.exitValue()==P37RemoteProcess.SUPERVISOR_FAILURE_EXIT_CODE,
          "identity_failure_exit_125");
    check(mismatchControl.hard==1,"identity_failure_attempts_kill");

    P67AuthenticatedHandoff wrongSession=create(new Control());
    check(!wrongSession.onAuthenticatedFrame(UID,SESSION.substring(1),
          P53StartOrder.HELLO,0,null,0),"wrong_session_denied");
    check(wrongSession.isTerminal(),"wrong_session_terminal");

    Control controlOps=new Control();
    P67AuthenticatedHandoff stop=create(controlOps);
    check(send(stop,P53StartOrder.HELLO,0),"stop_hello");
    check(send(stop,P53StartOrder.CHILD_STARTED,1),"stop_start");
    Process controlled=stop.processAfterVerifiedChildStart();
    controlled.destroy();controlled.destroy();
    check(controlOps.soft==1,"graceful_stop_once");
    controlled.destroyForcibly();controlled.destroyForcibly();
    check(controlOps.hard==1,"force_stop_once");

    P67AuthenticatedHandoff failed=create(new Control());
    check(send(failed,P53StartOrder.HELLO,0),"fail_hello");
    check(send(failed,P53StartOrder.FAIL,1),"explicit_failure_accepted");
    check(failed.isTerminal(),"failure_is_terminal");
    check(failed.processAfterVerifiedChildStart()==null,"fail_never_handoff");

    P67AuthenticatedHandoff oversized=create(new Control());
    check(send(oversized,P53StartOrder.HELLO,0),"oversized_hello");
    check(send(oversized,P53StartOrder.CHILD_STARTED,1),"oversized_started");
    check(!sendBytes(oversized,P53StartOrder.STDOUT,2,
          new byte[P37RemoteProcess.MAX_FRAME_BYTES+1]),"frame_bound_enforced");
    check(oversized.isTerminal(),"oversized_terminal");

    P67AuthenticatedHandoff disconnected=create(new Control());
    check(send(disconnected,P53StartOrder.HELLO,0),"disconnected_hello");
    check(send(disconnected,P53StartOrder.CHILD_STARTED,1),"disconnected_started");
    disconnected.onTransportLost();
    check(disconnected.isTerminal(),"binder_death_terminal");
    check(!send(disconnected,P53StartOrder.EXIT,2),"binder_death_no_exit_recovery");

    boolean constructorDenied=false;
    try { new P67AuthenticatedHandoff(UID, "bad", VERIFIER, new Control()); }
    catch(IllegalArgumentException expected){constructorDenied=true;}
    check(constructorDenied,"session_shape_rejected");
    System.out.println("P67_AUTHENTICATED_P53_P37_JVM_TESTS=PASS assertions="+checks);
    System.out.println("P67_HELLO_IS_NOT_CHILD_STARTED_OR_READY=PASS");
    System.out.println("P67_PROXY_ONLY_AFTER_AUTH_CHILD_STARTED=PASS");
    System.out.println("P67_ORIGINAL_ENGINE_READY=NOT_IMPLEMENTED");
    System.out.println("P67_ORIGINAL_ANDROID_BINDER_INTEGRATION=NOT_IMPLEMENTED");
    System.out.println("P67_SIGNED_PRODUCTION_APK=BLOCKED");
  }
}
