package com.dsh.android.p90;

/** One-turn UI send state: click acknowledgment is never delivery confirmation. */
public final class P90SendReceiptGate {
    public enum State { NEW, INPUT_VERIFIED, DISPATCHED_UNCONFIRMED, CONFIRMED, REJECTED, OUTCOME_UNKNOWN }
    private final String turnId;
    private final int expectedUtf16Length;
    private State state = State.NEW;
    private String error = "NONE";
    private boolean observed;

    public P90SendReceiptGate(String turnId, int expectedUtf16Length) {
        if (turnId == null || !turnId.matches("[A-Za-z0-9_-]{8,128}"))
            throw new IllegalArgumentException("INVALID_TURN_ID");
        if (expectedUtf16Length < 1 || expectedUtf16Length > 100000)
            throw new IllegalArgumentException("INVALID_MESSAGE_LENGTH");
        this.turnId = turnId;
        this.expectedUtf16Length = expectedUtf16Length;
    }
    /** Called only after reading the original editor back in the trusted UI. */
    public synchronized void injectionReceipt(boolean parsed, int editorLength,
                                             boolean sendDisabled, boolean contentMatched) {
        if (state != State.NEW) throw new IllegalStateException("DUPLICATE_INJECTION");
        if (!parsed || editorLength != expectedUtf16Length || sendDisabled || !contentMatched) {
            state = State.REJECTED;
            error = !parsed ? "INVALID_INJECTION_RECEIPT" :
                    (sendDisabled ? "SEND_CONTROL_DISABLED" : "EDITOR_NOT_VERIFIED");
            return;
        }
        state = State.INPUT_VERIFIED;
    }
    /** A JS click result of SENT only means a click was attempted. */
    public synchronized void clickReceipt(String observedClick) {
        if (state == State.REJECTED || state == State.OUTCOME_UNKNOWN || state == State.CONFIRMED)
            return;
        if (state != State.INPUT_VERIFIED) throw new IllegalStateException("INPUT_NOT_VERIFIED");
        if ("SENT".equals(observedClick)) {
            state = State.DISPATCHED_UNCONFIRMED;
        } else if ("NOT_SENT".equals(observedClick)) {
            state = State.REJECTED;
            error = "NOT_SENT";
        } else {
            state = State.OUTCOME_UNKNOWN;
            error = "AMBIGUOUS_CLICK_OUTCOME";
        }
    }
    /** Must originate from a real chat turn observer and carry the same correlation id. */
    public synchronized void onTrustedUserTurn(String id, boolean userMessagePresent) {
        if (state == State.CONFIRMED) return;
        if (state != State.DISPATCHED_UNCONFIRMED) return;
        if (userMessagePresent && turnId.equals(id)) {
            observed = true;
            state = State.CONFIRMED;
        }
    }
    public synchronized void connectionLost() {
        if (state == State.INPUT_VERIFIED || state == State.DISPATCHED_UNCONFIRMED) {
            state = State.OUTCOME_UNKNOWN;
            error = "DISCONNECTED_BEFORE_CONFIRMATION";
        }
    }
    public synchronized State state() { return state; }
    public synchronized String reason() { return error; }
    public synchronized boolean modelTurnObserved() { return observed; }
    public synchronized boolean reportSent() { return state == State.CONFIRMED; }
    /** Never make blind retries of an external side effect. */
    public synchronized boolean canAutoRetry() { return false; }
    public synchronized String userStatus() {
        switch (state) {
            case NEW: return "等待输入";
            case INPUT_VERIFIED: return "输入框已核验，尚未确认发出";
            case DISPATCHED_UNCONFIRMED: return "已触发发送，等待页面确认";
            case CONFIRMED: return "已由页面确认消息";
            case REJECTED: return "发送未成功";
            default: return "结果不确定，禁止自动重发";
        }
    }
}
