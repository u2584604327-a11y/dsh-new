package com.dsh.android.p71;

/** Exactly one terminal outcome for one authenticated browser tool call. */
public final class P71ToolReplyOnce {
  public interface Sink { void onTerminal(Terminal value); }
  public static final class Terminal {
    public final String id,code;
    public final boolean ok,dispatched,outcomeUnknown,retrySafe;
    private Terminal(String id,boolean ok,String code,boolean dispatched,boolean unknown,boolean safe) {
      this.id=id;this.ok=ok;this.code=code;this.dispatched=dispatched;
      this.outcomeUnknown=unknown;this.retrySafe=safe;
    }
  }
  private final String id;
  private final Sink sink;
  private boolean complete,dispatched;
  public P71ToolReplyOnce(String trustedId,Sink terminalSink) {
    if(trustedId==null || !trustedId.matches("[A-Za-z0-9_-]{1,96}") || terminalSink==null)
      throw new IllegalArgumentException("P71_TRUSTED_CALL_ID_REQUIRED");
    id=trustedId;sink=terminalSink;
  }
  public synchronized boolean markDispatched() {
    if(complete||dispatched)return false;
    dispatched=true;return true;
  }
  public boolean executorConfirmedSuccess(){return finish(true,"OK",false,false);}
  public boolean executorConfirmedFailure(String category) {
    if(category==null||!category.matches("[A-Z][A-Z0-9_]{1,63}"))
      throw new IllegalArgumentException("P71_SAFE_ERROR_CATEGORY_REQUIRED");
    return finish(false,category,false,false);
  }
  public boolean deadlineElapsed(){
    return finish(false,wasDispatched()?"EXECUTOR_TIMEOUT_OUTCOME_UNKNOWN":"QUEUED_TIMEOUT",
                  wasDispatched(),!wasDispatched());
  }
  public boolean browserLost(){
    return finish(false,wasDispatched()?"BROWSER_DISCONNECTED_OUTCOME_UNKNOWN":"BROWSER_UNAVAILABLE",
                  wasDispatched(),!wasDispatched());
  }
  public synchronized boolean wasDispatched(){return dispatched;}
  public synchronized boolean isCompleted(){return complete;}
  private boolean finish(boolean ok,String code,boolean unknown,boolean retrySafe){
    Terminal result;
    synchronized(this) {
      if(complete)return false;
      complete=true;
      result=new Terminal(id,ok,code,dispatched,unknown,retrySafe);
    }
    sink.onTerminal(result);
    return true;
  }
  /** Only trusted native UI may approve these individual browser mutations. */
  public static boolean requiresNativeConfirmation(String action) {
    return "postComment".equals(action) || "replyComment".equals(action) ||
      "clickPublish".equals(action) || "sendMessage".equals(action) ||
      "submitForm".equals(action);
  }
}
