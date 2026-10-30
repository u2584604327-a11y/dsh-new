package com.dsh.android.p92;

import com.dsh.android.p90.P90SendReceiptGate;

/** Contract for a single DSH-owned send to an already-installed OmniGate listener.
 * The actual OmniGate server MUST recheck owner on POST; /health is advisory.
 */
public final class P92DshRouteGate {
    public static final String ROUTE = "http://127.0.0.1:8787/v1/chat/completions";
    public static final String HEALTH = "http://127.0.0.1:8787/health";

    public enum Stage {
        NEW, PREFLIGHT_OK, DISPATCH_UNCONFIRMED, ORIGINAL_TRANSPORT_ACCEPTED_REPLY_UNVERIFIED, CONFIRMED,
        PRECHECK_REJECTED, HTTP_REJECTED, UNKNOWN_AFTER_DISPATCH
    }
    public static final class Health {
        public final boolean ok, reachable, verified, ambiguous;
        public final String listen, nativeOwner, runtimeRoute;
        public Health(boolean serviceOk,boolean upstreamReachable,boolean ownerVerified,
                      boolean ambiguousOwners,String listenAddress,String verifiedNativeOwner,
                      String observedRuntimeRoute) {
            ok=serviceOk;reachable=upstreamReachable;verified=ownerVerified;ambiguous=ambiguousOwners;
            listen=listenAddress;nativeOwner=verifiedNativeOwner;runtimeRoute=observedRuntimeRoute;
        }
    }
    /**
     * Only the ORIGINAL DSH session controller may implement this callback.
     * This candidate cannot authenticate a Java caller by itself; binding to
     * a genuine session callback is mandatory before production integration.
     */
    public interface OriginalSessionTurn {
        boolean isAcceptedCurrentUserTurn(String turnId);
    }
    private enum Origin { WEB_BUBBLE, ORIGINAL_PROVIDER }
    private final Origin origin;
    private final P90SendReceiptGate editorReceipt;
    private final OriginalSessionTurn sessionTurn;
    private final String providerTurnId;
    private boolean providerTurnObserved, httpAccepted;
    private Stage state=Stage.NEW;
    private String reason="NOT_CHECKED";
    private boolean clickReceiptApplied;

    public P92DshRouteGate(P90SendReceiptGate receipt) {
        if (receipt==null)throw new IllegalArgumentException("MISSING_EDITOR_RECEIPT");
        editorReceipt=receipt;
        origin=Origin.WEB_BUBBLE;
        sessionTurn=null;
        providerTurnId=null;
    }

    private P92DshRouteGate(String turnId, OriginalSessionTurn trustedSession) {
        if(turnId==null || !turnId.matches("[A-Za-z0-9_-]{8,128}") || trustedSession==null)
            throw new IllegalArgumentException("INVALID_ORIGINAL_SESSION_TURN");
        origin=Origin.ORIGINAL_PROVIDER;
        sessionTurn=trustedSession;
        providerTurnId=turnId;
        editorReceipt=null;
    }

    /** DSH's existing model adapter does not use an OmniGate WEB editor.
     * This is deliberately not a bypass for a missing original session turn.
     * An unverified caller must not fabricate approval via a literal flag.
     */
    public static P92DshRouteGate forOriginalProviderTurn(
            String turnId, OriginalSessionTurn trustedSession) {
        return new P92DshRouteGate(turnId,trustedSession);
    }

    private boolean originalTurnAccepted() {
        try {
            return sessionTurn!=null && sessionTurn.isAcceptedCurrentUserTurn(providerTurnId);
        } catch(RuntimeException invalidOriginalSession) {
            return false;
        }
    }

