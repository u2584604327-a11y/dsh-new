package com.dsh.p37;

import java.io.IOException;
import java.io.InputStream;
import java.io.InterruptedIOException;
import java.io.OutputStream;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * Source-only, host-side Java Process facade for a remote isolated Android Node.
 * This is NOT a process launcher, Android Binder implementation, or an original
 * EngineManager patch. A trusted native adapter must validate the framework
 * Binder sender UID and supply a host-generated session before constructing it.
 * No arbitrary stdin, command, filesystem, or tool capabilities are exposed.
 */
public final class P37RemoteProcess extends Process {
  public interface IsolatedUidVerifier {
    boolean isIsolatedUid(int frameworkUid);
  }
  public interface RemoteControl {
    void requestGracefulStop();
    void requestForceStop();
  }
  public enum TerminalReason {
    RUNNING, REMOTE_EXIT, TRANSPORT_LOST, IDENTITY_MISMATCH,
    BUFFER_OVERFLOW, STOP_TIMEOUT, REMOTE_CONTROL_FAILURE
  }
  public static final int BUFFER_BYTES = 65536;
  public static final int MAX_FRAME_BYTES = 4096;
  public static final int SUPERVISOR_FAILURE_EXIT_CODE = 125;
  private final int boundUid;
  private final String session;
  private final IsolatedUidVerifier uidVerifier;
  private final RemoteControl control;
  private final BoundedStream stdout = new BoundedStream(BUFFER_BYTES);
  private final BoundedStream stderr = new BoundedStream(BUFFER_BYTES);
  private final CountDownLatch exited = new CountDownLatch(1);
  private final Object lock = new Object();
  private volatile TerminalReason reason = TerminalReason.RUNNING;
  private int exitCode = SUPERVISOR_FAILURE_EXIT_CODE;
  private boolean stopSent = false;
  private boolean killSent = false;

  public P37RemoteProcess(int authenticatedWorkerUid, String hostSession,
      IsolatedUidVerifier verifier, RemoteControl remoteControl) {
    if (verifier == null || remoteControl == null || hostSession == null ||
        !hostSession.matches("[a-f0-9]{64}") || authenticatedWorkerUid < 0 ||
        !verifier.isIsolatedUid(authenticatedWorkerUid)) {
      throw new IllegalArgumentException("trusted isolated session required");
    }
    boundUid = authenticatedWorkerUid;
    session = hostSession;
    uidVerifier = verifier;
    control = remoteControl;
  }

  /** Caller MUST pass platform Message.sendingUid, never a Bundle UID. */
  private boolean authenticate(int frameworkUid, String incomingSession) {
    if (frameworkUid == boundUid && session.equals(incomingSession) &&
        uidVerifier.isIsolatedUid(frameworkUid)) return true;
    failClosed(TerminalReason.IDENTITY_MISMATCH);
    return false;
  }

  /** Nonblocking Binder callback; stream backpressure can NEVER block Binder. */
  public boolean onAuthenticatedStdout(int frameworkUid, String incomingSession,
      byte[] data) {
    return accept(frameworkUid, incomingSession, data, stdout);
  }
  public boolean onAuthenticatedStderr(int frameworkUid, String incomingSession,
      byte[] data) {
    return accept(frameworkUid, incomingSession, data, stderr);
  }
  private boolean accept(int uid, String incomingSession, byte[] data,
      BoundedStream stream) {
    if (!authenticate(uid, incomingSession)) return false;
    if (reason != TerminalReason.RUNNING) return false;
    if (data == null || data.length < 1 || data.length > MAX_FRAME_BYTES ||
        !stream.offer(data)) {
      failClosed(TerminalReason.BUFFER_OVERFLOW);
      return false;
    }
    return true;
  }

  public boolean onAuthenticatedExit(int frameworkUid, String incomingSession,
      int actualChildExitCode) {
    if (!authenticate(frameworkUid, incomingSession)) return false;
    synchronized (lock) {
      if (reason != TerminalReason.RUNNING) return false;
      exitCode = actualChildExitCode;
      reason = TerminalReason.REMOTE_EXIT;
      stdout.finish(false);
      stderr.finish(false);
      exited.countDown();
      return true;
    }
  }
  /** Both binder death and worker unbind must invalidate this proxy. */
  public void onTransportLost() { failClosed(TerminalReason.TRANSPORT_LOST); }
  /** Trusted supervisor must schedule this if stop/kill ACK is absent. */
  public void onStopDeadlineExpired() { failClosed(TerminalReason.STOP_TIMEOUT); }
  public TerminalReason terminalReason() { return reason; }

