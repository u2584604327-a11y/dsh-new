package com.dsh.android.p90;
public final class P90SendReceiptGateTest {
    static void require(boolean good, String label) { if (!good) throw new AssertionError(label); }
    static void reject(String label, boolean parsed, int len, boolean disabled, boolean matched) {
        P90SendReceiptGate gate = new P90SendReceiptGate("userturn01234", 5);
        gate.injectionReceipt(parsed, len, disabled, matched);
        gate.clickReceipt("SENT");
        gate.onTrustedUserTurn("userturn01234", true);
        require(gate.state() == P90SendReceiptGate.State.REJECTED && !gate.reportSent(), label);
    }
    public static void main(String[] args) {
        reject("observed log: len=0 sendDisabled=true", true, 0, true, false);
        reject("disabled even if nonempty", true, 5, true, true);
        reject("nonmatching content", true, 5, false, false);
        reject("malformed injection", false, 5, false, true);
        P90SendReceiptGate g = new P90SendReceiptGate("userturn01234", 5);
        g.injectionReceipt(true,5,false,true);
        g.clickReceipt("SENT");
        require(g.state() == P90SendReceiptGate.State.DISPATCHED_UNCONFIRMED && !g.reportSent(),
                "click is not a delivered turn");
        g.onTrustedUserTurn("otherturn01234", true);
        require(!g.reportSent(), "unrelated turn cannot confirm");
        g.onTrustedUserTurn("userturn01234", false);
        require(!g.reportSent(), "absent user message cannot confirm");
        g.onTrustedUserTurn("userturn01234", true);
        require(g.reportSent() && g.modelTurnObserved(), "trusted turn correlation");
        require(!g.canAutoRetry(), "no blind external send retry");
        P90SendReceiptGate disconnected = new P90SendReceiptGate("userturn01235",5);
        disconnected.injectionReceipt(true,5,false,true);
        disconnected.clickReceipt("SENT");
        disconnected.connectionLost();
        disconnected.onTrustedUserTurn("userturn01235",true);
        require(disconnected.state()==P90SendReceiptGate.State.OUTCOME_UNKNOWN &&
                !disconnected.reportSent() && !disconnected.canAutoRetry(), "unknown outcome cannot retry");
        P90SendReceiptGate rejected = new P90SendReceiptGate("userturn01236",5);
        rejected.injectionReceipt(true,5,false,true);
        rejected.clickReceipt("NOT_SENT");
        require(rejected.state()==P90SendReceiptGate.State.REJECTED, "explicit not sent");
        require("未登录".equals(P90EvidenceProjection.balance(false,0L,0L)),"no false zero");
        require("未提供".equals(P90EvidenceProjection.balance(true,null,0L)),"no missing zero");
        require(P90EvidenceProjection.balance(true,0L,0L).contains("合计 0"),"real zero preserved");
        require("未提供".equals(P90EvidenceProjection.tokens(null,null)),"no false token zero");
        require(P90EvidenceProjection.tokens(null,200L).contains("估算"),"estimate labeled");
        require("Binder 未连接".equals(P90EvidenceProjection.privilege(true,false,false,false)),"manager not equal binder");
        require("尚未授权".equals(P90EvidenceProjection.privilege(true,true,false,true)),"binder not equal authorization");
        require("已授权且通道就绪".equals(P90EvidenceProjection.privilege(true,true,true,true)),"actual channel");
        System.out.println("P90_FALSE_SENT_EMPTY_DISABLED_REJECTED=PASS");
        System.out.println("P90_CLICK_SENT_NEVER_EQUALS_MODEL_TURN=PASS");
        System.out.println("P90_DEDUP_UNKNOWN_NO_BLIND_RETRY=PASS");
        System.out.println("P90_UNAUTH_BALANCE_UNKNOWN_PRIVILEGE_EVIDENCE=PASS");
    }
}
