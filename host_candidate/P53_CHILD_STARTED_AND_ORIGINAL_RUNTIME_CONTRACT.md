# P53: exact child-start acknowledgement (post-ProcessBuilder.start) and original runtime staging boundary

## Observed blocker corrected
P52 delivered a genuine P37 Java Process proxy at Binder HELLO, but in P48/P50 the Worker sent HELLO **before** invoking ProcessBuilder.start(). Therefore P52 delivered the facade even if actual child creation failed. That was inappropriate for a future EngineManager handoff.

## P53 substantive changes
- Reserve one authenticated Messenger event `CHILD_STARTED=489`, sent by the isolated Worker only after real `ProcessBuilder.start()` returns. P48 fixed id child and P50 original SHA-verified ARM64 Node child both send this ACK before any stdout/stderr/EXIT messages. It is NOT a production READY signal or an independent kernel attestation.
- `P53StartOrder` is a real Java 8 state machine compiled into the derived original DSH classes3.dex. It mandates HELLO(seq0) -> CHILD_STARTED(seq1) -> bounded stdout/stderr frames and EXIT. Allows explicit FAIL before child spawn; rejects pre-start STDOUT/STDERR/EXIT, duplicate HELLO/STARTED, unknown event, replayed, skipped or negative sequence and post-terminal frames.
- Host `P48HostProcessProbe` validates **Android Message.sendingUid**, 256-bit host session, and the P53 sequence/state machine before dispatch. It only invokes `LiveProcessReceiver` on the authenticated CHILD_STARTED event. A wrong frame kills P37's transport and fails closed; no host ProcessBuilder fallback is possible. The original V138 `EngineManager.probeBoot` and `runDumpConfig` callsites remain preserved.
- Pure-Java negative tests are executed in private CI; actual Android35 x86 disposable distinct-package test ensures P51/P52 positive Worker/Binder/P37 regression plus P53's native host start-ack signals, and cleanup. Original production Node scripts, user data and fixed signing are not touched.

## Separate exact original engine asset inventory
P53 additionally inspects only the SHA-pinned original signed v138 `assets/engine.bin` inside private CI. It classifies compressed container type and counts JS/MJS/CJS/JSON/native-addon ZIP entries if the container is ZIP, without writing extracted scripts, printing source paths, leaking original Node binaries, or granting runtime capabilities. If compressed as a non-ZIP container, counts remain unknown. This narrows how a future immutable real production script broker might work; it does not identify the exact production command/working directory/environment or prove a runnable script closure.

## Absolutely NOT complete
P53 guarantees a worker-reported successful ProcessBuilder.start() **before** handoff, but not that the child emitted its first byte, remained alive, loaded any script, bound a network socket, or reached real READY. P50 owner ARM64 report validated a pinned original Node running a fixed `--eval` synthetic program in an isolated app; it is not the original production runtime. Original Kotlin EngineManager coroutine has NOT been connected to P37 and P47 denies its unsafe host start. Original DSH native Application/MainActivity, production script closure, argv/cwd/env, Socket ownership, Shizuku/Termux integration, chat/browser/attachments, background service persistence and fixed cert remain untested.

Required next: safe exact original signed-v138 runtime asset inspection, then a content-hash-pinned real production script broker with local native authorization and bounded IPC; only then a supervised production Process replacement can be evaluated against original EngineManager's reader thread/CountDownLatch/StateFlow READY edges. No general exec, arbitrary environment, raw host-private paths, hidden root, or elevated permissions.

P53_POST_EXECVE_PROCESS_PROXY_HANDOFF=UNDER_TEST
P53_REAL_NODE_PRODUCTION_READY=NO
P53_ORIGINAL_ENGINE_MANAGER_INTEGRATION=NO
P53_SIGNED_V139_RELEASE=BLOCKED
