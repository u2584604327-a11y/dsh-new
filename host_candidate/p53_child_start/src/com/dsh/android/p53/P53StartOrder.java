package com.dsh.android.p53;

/**
 * P53 pure Java 8, exact one-shot process framing protocol.
 * Independent of Android. Platform Binder UID and session are separately
 * authenticated by P48HostProcessProbe before accepting these frames.
 *
 * HELLO(0) -> CHILD_STARTED(1) -> bounded streams(N) -> EXIT(N+1)
 * or HELLO(0) -> FAIL(1). HELLO is never a process-start assertion.
 * Explicitly disallows streaming or remote EXIT without real start ACK.
 */
public final class P53StartOrder {
  public static final int HELLO=482, STDOUT=483, STDERR=484,
      EXIT=485, FAIL=486, CHILD_STARTED=489;
  private boolean hello,child,terminal;
  private long expected=1;
  public synchronized boolean accept(int kind,long sequence) {
    if(terminal)return false;
    if(kind==HELLO) {
      if(hello || sequence!=0)return false;
      hello=true;
      return true;
    }
    if(!hello || sequence!=expected || expected==Long.MAX_VALUE)return false;
    if(kind==CHILD_STARTED) {
      if(child)return false;
      child=true; expected++;
      return true;
    }
    if(kind==FAIL) {
      terminal=true;expected++;
      return true;
    }
    if(!child)return false;
    if(kind==STDOUT || kind==STDERR) {
      expected++;
      return true;
    }
    if(kind==EXIT) {
      terminal=true;expected++;
      return true;
    }
    return false;
  }
  public synchronized boolean hasStartedChild() {return child;}
  public synchronized boolean isTerminal() {return terminal;}
}