    /**
     * Consumes read-only /health evidence; does not send, retry, login, change port or ownership.
     * Health status can race a new POST and NEVER grants permission to bypass server-side 409.
     */
    public synchronized boolean preflight(Health h) {
        if(state!=Stage.NEW)throw new IllegalStateException("P92_ALREADY_CHECKED");
        if(origin==Origin.WEB_BUBBLE) {
            if(editorReceipt.state()!=P90SendReceiptGate.State.INPUT_VERIFIED) {
                state=Stage.PRECHECK_REJECTED;reason="DSH_EDITOR_NOT_VERIFIED";return false;
            }
        } else if(!originalTurnAccepted()) {
            state=Stage.PRECHECK_REJECTED;
            reason="ORIGINAL_DSH_SESSION_TURN_NOT_VERIFIED";return false;
        }
        if(h==null || !h.ok || !"127.0.0.1:8787".equals(h.listen)) {
            state=Stage.PRECHECK_REJECTED;reason="OMNIGATE_LISTENER_NOT_VERIFIED";return false;
        }
        if(!h.reachable){state=Stage.PRECHECK_REJECTED;reason="NATIVE_LISTENER_UNAVAILABLE";return false;}
        if(!h.verified || h.ambiguous){
            state=Stage.PRECHECK_REJECTED;reason="NATIVE_RUNTIME_OWNER_UNVERIFIED";return false;
        }
        if(!(("main".equals(h.nativeOwner) && "main_socket_and_driver_match".equals(h.runtimeRoute)) ||
             ("overlay".equals(h.nativeOwner) && "overlay_socket_and_driver_match".equals(h.runtimeRoute)))) {
            state=Stage.PRECHECK_REJECTED;reason="OWNER_IDENTITY_ROUTE_CONFLICT";return false;
        }
        state=Stage.PREFLIGHT_OK;reason="ADVISORY_READY_FOR_ONE_ATTEMPT";return true;
    }
    /** Called before the one real DSH transport POST; no automatic resend on failure. */
    public synchronized boolean consumeOneAttempt() {
        if(state!=Stage.PREFLIGHT_OK)return false;
        // Original chat sessions can change between GET /health and POST.
        // Recheck live original turn identity immediately before one attempt.
        if(origin==Origin.ORIGINAL_PROVIDER && !originalTurnAccepted()) {
            state=Stage.PRECHECK_REJECTED;reason="ORIGINAL_SESSION_TURN_CHANGED";return false;
        }
        state=Stage.DISPATCH_UNCONFIRMED;reason="TRANSPORT_RESULT_NOT_CONFIRMED";return true;
    }
    /** HTTP status is transport-only. A 200 is not confirmation of user turn delivery. */
    public synchronized void onHttpStatus(int status) {
        if(state!=Stage.DISPATCH_UNCONFIRMED)return;
        if(status==409){state=Stage.HTTP_REJECTED;reason="ORIGINAL_RUNTIME_OWNER_MISMATCH";}
        else if(status==503){state=Stage.HTTP_REJECTED;reason="NATIVE_API_UNAVAILABLE";}
        else if(status==401 || status==403){state=Stage.HTTP_REJECTED;reason="AUTH_REJECTED";}
        else if(status==200){
            httpAccepted=true;
            reason="HTTP_200_WAITING_FOR_REAL_TURN";
            confirmOriginalProviderIfBothObserved();
        }
        else if(status>0){state=Stage.HTTP_REJECTED;reason="HTTP_OTHER_REJECTED";}
    }
    /** A verified original user turn plus HTTP 200 is still NOT a model reply. */
    private void confirmOriginalProviderIfBothObserved() {
        if(origin==Origin.ORIGINAL_PROVIDER && state==Stage.DISPATCH_UNCONFIRMED &&
           httpAccepted && providerTurnObserved && originalTurnAccepted()){
            state=Stage.ORIGINAL_TRANSPORT_ACCEPTED_REPLY_UNVERIFIED;
            reason="ORIGINAL_TURN_AND_HTTP_ACCEPTED_MODEL_REPLY_UNPROVEN";
        }
    }
    /** Does not infer a turn from SSE [DONE], model content, or transport HTTP200. */
    public synchronized void onTrustedUserTurn(String turnId,boolean actuallyPresent) {
        if(state!=Stage.DISPATCH_UNCONFIRMED)return;
        if(origin==Origin.ORIGINAL_PROVIDER) {
            if(actuallyPresent && providerTurnId.equals(turnId) && originalTurnAccepted()) {
                providerTurnObserved=true;
                confirmOriginalProviderIfBothObserved();
            }
            return;
        }
        if(!clickReceiptApplied) {
            editorReceipt.clickReceipt("SENT");
            clickReceiptApplied=true;
        }
        editorReceipt.onTrustedUserTurn(turnId,actuallyPresent);
        if(editorReceipt.reportSent()){
            state=Stage.CONFIRMED;reason="TRUSTED_USER_TURN_OBSERVED";
        }
    }
    public synchronized void onConnectionLost() {
        if(state==Stage.DISPATCH_UNCONFIRMED ||
           state==Stage.ORIGINAL_TRANSPORT_ACCEPTED_REPLY_UNVERIFIED){
            if(editorReceipt!=null) editorReceipt.connectionLost();
            state=Stage.UNKNOWN_AFTER_DISPATCH;
            reason="NO_RETRY_AMBIGUOUS_DISCONNECT";
        }
    }
    public synchronized Stage stage(){return state;}
    public synchronized String reason(){return reason;}
    public synchronized boolean canAutoRetry(){return false;}
    /** Distinguish verified original request acceptance from an actual model reply.
     * A provider request can never be CONFIRMED until a trusted original
     * assistant message projection has been wired (not present in this candidate).
     */
    public synchronized boolean originalRequestAcceptedButReplyUnverified(){
        return origin==Origin.ORIGINAL_PROVIDER &&
            state==Stage.ORIGINAL_TRANSPORT_ACCEPTED_REPLY_UNVERIFIED;
    }
    public synchronized boolean isConfirmed(){return state==Stage.CONFIRMED;}
}
