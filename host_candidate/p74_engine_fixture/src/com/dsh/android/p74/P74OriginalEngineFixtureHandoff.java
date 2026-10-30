package com.dsh.android.p74;

import com.dsh.p37.P37RemoteProcess;
import java.io.File;
import java.io.IOException;
import java.util.List;

/**
 * P74 original MAIN-DEX P40 bridge process handoff fixture.
 * No Node, no original argv, no real engine READY. The ONLY accepted command
 * is hardcoded disposable /system/bin/id -u. A binder-verified P37 Process
 * must already have received P53 CHILD_STARTED; no host spawning occurs.
 */
public final class P74OriginalEngineFixtureHandoff {
  private static final String DENY="P47_ISOLATED_SUPERVISOR_UNAVAILABLE_NO_HOST_FALLBACK";
  private static final ThreadLocal<Lease> SLOT=new ThreadLocal<>();
  private static final class Lease {
    final P37RemoteProcess proxy;
    final long expiresNano;
    Lease(P37RemoteProcess process,long expires){proxy=process;expiresNano=expires;}
  }
  private P74OriginalEngineFixtureHandoff(){}
  public static void stageFromAuthenticatedChild(
      P37RemoteProcess proxy,int androidBinderUid,String hostSession,
      P37RemoteProcess.IsolatedUidVerifier trustedAndroidUidCheck) {
    if(proxy==null || !proxy.isAlive() || androidBinderUid<0 ||
       hostSession==null || !hostSession.matches("[a-f0-9]{64}") ||
       trustedAndroidUidCheck==null ||
       !trustedAndroidUidCheck.isIsolatedUid(androidBinderUid) ||
       SLOT.get()!=null)
      throw new SecurityException("P74_TRUSTED_CHILD_ACK_REQUIRED");
    SLOT.set(new Lease(proxy,System.nanoTime()+5_000_000_000L));
  }
  public static Process startOrDeny(ProcessBuilder originalBuilder)throws IOException {
    Lease lease=SLOT.get();
    SLOT.remove();
    if(lease==null)throw new IOException(DENY);
    if(System.nanoTime()-lease.expiresNano>0 || !lease.proxy.isAlive())
      throw new IOException("P74_EXPIRED_OR_TERMINATED_ISOLATED_CHILD");
    if(originalBuilder==null)
      throw new IOException("P74_NULL_BUILDER");
    List<String> cmd=originalBuilder.command();
    File dir=originalBuilder.directory();
    if(cmd==null||cmd.size()!=2 ||
       !"/system/bin/id".equals(cmd.get(0)) || !"-u".equals(cmd.get(1)) ||
       dir==null || !"/".equals(dir.getAbsolutePath()) ||
       originalBuilder.redirectErrorStream())
      throw new IOException("P74_FIXTURE_ONLY_REAL_ENGINE_ARGV_NOT_AUTHORIZED");
    return lease.proxy;
  }
  public static boolean pendingOnCurrentThread(){return SLOT.get()!=null;}
}
