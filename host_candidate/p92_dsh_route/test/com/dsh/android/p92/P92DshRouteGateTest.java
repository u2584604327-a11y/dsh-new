package com.dsh.android.p92;
import com.dsh.android.p90.P90SendReceiptGate;
public final class P92DshRouteGateTest {
    static void ok(boolean good,String reason){if(!good)throw new AssertionError(reason);}
    static P90SendReceiptGate editor(boolean valid) {
        P90SendReceiptGate gate=new P90SendReceiptGate("turn_p92_12345",4);
        gate.injectionReceipt(true,valid?4:0,!valid,valid);
        return gate;
    }
    static P92DshRouteGate.Health health(boolean verified,String nativeOwner,String route) {
        return new P92DshRouteGate.Health(true,true,verified,false,
            "127.0.0.1:8787",nativeOwner,route);
    }
    static void originalProviderNotWebBubble() {
        final String id="turn_dsh_provider_123";
        final boolean[] current={true};
        P92DshRouteGate.OriginalSessionTurn original=turn ->
            current[0] && id.equals(turn);
        P92DshRouteGate api=P92DshRouteGate.forOriginalProviderTurn(id, original);
        ok(api.preflight(health(true,"main","main_socket_and_driver_match")),
           "original DSH provider accepted without invented web bubble");
        ok(api.consumeOneAttempt(),"exactly one original provider POST attempt");
        ok(!api.consumeOneAttempt(),"second original provider POST is prohibited");
        api.onHttpStatus(200);
        ok(!api.isConfirmed(),"HTTP 200 alone cannot certify user turn");
        api.onTrustedUserTurn("wrong_original_turn",true);
        ok(!api.isConfirmed(),"foreign session turn must not confirm");
        api.onTrustedUserTurn(id,true);
        ok(!api.isConfirmed() && api.originalRequestAcceptedButReplyUnverified(),
           "original turn + HTTP is transport acceptance, NOT model reply");
        ok("ORIGINAL_TURN_AND_HTTP_ACCEPTED_MODEL_REPLY_UNPROVEN".equals(api.reason()),
           "must not claim model reply");

        P92DshRouteGate reverse=P92DshRouteGate.forOriginalProviderTurn(id,original);
        ok(reverse.preflight(health(true,"overlay","overlay_socket_and_driver_match")),
           "overlay original provider owner validated");
        ok(reverse.consumeOneAttempt(),"overlay original provider one attempt");
        reverse.onTrustedUserTurn(id,true);
        ok(!reverse.isConfirmed(),"trusted user turn alone insufficient");
        reverse.onHttpStatus(200);
        ok(!reverse.isConfirmed() && reverse.originalRequestAcceptedButReplyUnverified(),
           "reverse event order does not claim assistant message complete");

        // Even after a 200 and a real user turn, premature SSE loss must
        // not be reported as a delivered model answer or cause a retry.
        api.onConnectionLost();
        ok(api.stage()==P92DshRouteGate.Stage.UNKNOWN_AFTER_DISPATCH &&
           !api.isConfirmed() && !api.originalRequestAcceptedButReplyUnverified() &&
           !api.canAutoRetry(),"post-200 model stream disconnect is not success");

        P92DshRouteGate notTrusted=P92DshRouteGate.forOriginalProviderTurn(id,t -> false);
        ok(!notTrusted.preflight(health(true,"main","main_socket_and_driver_match")),
           "no confirmed original session means no attempt");
        ok(!notTrusted.consumeOneAttempt(),"no bypass by owner verified alone");
        P92DshRouteGate revoked=P92DshRouteGate.forOriginalProviderTurn(id,original);
        ok(revoked.preflight(health(true,"main","main_socket_and_driver_match")),
           "original session valid at health");
        current[0]=false;
        ok(!revoked.consumeOneAttempt(),"original session revoked between GET and POST");
        ok("ORIGINAL_SESSION_TURN_CHANGED".equals(revoked.reason()),
           "stale session must be visible as rejected");
        current[0]=true;

        P92DshRouteGate refused=P92DshRouteGate.forOriginalProviderTurn(id,original);
        ok(refused.preflight(health(true,"main","main_socket_and_driver_match")),
           "owner preflight for 409");
        ok(refused.consumeOneAttempt(),"409 one attempt");
        refused.onTrustedUserTurn(id,true);
        refused.onHttpStatus(409);
        ok(refused.stage()==P92DshRouteGate.Stage.HTTP_REJECTED &&
           !refused.isConfirmed() && !refused.canAutoRetry(),
           "409 cannot be bypassed by local original user turn");

        P92DshRouteGate lost=P92DshRouteGate.forOriginalProviderTurn(id,original);
        ok(lost.preflight(health(true,"main","main_socket_and_driver_match")),
           "original session ready for ambiguous network failure");
        ok(lost.consumeOneAttempt(),"one attempted send");
        lost.onConnectionLost();
        ok(lost.stage()==P92DshRouteGate.Stage.UNKNOWN_AFTER_DISPATCH &&
           !lost.canAutoRetry(),"original provider network failure cannot blind retry");

        P92DshRouteGate noOwner=P92DshRouteGate.forOriginalProviderTurn(id,original);
        ok(!noOwner.preflight(health(false,"unknown","port_not_owned_by_main")),
           "original provider cannot bypass native runtime owner");
        boolean rejected=false;
        try {P92DshRouteGate.forOriginalProviderTurn(" ", original);}
        catch(IllegalArgumentException correct){rejected=true;}
        ok(rejected,"invalid original turn identifier rejected");
        System.out.println("P92_ORIGINAL_PROVIDER_NO_WEB_BUBBLE_DEPENDENCY=PASS");
        System.out.println("P92_ORIGINAL_SESSION_RECHECK_AND_409_NO_RETRY=PASS");
        System.out.println("P92_HTTP200_AND_TURN_NOT_MODEL_REPLY=PASS");
        System.out.println("P92_ORIGINAL_HTTP200_NEVER_FAKE_ASSISTANT_COMPLETION=PASS");
    }

