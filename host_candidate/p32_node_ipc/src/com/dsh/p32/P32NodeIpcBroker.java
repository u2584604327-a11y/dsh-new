package com.dsh.p32;

import com.dsh.p17.P17CapabilityGate;
import java.security.SecureRandom;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Trusted-host-only IPC grant broker. A real Android Activity/Service must pass
 * framework-authenticated Message.sendingUid after Process.isIsolatedUid().
 *
 * This class does not receive arbitrary raw user data or open files/URLs.
 * It does not certify Node runtime authenticity. SHA-pinned Node execution and
 * isolated->host Messenger binding are separate *mandatory* integration gates.
 */
public final class P32NodeIpcBroker {
  /** Implement using android.os.Process.isIsolatedUid in the TRUSTED host. */
  public interface IsolatedUidVerifier { boolean isIsolatedUid(int frameworkUid); }
  public enum Outcome {
    ALLOW_COUNT,
    DENY_NOT_BOUND,
    DENY_UNTRUSTED_SENDER,
    DENY_WRONG_SESSION,
    DENY_NO_GRANT,
    DENY_BAD_FRAME
  }
  public static final class Decision {
    public final Outcome outcome;
    public final int count;
    private Decision(Outcome o,int c) {outcome=o;count=c;}
    public boolean allowed() {return outcome==Outcome.ALLOW_COUNT;}
  }
  private static Decision deny(Outcome o) {return new Decision(o,0);}
  private static final Pattern NODE_FRAME =
      Pattern.compile("\\{\"op\":\"METADATA_COUNT\",\"limit\":([1-8])\\}");
  private static final int FRAME_MAX_BYTES=64;
  private static final long GRANT_TTL_MS=10_000L;
  private final P17CapabilityGate grants;
  private final IsolatedUidVerifier uidVerifier;
  private final SecureRandom random=new SecureRandom();
  private boolean bound=false;
  private int boundUid=-1;
  private String session=null;
  private String activeGrant=null;

  public P32NodeIpcBroker(
      P17CapabilityGate.MonotonicClock clock,IsolatedUidVerifier uidVerifier) {
    if(clock==null||uidVerifier==null)throw new IllegalArgumentException("trusted deps required");
    this.grants=new P17CapabilityGate(clock);
    this.uidVerifier=uidVerifier;
  }
  private String randomHex() {
    byte[] bytes=new byte[32];random.nextBytes(bytes);
    StringBuilder out=new StringBuilder(64);
    for(byte b:bytes) {
      out.append(Character.forDigit((b>>4)&15,16));
      out.append(Character.forDigit(b&15,16));
    }
    return out.toString();
  }

  /** Called ONLY when the trusted Android host receives a valid Binder HELLO.
   * The source UID must be android.framework Messenger.sendingUid.
   * Never pass a UID read from an untrusted Bundle or Node stdout. */
  public synchronized String bindAuthenticatedWorker(int frameworkUid) {
    disconnect();
    if(frameworkUid<0||!uidVerifier.isIsolatedUid(frameworkUid))
      return null;
    bound=true;
    boundUid=frameworkUid;
    session=randomHex();
    return session;
  }

  /** This call MUST occur only in a trusted Android native UI click listener.
   * Do not expose via Binder, JS bridge, model tool, receiver or CLI. */
  public synchronized String approveOneSyntheticCountOnTrustedUiClick() {
    if(!bound||session==null||boundUid<0||
        !uidVerifier.isIsolatedUid(boundUid))
      return null;
    if(activeGrant!=null){grants.revoke(activeGrant);activeGrant=null;}
    activeGrant=grants.approveOnce(
        P17CapabilityGate.SCOPE_METADATA_COUNT,boundUid,GRANT_TTL_MS);
    return activeGrant;
  }

  /**
   * Process a real isolated worker's request: frameworkUid is NOT taken from
   * user-supplied JSON. Session is host-minted upon the current Binder binding.
   * Node frame must be exact bounded canonical JSON from stdout of SHA-pinned
   * original Node executed in isolated UID. Only a positive synthetic count
   * is allowed; no filenames, domains, headers, URLs or raw result forwarding.
   */
  public synchronized Decision receiveAuthenticatedWorkerRequest(
      int frameworkUid,String sessionId,String token,String nodeStdout) {
    if(!bound||session==null)return deny(Outcome.DENY_NOT_BOUND);
    if(frameworkUid!=boundUid || !uidVerifier.isIsolatedUid(frameworkUid)) {
      disconnect(); // invalid caller burns all outstanding grants.
      return deny(Outcome.DENY_UNTRUSTED_SENDER);
    }
    if(sessionId==null||!session.equals(sessionId)) {
      disconnect(); // stale/mismatched session cannot retain a live grant.
      return deny(Outcome.DENY_WRONG_SESSION);
    }
    // Burn before inspecting the untrusted Node frame: malformed attempts
    // cannot retain a one-shot token for replay.
    if(activeGrant==null||token==null||!activeGrant.equals(token))
      return deny(Outcome.DENY_NO_GRANT);
    activeGrant=null;
    if(!grants.consume(token,P17CapabilityGate.SCOPE_METADATA_COUNT,frameworkUid))
      return deny(Outcome.DENY_NO_GRANT);
    if(nodeStdout==null||nodeStdout.length()>FRAME_MAX_BYTES)
      return deny(Outcome.DENY_BAD_FRAME);
    Matcher m=NODE_FRAME.matcher(nodeStdout);
    if(!m.matches())return deny(Outcome.DENY_BAD_FRAME);
    final int n;
    try{n=Integer.parseInt(m.group(1));}
    catch(NumberFormatException unexpected){return deny(Outcome.DENY_BAD_FRAME);}
    if(n<1||n>8)return deny(Outcome.DENY_BAD_FRAME);
    return new Decision(Outcome.ALLOW_COUNT,n);
  }
  public synchronized void onTrustedUiBackground() {disconnect();}
  public synchronized void onWorkerServiceDisconnected() {disconnect();}
  public synchronized void onBinderDeath() {disconnect();}
  public synchronized void disconnect() {
    grants.revokeAll();activeGrant=null;
    bound=false;boundUid=-1;session=null;
  }
  /** Test/audit visibility only; never expose in production app IPC. */
  synchronized int outstandingForTests() {return grants.outstanding();}
}
