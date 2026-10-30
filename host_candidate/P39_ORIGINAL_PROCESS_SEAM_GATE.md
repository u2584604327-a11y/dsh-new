# P39 exact signed-original EngineManager Process interposition seam audit

Input = privately held signed original v138 APK, SHA256 `3ca56655d79afc57431636e340823e7071bc830615c485b0b9a30b6e3e5`.

Verified P38 owner report:
```
P38_REAL_ORIGINAL_NODE_PROCESS_STREAM=PASS
ANDROID_API=36
ABI=arm64-v8a
TRUSTED_HOST_UID=10414
WORKER_BINDER_UID=99069
VERIFIED_NODE_STDOUT=PASS
SEPARATE_STDERR=PASS
REAL_JAVA_PROCESS_PROXY_WAIT_EXIT=PASS
STATUS=REAL_NODE_STREAM_EXIT_AND_PROXY_EOF_VERIFIED
FAILURE=NONE
ORIGINAL_DSH_ENGINEMANAGER_PATCHED=NO
```

Owner-reported P38 success demonstrates P38 separate-package fixed Node eval stream and bound Worker, NOT a real DSH engine migration. A reported Worker UID is not a production app identity assertion.

P39 analyzes the original EngineManager family to enumerate Java Process, streams, ProcessBuilder and shutdown API callsites, exact method opcode, code offsets and P35-pinned lifecycle edges. It reads original APK only in private GitHub CI, emits a bounded method-API-only report to ephemeral runner files and deletes it in an always-run step. No APK, DEX literals, private configuration, original binary, user files, signatures or environment are uploaded or logged.

**No bytecode modification is undertaken.** Even an exact `invoke-virtual ProcessBuilder.start` site cannot be safely redirected without independently validating DEX method-id table, invocation register encoding, verifier behavior, complete actual v138 Process callsites, shutdown paths, ART loading, upstream input/environment semantics, original signature and user data backup. DSH v139 cannot be declared complete.

Required next gate after P39: only if this exact seam is compatible, implement and test a protected host-side factory and authenticated isolated Binder supervisor on an independent copy of the real original engine, never on phone-installed v138. Distinct root/Termux/Shizuku/shell ProcessBuilder calls must remain untouched; no unrestricted filesystem or Node tool privileges may be introduced. Verify complete chat/browser/media/diagnostic functionality before signing or overlay installation.

P39_APK_MUTATED=NO
P39_DSH_ENGINEMANAGER_WIRED=NO
P39_REAL_V139_RELEASE=BLOCKED
