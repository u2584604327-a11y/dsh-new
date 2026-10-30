package com.dsh.p17;
import java.security.SecureRandom;
import java.util.HashMap;
import java.util.Map;

/**
 * A trusted-process capability ledger. Never instantiate this in the isolated
 * worker. Uses a monotonic clock (Android SystemClock.elapsedRealtime), not
 * wall time; a grant is one-shot, UID-bound, scoped and short-lived.
 *
 * This class does not itself perform Binder caller authentication. The hosting
 * Binder/Messenger broker MUST check framework-authenticated calling UID,
 * never a UID asserted inside JSON/Bundle/JS, before calling consume().
 */
public final class P17CapabilityGate {
  public interface MonotonicClock { long nowMs(); }
  public static final String SCOPE_METADATA_COUNT="METADATA_COUNT";
  private static final long MAX_TTL_MS=30000L;
  private static final int MAX_OUTSTANDING=16;
  private final MonotonicClock clock;
  private final SecureRandom random=new SecureRandom();
  private final Map<String,Grant> grants=new HashMap<>();
  private static final class Grant {
    final String scope;final int isolatedUid;final long expiresMs;
    Grant(String s,int uid,long expiry){scope=s;isolatedUid=uid;expiresMs=expiry;}
  }
  public P17CapabilityGate(MonotonicClock clock) {
    if(clock==null)throw new IllegalArgumentException("monotonic clock required");
    this.clock=clock;
  }
  /** Trusted UI only: do not expose this method through Node/JS/plugins. */
  public synchronized String approveOnce(String scope,int isolatedUid,long ttlMs) {
    if(!SCOPE_METADATA_COUNT.equals(scope)||isolatedUid<0||
       ttlMs<=0||ttlMs>MAX_TTL_MS)
       throw new IllegalArgumentException("capability denied");
    expireOld();
    if(grants.size()>=MAX_OUTSTANDING)throw new IllegalStateException("too many grants");
    byte[] b=new byte[32];random.nextBytes(b);
    StringBuilder hex=new StringBuilder(64);
    for(byte part:b)hex.append(Character.forDigit((part>>>4)&15,16))
                       .append(Character.forDigit(part&15,16));
    String token=hex.toString();
    if(grants.containsKey(token))throw new IllegalStateException("nonce collision");
    long now=clock.nowMs();
    if(now<0||now>Long.MAX_VALUE-ttlMs)throw new IllegalStateException("clock invalid");
    grants.put(token,new Grant(scope,isolatedUid,now+ttlMs));
    return token;
  }
  /** Called only after trusted native IPC verifies Binder sender UID. */
  public synchronized boolean consume(String token,String scope,int authenticatedUid) {
    if(token==null||token.length()!=64)return false;
    Grant g=grants.remove(token); // burn even on wrong scope/UID (fail closed)
    if(g==null)return false;
    if(!SCOPE_METADATA_COUNT.equals(scope)||authenticatedUid<0)return false;
    return g.isolatedUid==authenticatedUid&&g.scope.equals(scope)&&
        clock.nowMs()>=0&&clock.nowMs()<g.expiresMs;
  }
  public synchronized void revoke(String token){if(token!=null)grants.remove(token);}
  public synchronized void revokeAll(){grants.clear();}
  public synchronized int outstanding(){expireOld();return grants.size();}
  private void expireOld() {
    long now=clock.nowMs();
    grants.entrySet().removeIf(e->now<0||now>=e.getValue().expiresMs);
  }
}
