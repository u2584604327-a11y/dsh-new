# P52 — Live Process handoff from isolated Android Binder in original DSH-derived host

## Verified prerequisite
P51 physical Android ARM64 user-supplied status confirms exact original SHA-pinned Node ELF under isolated UID and authenticated Binder/P37 Java Process, stdout/stderr/BOOT/READY and exit **for a fixed synthetic script**, not production EngineManager or original DSH Application.

## P52 actual code delta
- Extend P48HostProcessProbe with optional `LiveProcessReceiver`. The existing original-host process proxy (a P37RemoteProcess subclass of java.lang.Process) can now be handed off immediately after an authenticated first isolated-UID Binder HELLO and before the synthetic child naturally exits. Existing two/three-argument constructors are backward compatible. The receiver is local trusted Java code, not remote/mutable registry and cannot supply argv, cwd, env, file grants or network access.
- Trust gates before callback: Android framework Message.sendingUid must be isolated and different from host; 256-bit session must match; HELLO must have seq0 and occur exactly once; P37 Process constructed with a binder-bound Stop/Kill control. Callback exceptions cause fail-closed transport loss; no fallback ProcessBuilder.start.
- The disposable original-host P43ProbeActivity installs receiver and checks instance of P37RemoteProcess, true isolated UID, live Process and streams, emitting `P52_LIVE_P37_JAVA_PROCESS_FROM_ISOLATED_BINDER=PASS`.
- **Important:** HELLO currently precedes the actual Node ProcessBuilder.start() in P50. This callback proves live facade availability, NOT proven child execve, Node ready, or production EngineManager startup. The original EngineManager coroutine still invokes P47's fail-closed bridge. P35 found that original coroutine stores java.lang.Process, starts a reader thread and awaits CountDownLatch. Safe later integration must satisfy each lifecycle path independently.

## Production blockers
A production supervisor needs original launcher argv/cwd/env and script dependency closure, secure script capability broker, isolated Node port/proxied networking, child startup/READY barrier with correct sequencing, early-crash propagation, stdin and stream backpressure, exact stop/restart parity, bounded host socket owner continuity and original chat/browser/attachment regression. Avoid any direct original host ProcessBuilder fallback and never kill a live generating model while swapping owners.

Current P52 callback is test-only in isolated DSH-derived app, not a fixed-signed v139 update or original EngineManager Process assignment.

P52_LIVE_P37_PROCESS_FACADE_DELIVERED=UNDER_CI
P52_PRODUCTION_ENGINE_MANAGER_COROUTINE=NOT_CONNECTED
P52_REAL_NODE_BOOT_SYNTETHIC_ONLY=YES
P52_OWNER_INSTALLED_DSH=UNTOUCHED
P52_FORMAL_FIXED_SIGNED_V139=BLOCKED
