# P35: exact original DSH EngineManager spawn-and-shutdown integration feasibility gate

## Carried real evidence
- P31 owner-reported Android API36 arm64 original Node v26.4.0: real
  Node child UID = Android Binder isolated Worker UID, positive Node fs
  ELF read, host private canary path invisible while host canary SHA
  unchanged, localhost and TEST-NET TCP EACCES. Narrow test ONLY.
- P32 Java8 host capability ledger + genuine Android Messenger adapter
  compile CI PASS. P34 actual Android35 x86_64 isolated Service to
  trusted Activity via Binder + genuine native Button tap PASS including
  no grant before trusted tap, one request, replay denial, background
  lifecycle revocation. Final run https://github.com/u2584604327-a11y/dshe/actions/runs/40882377690
- P33 exact SHA-pinned original v138 APK scanned 4,592 app methods and
  6,149 direct app invokes, finding EngineManager$start$2.invokeSuspend
  -> ProcessBuilder.start at classes.dex code_off=3163260, PC=3912.
  P33 follow-up (code SHA 48fa7c941505dddd026fa4ebc406611398d97f4b)
  also exposed non-interchangeable EngineManager.probeBoot,
  runDumpConfig, TermuxBootstrap.nodeIsUsable and dangerous shell
  and root process callsites.

## Recovered older host sources, not discarded
Prior Library packs:
- DSH_V139_NATIVE_INTEGRATION_SOURCE_AND_EVIDENCE.zip
- DSH_V139_P2_FD_REVIEW_HOST_SOURCE_AND_EVIDENCE.zip
- DSH_V139_P3_PROJECTION_BINDING_SOURCE_ONLY.zip
- DSH_V139_P4_SINGLE_USE_DIAGNOSTIC_DISPATCH_SOURCE_ONLY.zip

These contain reusable AndroidFdQueue, NativeDiagnosticReview,
ConsentLedger, DiagnosticDispatchGate, BrowserCoordinator, settings and
browser patches, JVM tests and reference evidence; they do NOT contain
a complete original MainActivity and EngineManager Kotlin/Java source
project, nor a live v139 Binder worker or callback migration.
P2 NEXT_ACCEPTANCE explicitly requires real host callsite integration.

## P35 actual next audit
The new pinned signed-v138 analysis script isolates exactly the
EngineManager$start$2.invokeSuspend coroutine:
- Reject any APK SHA or method code offset/ProcessBuilder.start
  instruction offset drift before extracting anything.
- Collect bounded actual invoked method API names near the spawn
  instruction, plus original EngineManager start/stop/preflight/probeBoot/
  dumpConfig and TermuxBootstrap nodeIsUsable method calls.
- Never emit strings, command arguments, env vars, file paths, API keys,
  DEX bytes or private user data; only bounded method signatures and
  bytecode callsite offsets.
- Analyze stable process lifecycle, stream and startup call mechanics
  before deciding on an interposition seam, rather than patching all
  ProcessBuilder.start invocations (which would break shell/root/ADB).
- Original APK is ephemeral private CI input and deleted; neither APK
  nor source-derived JSON is committed or uploaded.
- The inspection deliberately DOES NOT rewrite existing DEX, create an
  APK, claim ART/live call replacement, or claim Node stdout now flows
  through P32 trusted Binder.

## Critical gates for genuine DSH host wiring (still pending)
1. Verify original engine process argument/working directory/lifecycle/
   signal/stream configuration under a sanctioned synthetic runtime
   (without logging credentials), including original chat data retention.
2. Connect only the actual original Node startup/supervisor path to an
   Android isolatedProcess Worker; keep shell/RootAccess/WirelessDebugging
   and TermuxBootstrap probes separate and fail closed.
3. Host must authenticate Binder UID and maintain real trusted native UI
   per-packet one-use grants, not a WebView/Node/AI-defined consent flag.
4. Expose only minimal guarded protocol, not unrestricted Node eval,
   file paths, shell, upload endpoints or browser access.
5. Test real Node callback to Binder host plus full DSH streaming,
   file/image, WebView, API key, background and lifecycle regressions.
6. Only after source/ART and safety gates may version 139 signed updates
   be separately authorized. Original signing key never in source/CI.

P35_SIGNED_V138_ENGINE_START_CONTRACT=PASS_CI_40886757918
P35_P32_BROKER_REAL_NODE_IN_DSH=NOT_CONNECTED
P35_NATIVE_DIAGNOSTIC_SEND_APPROVAL_IN_DSH=NOT_CONNECTED
P35_FULL_ORIGINAL_CHAT_AND_BROWSER_PARITY=NOT_VERIFIED
P35_SIGNED_RELEASE=BLOCKED

## Actual signed-original v138 DEX findings (2026-10-29)
Verified original exact engine startup at
https://github.com/u2584604327-a11y/dshe/actions/runs/40886757918

- Baseline SHA, EngineManager$start$2.invokeSuspend code_off 3163260
  and unique ProcessBuilder.start PC 3912 are verified.
- Before spawn the original engine builds environment from homeDir,
  Android getCacheDir/getFilesDir, nodeOptions, Termux mirror
  environment and ShizukuChannel.socketName. It records active env
  and invokes maybeIsolateBadBundles, requestRestart,
  resumePrivilegedChannel and ensureRescuePrompt.
  No original environment variable values were emitted.
- Immediately AFTER ProcessBuilder.start(): PC 3924 sets the original
  Java Process into EngineManager.process; PC 3980 constructs a
  lambda capturing Process, CountDownLatch, CoroutineScope,
  EngineManager and Regex; PC 3986 creates reader Thread;
  PC 4010 calls Thread.start; PC 4026 waits on CountDownLatch;
  PC 4674 updates MutableStateFlow Ready-related value.
- The exact P35 source assertions now fail closed if these API
  edges drift: original process handle, reader thread, startup
  latch and StateFlow state transition are required semantics.
- Therefore replacing only ProcessBuilder.start with a Binder
  message would BREAK original engine lifecycle and chat readiness.
  A validated process-proxy or ported supervised state machine
  is necessary, not a no-op spawn method patch.
- Static observations do not prove runtime host migration.

P35_REAL_HOST_PROCESS_LIFECYCLE_OBSERVED=PASS_STATIC_EXACT
P35_ORIGINAL_PROCESS_READER_LATCH_STATEFLOW_DEPS=CONFIRMED
P35_ACTUAL_NODE_OUT_TO_P32_BINDER=NOT_CONNECTED
P35_ORIGINAL_ENGINEMANAGER_PATCHED=NO
P35_V139_RELEASE=BLOCKED
