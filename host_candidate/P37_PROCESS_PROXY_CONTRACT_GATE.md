# P37 — isolated-engine Java Process compatibility facade (SOURCE ONLY)

## P35/P36 observed constraints
- P35 verified exact signed-v138 DEX EngineManager start coroutine: ProcessBuilder.start at PC 3912, process stored at PC 3924, reader lambda at PC 3980, Thread construction at PC 3986/start PC 4010, CountDownLatch.await at PC 4026, Ready-related update PC 4674.
- P36 is a separate throwaway test app; physical-device end-to-end result is NOT VERIFIED. It does not connect original DSH EngineManager.
- This repo lacks complete independently buildable original DSH EngineManager/MainActivity source. NO bytecode patch authorized.

## Delivered narrow seam
- P37RemoteProcess extends java.lang.Process with ordered, separate bounded streams (64 KiB each, max 4 KiB per incoming callback).
- waitFor, timed waitFor, exitValue, isAlive require authenticated remote exit, not speculative shutdown ACK.
- destroy and destroyForcibly request remote stop/kill at most once, without pretending worker has acknowledged.
- Remote stdout/stderr/exit must match trusted platform Binder UID and host-issued session on every callback. Claimed UID from Node or Bundle must never qualify.
- Binder callbacks never block on buffer pressure. Overflow fails closed and discards buffered data.
- Transport loss, failed remote control, stop deadline and identity mismatch unblock readers/waiters with synthetic exit code 125. This does NOT prove physical child termination.
- Unverified stdin writes explicitly fail, rather than silently drop or execute.
- Local Java 8 contract test: 52 assertions passed, real streams/thread semantics. This does NOT run Android Binder or original Node.

## Mandatory remaining gates before any real host patch
1. Acquire authorized original EngineManager/MainActivity source or independently validate an exact-signature method-local patch inside a private disposable package. Preserve unrelated ProcessBuilder.start in Termux, root, Shizuku, shell, probeBoot and dumpConfig.
2. Implement Android nonexported isolated Service + trusted Binder supervisor. Only platform Message.sendingUid and host-issued session can deliver stdout/stderr/exit frames. Sequence, frame sizes, EOF, child PID, stop/kill ACK and timeout watchdog are required.
3. Node frame never grants itself tools or diagnostic upload rights. P32 currently grants only synthetic METADATA_COUNT; production stdout streaming needs a separate bounded protocol.
4. Preserve required environment/host directory semantics with minimal capability brokers, not broad host-file copying, exposed credentials, device spoofing or implicit network access. P31 canary ENOENT proves nonvisibility, not ACL denial; P36 fixed --eval is not actual engine startup.
5. Audit all real Process callsites (pid/toHandle, stdin, reader regex, latch, Ready, signal, poll, shutdown, restart). Missing semantics block integration.
6. Verify original chat streaming, browser/WebView, tools, files/images, per-packet diagnostic consent, API keys, data retention, background lifecycle and restart on user device.
7. Sign/install only under separate explicit approval after backup. Keep PR Draft.

PROCESS_FACADE_JAVA8_SOURCE_AND_TESTS=LOCAL_PASS_52_ASSERTIONS
P37_PROCESS_HANDLE_AND_STREAM_SEMANTICS=CONTRACT_ONLY
P37_ANDROID_AUTHENTICATED_BINDER_ADAPTER=NOT_IMPLEMENTED
P37_REAL_DSH_ENGINEMANAGER_WIRING=NO
P37_ANDROID_OWNER_PHONE_RUN=NOT_TESTED
P37_P36_REAL_NODE_E2E=NOT_TESTED
P37_CHAT_BROWSER_FILE_DIAGNOSTIC_PARITY=NOT_TESTED
P37_V139_RELEASE=BLOCKED
