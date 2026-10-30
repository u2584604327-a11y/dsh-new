package com.dsh.android.p67;

import com.dsh.android.p53.P53StartOrder;
import com.dsh.p37.P37RemoteProcess;

/**
 * Source-only authenticated host handoff joining the EXISTING P53 frame order
 * and P37 Process facade. This class does not start a process or bind Android
 * Binder; that implementation is an independent future production gate.
 *
 * UID MUST be Android framework Message.sendingUid, never a Bundle claim.
 * CHILD_STARTED only means a remote child started; it NEVER means Node is READY.
 * Original EngineManager's actual READY predicate has not been implemented.
 */
public final class P67AuthenticatedHandoff {
  private final int expectedUid;
  private final String hostSession;
  private final P37RemoteProcess.IsolatedUidVerifier verifier;
  private final P37RemoteProcess.RemoteControl remoteControl;
  private final P53StartOrder ordering = new P53StartOrder();
  private P37RemoteProcess process;
  private boolean terminal;
  private boolean startConfirmed;

  public P67AuthenticatedHandoff(
      int frameworkIsolatedUid, String hostGeneratedSession,
      P37RemoteProcess.IsolatedUidVerifier frameworkVerifier,
      P37RemoteProcess.RemoteControl trustedStopControl) {
    if (frameworkIsolatedUid < 0 || frameworkVerifier == null ||
        trustedStopControl == null || hostGeneratedSession == null ||
        !hostGeneratedSession.matches("[a-f0-9]{64}") ||
        !frameworkVerifier.isIsolatedUid(frameworkIsolatedUid)) {
      throw new IllegalArgumentException("P67_TRUSTED_ISOLATED_SESSION_REQUIRED");
    }
    expectedUid = frameworkIsolatedUid;
    hostSession = hostGeneratedSession;
    verifier = frameworkVerifier;
    remoteControl = trustedStopControl;
  }

  private boolean verify(int frameworkUid, String incomingSession) {
    try {
      return expectedUid == frameworkUid &&
          hostSession.equals(incomingSession) &&
          verifier.isIsolatedUid(frameworkUid);
    } catch (RuntimeException rejected) {
      return false;
    }
  }

  private void failClosed() {
    if (terminal) return;
    terminal = true;
    if (process != null) process.onTransportLost();
  }

  private static boolean validPayload(int kind, byte[] frameBytes) {
    if (kind == P53StartOrder.STDOUT || kind == P53StartOrder.STDERR)
      return frameBytes != null && frameBytes.length >= 1 &&
          frameBytes.length <= P37RemoteProcess.MAX_FRAME_BYTES;
    if (kind == P53StartOrder.HELLO ||
        kind == P53StartOrder.CHILD_STARTED ||
        kind == P53StartOrder.EXIT ||
        kind == P53StartOrder.FAIL)
      return frameBytes == null || frameBytes.length == 0;
    return false;
  }

  /**
   * Caller must supply the actual Android Binder sending UID as frameworkUid.
   * The host session is created by the host and never accepted from an
   * unverified source. Protocol failure irreversibly terminates this handoff.
   * No output bytes are logged, inspected for READY, or persisted.
   */
  public synchronized boolean onAuthenticatedFrame(
      int frameworkUid, String incomingSession, int kind,
      long sequence, byte[] frameBytes, int exitCode) {
    if (terminal) return false;
    if (!verify(frameworkUid, incomingSession) ||
        !validPayload(kind, frameBytes) ||
        !ordering.accept(kind, sequence)) {
      failClosed();
      return false;
    }

    if (kind == P53StartOrder.HELLO) {
      // Greeting is NOT a process handoff or a process started ACK.
      return true;
    }
    if (kind == P53StartOrder.CHILD_STARTED) {
      if (process != null || startConfirmed) {
        failClosed();
        return false;
      }
      try {
        process = new P37RemoteProcess(
            expectedUid, hostSession, verifier, remoteControl);
        startConfirmed = true;
        return true;
      } catch (RuntimeException invalid) {
        failClosed();
        return false;
      }
    }
    if (kind == P53StartOrder.FAIL) {
      failClosed();
      return true; // Terminal failure frame accepted, not a successful start.
    }
    if (process == null || !startConfirmed) {
      failClosed();
      return false;
    }
    if (kind == P53StartOrder.STDOUT || kind == P53StartOrder.STDERR) {
      boolean ok = kind == P53StartOrder.STDOUT ?
          process.onAuthenticatedStdout(frameworkUid, incomingSession, frameBytes) :
          process.onAuthenticatedStderr(frameworkUid, incomingSession, frameBytes);
      if (!ok) failClosed();
      return ok;
    }
    if (kind == P53StartOrder.EXIT) {
      boolean ok = process.onAuthenticatedExit(
          frameworkUid, incomingSession, exitCode);
      terminal = true;
      if (!ok) process.onTransportLost();
      return ok;
    }
    failClosed();
    return false;
  }

  /** An Android Binder death or disconnect must invalidate all future frames. */
  public synchronized void onTransportLost() { failClosed(); }

  /**
   * Returns an actual Java Process facade only after authenticated
   * CHILD_STARTED. It is NOT proof of engine READY, even if stdout follows.
   */
  public synchronized Process processAfterVerifiedChildStart() {
    return startConfirmed ? process : null;
  }
  public synchronized boolean hasVerifiedChildStart() {
    return startConfirmed;
  }
  public synchronized boolean isTerminal() { return terminal; }

  /**
   * No READY observer exists until verified original EngineManager reader
   * predicate and server startup semantics are connected and tested.
   */
  public boolean hasVerifiedOriginalEngineReady() { return false; }
}
