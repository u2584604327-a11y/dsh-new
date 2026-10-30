package com.dsh.android.p47;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
public final class P47LaunchGateTest {
  private static int checks;
  private static void yes(boolean b,String label) {
    checks++;
    if(!b)throw new AssertionError(label);
  }
  private static void deny(ProcessBuilder pb,String expected) {
    checks++;
    try {
      Process p=P47LaunchGate.startOrDeny(pb);
      if(p!=null)p.destroyForcibly();
      throw new AssertionError("host process unexpectedly started");
    }catch(IOException correct) {
      if(!expected.equals(correct.getMessage()))
        throw new AssertionError("wrong denial class/message",correct);
    }
  }
  public static void main(String[] args) throws Exception {
    File canary=File.createTempFile("p47-deny-",".txt");
    yes(canary.delete(),"canary should be absent");
    String command="printf UNAUTHORIZED > "+canary.getAbsolutePath();
    ProcessBuilder pb=new ProcessBuilder("sh","-c",command);
    pb.redirectErrorStream(true);
    pb.environment().put("P47_SYNTHETIC_TEST_SECRET","MUST_NOT_BE_LOGGED");
    P47LaunchGate.Shape s=P47LaunchGate.categorize(pb);
    yes(s.argvCount==3,"arg count");
    yes(!s.hasDirectory,"cwd default");
    yes(s.stderrMerged,"stderr config");
    yes(s.environmentEntries>0,"env count");
    deny(pb,"P47_ISOLATED_SUPERVISOR_UNAVAILABLE_NO_HOST_FALLBACK");
    yes(!canary.exists(),"no file created by unauthorized host launch");
    pb.directory(new File("."));
    yes(P47LaunchGate.categorize(pb).hasDirectory,"cwd category");
    deny(pb,"P47_ISOLATED_SUPERVISOR_UNAVAILABLE_NO_HOST_FALLBACK");
    deny(new ProcessBuilder(),"P47_INVALID_ORIGINAL_LAUNCH_SHAPE");
    List<String> oversized=new ArrayList<>();
    for(int i=0;i<129;i++)oversized.add("a");
    deny(new ProcessBuilder(oversized),"P47_INVALID_ORIGINAL_LAUNCH_SHAPE");
    yes(!canary.exists(),"no unexpected process after negative tests");
    System.out.println("P47_JAVA_PROCESS_BUILDER_DENY_TESTS=PASS assertions="+checks);
    System.out.println("P47_NO_HOST_SPAWN_CANARY=PASS");
    System.out.println("P47_ENGINE_WORKER_READY=NO");
  }
}
