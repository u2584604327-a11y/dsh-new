# P38 private original Node / P37 Process facade Android integration gate

This phase is a **separate owner-only Android test application**, not DSH v139.

## Real architecture
- Exact original signed-v138 Node ARM64 executable and 10 ELF libraries, immutable source SHA and runtime digest checks, API34+ isolatedProcess worker, no requested Android permissions.
- Trusted host Activity mints 256-bit session. Platform Message.sendingUid must identify a single isolated worker. Strict monotonically increasing sequence on stdout, stderr and exit frames. Node stdout cannot supply a grant or a UID trust anchor.
- The real Node child executes ONLY fixed in-package JavaScript: prints its actual process.getuid(), BOOT and READY to stdout, and a fixed marker to stderr; then actually terminates. It cannot read personal files or send network traffic as part of this test code.
- Worker streams chunks from the real child stdout/stderr to trusted host with real Android Messenger; P37RemoteProcess extends java.lang.Process and provides ordered bounded streams, waitFor, exitValue, destroy/destroyForcibly and loss-handling.
- Host reads both streams on independent threads and only marks PASS for exact UID, bytes, separate stderr and genuine zero exit. A one-way claimed worker status is not sufficient. Backgrounding revokes trust and requests kill.

## Hard limits
- GitHub CI proves **APK build, exact ELF hash, byte alignment, manifest permissions, code compilation, static checks and local JVM contract tests only**.
- Real physical Android owner test remains necessary for Binder sender UID, isolated native execution, stream and exit semantics. Testing the APK has NOT tested original DSH EngineManager.
- No original DSH MainActivity / EngineManager full source, no production startup/shutdown callsite interposition, no runtime environment integration.
- P36's one-shot P32 grants are NOT ported to arbitrary Node capabilities; P38 sends only bounded fixed stream output and has no user actions beyond its test.
- Original signed APK, signing key, data and installed app remain unchanged. This APK uses a throwaway signing certificate and separate application ID.

P38_REAL_NODE_STREAM_ANDROID_SOURCE=IMPLEMENTED_TEST_PACKAGE
P38_JAVA_PROCESS_FACADE=IMPLEMENTED_SOURCE_AND_JVM_TESTS
P38_CI_APK_AND_SIGNATURE=AWAITING_GITHUB_ACTIONS
P38_ANDROID16_PHYSICAL_DEVICE=NOT_TESTED
P38_ORIGINAL_DSH_ENGINEMANAGER_WIRED=NO
P38_CHAT_BROWSER_ATTACHMENTS_REGRESSION=NO
P38_RELEASE_V139=BLOCKED
