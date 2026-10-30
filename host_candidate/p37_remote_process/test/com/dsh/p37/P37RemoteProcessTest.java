package com.dsh.p37;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

/** No Android stubs, APK, network, personal data or original DSH files. */
public final class P37RemoteProcessTest {
  private static final String S = new String(new char[64]).replace('\0','a');
  private static final int UID=99055;
  private static final AtomicInteger checks=new AtomicInteger();
  private static void ok(boolean b,String message) {
    checks.incrementAndGet();
    if (!b) throw new AssertionError(message);
  }
  private static class Port implements P37RemoteProcess.RemoteControl {
    int stop=0,kill=0;
    boolean failStop=false,failKill=false;
    @Override public void requestGracefulStop() {
      stop++;if(failStop)throw new IllegalStateException("lost");
    }
    @Override public void requestForceStop() {
      kill++;if(failKill)throw new IllegalStateException("lost");
    }
  }
  private static P37RemoteProcess start(Port p) {
    return new P37RemoteProcess(UID,S,uid->uid==UID,p);
  }
  private static byte[] b(String s) {return s.getBytes(StandardCharsets.UTF_8);}
  private static String readAll(InputStream input)throws Exception {
    ByteArrayOutputStream result=new ByteArrayOutputStream();
    byte[] tmp=new byte[200];int n;
    while((n=input.read(tmp))!=-1)result.write(tmp,0,n);
    return new String(result.toByteArray(),StandardCharsets.UTF_8);
  }
  private static void testLifecycle()throws Exception {
    Port port=new Port(); P37RemoteProcess p=start(port);
    ok(p.isAlive(),"alive at create");
    try {p.exitValue();throw new AssertionError("exitValue did not throw");}
    catch(IllegalThreadStateException expected){checks.incrementAndGet();}
    ok(!p.waitFor(0,TimeUnit.MILLISECONDS),"nonblocking wait should timeout");
    ExecutorService e=Executors.newSingleThreadExecutor();
    Future<String> reader=e.submit(()->readAll(p.getInputStream()));
    ok(p.onAuthenticatedStdout(UID,S,b("boot\n")),"stdout accepted");
    ok(p.onAuthenticatedStdout(UID,S,b("ready:1604\n")),"second chunk accepted");
    ok(p.onAuthenticatedStderr(UID,S,b("log\n")),"stderr accepted");
    p.destroy(); p.destroy();
    ok(port.stop==1,"stop idempotent");
    ok(p.isAlive(),"not exited until worker exit");
    ok(p.onAuthenticatedExit(UID,S,0),"verified exit");
    ok(!p.isAlive()&&p.exitValue()==0&&p.waitFor(1,TimeUnit.SECONDS),"clean exit");
    ok("boot\nready:1604\n".equals(reader.get(2,TimeUnit.SECONDS)),"ordered stdout and EOF");
    ok("log\n".equals(readAll(p.getErrorStream())),"separate stderr");
    ok(!p.onAuthenticatedExit(UID,S,17),"duplicate exit rejected");
    ok(p.waitFor()==0,"waitFor stable");
    e.shutdownNow();
  }
  private static void testIsolationAndReplay()throws Exception {
    Port port=new Port(); P37RemoteProcess p=start(port);
    ok(!p.onAuthenticatedStdout(10001,S,b("ready\n")),"fake UID rejected");
    ok(p.terminalReason()==P37RemoteProcess.TerminalReason.IDENTITY_MISMATCH,"identity terminal");
    ok(p.waitFor()==125 && port.kill==1,"kill requested and synthetic failure");
    ok(p.getInputStream().read()==-1,"bad payload discarded");
    ok(!p.onAuthenticatedStdout(UID,S,b("ready\n")),"no reuse after failure");
    Port port2=new Port();P37RemoteProcess q=start(port2);
    ok(!q.onAuthenticatedStderr(UID,S.substring(1),b("wrong")),"session denied");
    ok(port2.kill==1&&q.waitFor()==125,"session mismatch revokes");
  }
  private static void testBoundedBuffer()throws Exception {
    Port port=new Port();P37RemoteProcess p=start(port);
    byte[] chunk=new byte[P37RemoteProcess.MAX_FRAME_BYTES];
    Arrays.fill(chunk,(byte)'x');
    for(int i=0;i<16;i++)ok(p.onAuthenticatedStdout(UID,S,chunk),"buffer chunk " +i);
    ok(!p.onAuthenticatedStdout(UID,S,b("overflow")),"no unbounded queue");
    ok(p.terminalReason()==P37RemoteProcess.TerminalReason.BUFFER_OVERFLOW,"overflow reason");
    ok(port.kill==1&&p.waitFor()==125,"overflow kill request");
    ok(p.getInputStream().read()==-1,"overflow discards buffered secret/ready tokens");
    Port port2=new Port();P37RemoteProcess q=start(port2);
    ok(!q.onAuthenticatedStdout(UID,S,new byte[P37RemoteProcess.MAX_FRAME_BYTES+1]),"max chunk");
    ok(q.terminalReason()==P37RemoteProcess.TerminalReason.BUFFER_OVERFLOW,"oversize terminal");
  }
  private static void testTimeoutAndDisconnect()throws Exception {
    Port p1=new Port();P37RemoteProcess p=start(p1);
    ExecutorService e=Executors.newSingleThreadExecutor();
    Future<Integer> blocked=e.submit(()->p.getInputStream().read());
    p.onTransportLost();
    ok(blocked.get(2,TimeUnit.SECONDS)==-1,"stream interrupted on disconnect");
    ok(p.waitFor()==125 && p.terminalReason()==P37RemoteProcess.TerminalReason.TRANSPORT_LOST,"disconnect fail closed");
    ok(p1.kill==1,"kill requested on disconnect");
    e.shutdownNow();
    Port p2=new Port();P37RemoteProcess q=start(p2);
    q.destroyForcibly();q.destroyForcibly();
    ok(p2.kill==1 && q.isAlive(),"kill sent once, no fake ack");
    q.onStopDeadlineExpired();
    ok(q.waitFor()==125 && p2.kill==1,"deadline terminal");
  }
  private static void testStdinAndFailures()throws Exception {
    Port port=new Port();P37RemoteProcess p=start(port);
    try {p.getOutputStream().write(b("bad command"));throw new AssertionError("stdin open");}
    catch(IOException expected){checks.incrementAndGet();}
    port.failStop=true;
    p.destroy();
    ok(p.waitFor()==125,"control failure burns process");
    ok(p.terminalReason()==P37RemoteProcess.TerminalReason.REMOTE_CONTROL_FAILURE,"control failure state");
    Port invalid=new Port();
    try {new P37RemoteProcess(10000,S,uid->false,invalid);throw new AssertionError("wrong uid accepted");}
    catch(IllegalArgumentException expected){checks.incrementAndGet();}
  }
  public static void main(String[] args)throws Exception {
    testLifecycle();testIsolationAndReplay();testBoundedBuffer();
    testTimeoutAndDisconnect();testStdinAndFailures();
    System.out.println("P37_JAVA_PROCESS_LIFECYCLE_PROXY_TESTS=PASS assertions="+checks);
    System.out.println("P37_ORIGINAL_ENGINEMANAGER_WIRING=NO");
    System.out.println("P37_ANDROID_BINDER_RUNTIME_E2E=NOT_TESTED");
    System.out.println("P37_V139_RELEASE=BLOCKED");
  }
}