    public static void main(String[] ignored) {
        originalProviderNotWebBubble();
        P92DshRouteGate invalid=new P92DshRouteGate(editor(false));
        ok(!invalid.preflight(health(true,"main","main_socket_and_driver_match")),"len0 must block");
        ok(!invalid.consumeOneAttempt(),"must not POST empty text");
        P92DshRouteGate unknown=new P92DshRouteGate(editor(true));
        ok(!unknown.preflight(health(false,"unknown","port_not_owned_by_main")),"mismatch must block");
        ok(!unknown.consumeOneAttempt(),"no unknown owner POST");
        P92DshRouteGate overlay=new P92DshRouteGate(editor(true));
        ok(overlay.preflight(health(true,"overlay","overlay_socket_and_driver_match")),"valid overlay");
        ok(overlay.consumeOneAttempt(),"single attempt");
        ok(!overlay.consumeOneAttempt(),"no second attempt");
        overlay.onHttpStatus(200);
        ok(!overlay.isConfirmed(),"HTTP200 is not model-turn confirmation");
        overlay.onTrustedUserTurn("wrongturn",true);
        ok(!overlay.isConfirmed(),"wrong turn does not confirm");
        overlay.onTrustedUserTurn("turn_p92_12345",true);
        ok(overlay.isConfirmed(),"verified correlated turn");
        P92DshRouteGate changed=new P92DshRouteGate(editor(true));
        ok(changed.preflight(health(true,"main","main_socket_and_driver_match")),"main ready");
        ok(changed.consumeOneAttempt(),"dispatch ready");
        changed.onHttpStatus(409);
        ok(changed.stage()==P92DshRouteGate.Stage.HTTP_REJECTED
           && "ORIGINAL_RUNTIME_OWNER_MISMATCH".equals(changed.reason()),"server 409 must be final");
        ok(!changed.canAutoRetry(),"409 no retry");
        P92DshRouteGate disconnected=new P92DshRouteGate(editor(true));
        ok(disconnected.preflight(health(true,"main","main_socket_and_driver_match")),"main preflight");
        ok(disconnected.consumeOneAttempt(),"one attempt");
        disconnected.onConnectionLost();
        ok(disconnected.stage()==P92DshRouteGate.Stage.UNKNOWN_AFTER_DISPATCH &&
           !disconnected.canAutoRetry(),"connection lost no blind retry");
        P92DshRouteGate ambiguous=new P92DshRouteGate(editor(true));
        ok(!ambiguous.preflight(new P92DshRouteGate.Health(true,true,true,true,
           "127.0.0.1:8787","main","main_socket_and_driver_match")),"ambiguous owner");
        P92DshRouteGate wrongListen=new P92DshRouteGate(editor(true));
        ok(!wrongListen.preflight(new P92DshRouteGate.Health(true,true,true,false,
           "127.0.0.1:1604","main","main_socket_and_driver_match")),"no direct 1604");
        System.out.println("P92_DSH_EDITOR_FAIL_CLOSED_BEFORE_OMNIGATE=PASS");
        System.out.println("P92_8787_VERIFIED_OWNER_PREFLIGHT_AND_409_FAIL_CLOSED=PASS");
        System.out.println("P92_ONE_SHOT_NO_AUTO_RETRY_AND_HTTP200_NOT_DELIVERY=PASS");
        System.out.println("P92_MAIN_AND_OVERLAY_OWNER_EXCLUSIVE=PASS");
    }
}