  private void failClosed(TerminalReason cause) {
    boolean callKill = false;
    synchronized (lock) {
      if (reason != TerminalReason.RUNNING) return;
      reason = cause;
      exitCode = SUPERVISOR_FAILURE_EXIT_CODE;
      stdout.finish(true); // Discard untrusted pending lines; never imply READY.
      stderr.finish(true);
      exited.countDown();
      if (!killSent) { killSent = true; callKill = true; }
    }
    if (callKill) {
      try { control.requestForceStop(); } catch (RuntimeException ignored) {
        // Failure is already terminal; physical worker kill is NOT proven.
      }
    }
  }
  @Override public InputStream getInputStream() { return stdout; }
  @Override public InputStream getErrorStream() { return stderr; }
  /** Fail closed: real original EngineManager stdin use is NOT yet audited. */
  @Override public OutputStream getOutputStream() {
    return new OutputStream() {
      @Override public void write(int b) throws IOException {
        throw new IOException("P37_UNAUDITED_STDIN_DENIED");
      }
      @Override public void write(byte[] b, int o, int len) throws IOException {
        if (b == null) throw new NullPointerException();
        if (o < 0 || len < 0 || o > b.length - len)
          throw new IndexOutOfBoundsException();
        if (len != 0) throw new IOException("P37_UNAUDITED_STDIN_DENIED");
      }
    };
  }
  @Override public int waitFor() throws InterruptedException {
    exited.await();
    synchronized (lock) { return exitCode; }
  }
  @Override public boolean waitFor(long timeout, TimeUnit unit)
      throws InterruptedException {
    if (unit == null) throw new NullPointerException("unit");
    return exited.await(timeout, unit);
  }
  @Override public int exitValue() {
    synchronized (lock) {
      if (reason == TerminalReason.RUNNING) throw new IllegalThreadStateException();
      return exitCode;
    }
  }
  @Override public boolean isAlive() { return reason == TerminalReason.RUNNING; }
  @Override public void destroy() {
    synchronized (lock) {
      if (reason != TerminalReason.RUNNING || stopSent || killSent) return;
      stopSent = true;
    }
    try { control.requestGracefulStop(); }
    catch (RuntimeException bad) { failClosed(TerminalReason.REMOTE_CONTROL_FAILURE); }
  }
  @Override public Process destroyForcibly() {
    synchronized (lock) {
      if (reason != TerminalReason.RUNNING || killSent) return this;
      killSent = true;
    }
    try { control.requestForceStop(); }
    catch (RuntimeException bad) { failClosed(TerminalReason.REMOTE_CONTROL_FAILURE); }
    return this;
  }

  private static final class BoundedStream extends InputStream {
    private final byte[] buffer;
    private int first = 0, used = 0;
    private boolean done = false;
    BoundedStream(int cap) { buffer = new byte[cap]; }
    synchronized boolean offer(byte[] source) {
      if (done || source.length > buffer.length - used) return false;
      for (byte b : source) {
        buffer[(first + used) % buffer.length] = b;
        used++;
      }
      notifyAll();
      return true;
    }
    synchronized void finish(boolean discard) {
      if (discard) { used = 0; first = 0; }
      done = true;
      notifyAll();
    }
    @Override public synchronized int available() { return used; }
    @Override public int read() throws IOException {
      byte[] one = new byte[1];
      int n = read(one, 0, 1);
      return n < 0 ? -1 : one[0] & 255;
    }
    @Override public synchronized int read(byte[] out, int off, int len)
        throws IOException {
      if (out == null) throw new NullPointerException();
      if (off < 0 || len < 0 || off > out.length - len)
        throw new IndexOutOfBoundsException();
      if (len == 0) return 0;
      while (used == 0 && !done) {
        try { wait(); }
        catch (InterruptedException interrupted) {
          Thread.currentThread().interrupt();
          InterruptedIOException x = new InterruptedIOException("stream interrupted");
          x.initCause(interrupted);
          throw x;
        }
      }
      if (used == 0) return -1;
      int amount = Math.min(used, len);
      for (int i = 0; i < amount; i++) out[off+i] = buffer[(first+i)%buffer.length];
      first = (first+amount)%buffer.length;
      used -= amount;
      return amount;
    }
    @Override public void close() { finish(true); }
  }
}
