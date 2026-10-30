# P48 original DSH isolated child and P37 Process facade verification

## Exact inherited evidence
P47 verifies the original DSH v138 EngineManager main startup bridge denies host ProcessBuilder fallback. The original MainActivity and P43–P46 private Binder/UID/resource tests passed on Android35 x86_64 emulator.

## P48 exact implementation
1. Original com.dsh.android test-only trusted Activity first completes P43–P46 session and Binder authorization.
2. The same nonexported isolatedProcess Service accepts one additional request ONLY from that same original host UID and 256-bit session after P43 initiation, launching a FIXED system child command: /system/bin/id -u.
3. No caller-controlled binary, argv, cwd, env, networking, filesystem path, Node script or shell command can enter the child launch.
4. Isolated worker Messenger sends HELLO, bounded stdout/stderr and exit frames with monotone sequence; original host validates framework Message.sendingUid and authenticates its P37RemoteProcess facade.
5. Original host verifies child's actual id -u equals isolated Binder worker UID, stdout, EOF, waitFor and exitValue; P47 main DEX no-host-fallback and P43–P46 continue passing.
6. Existing SHA-pinned original APK resources/libs/classes2 DEX, Manifest permissions, exact target SDK and throwaway signer remain unchanged. No test binaries uploaded.

## Hard boundaries
This test does NOT execute the exact original ARM64 Node engine: emulator is x86_64. It proves a fixed synthetic system child in original DSH isolated Service, not EngineManager handoff. The original engine still intentionally fails to start at P47 gate without a real production supervisor, and other two EngineManager ProcessBuilder sites remain unchanged. No chat, WebView, photos, file browsing or original HTTP/WebSocket route parity. Not a real virtual machine. No privilege escalation, root exploit or Shizuku inside DSH; the disposable GitHub emulator harness uses adb root to block host UID outbound networking.

The APK uses a test-only exported diagnostic Activity and one-day incompatible signature. Never install it on owner's phone; never call this a production update or fixed-signed v139.

P48_ORIGINAL_IN_APP_P37_PROCESS_PROXY=UNDER_TEST
P48_PRODUCTION_ARM64_NODE_ISOLATION=NO
P48_ORIGINAL_ENGINE_MANAGER_PROXY_HANDOFF=NO
P48_OWNER_ARM64_ANDROID16=NOT_TESTED
P48_SIGNED_V139_RELEASE=BLOCKED

## P49 next
Implement explicit trusted startup context transfer and approved immutable original runtime assets; validate real Node's script/native dependencies, keep Binder UID/session/frame guarantees, READY, stdin, stop/restart and network broker. Only after those pass may P47 denial gate become a real Process adapter. Never silently fallback to unsandboxed host Node or use broad root.
