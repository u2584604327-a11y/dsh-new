# DSH P20 — Android UID/egress proof and real ARM64 Node execution conditions

Date: 2026-10-29. **Not** a full DSH APK and **not** a VM implementation.

## Baseline evidence
- P18 Android35 P17/Binder identity + explicit UI grant/revoke: https://github.com/u2584604327-a11y/dshe/actions/runs/40839307072
- P19 exact original v138 Node+Termux-bootstrap static dependency file closure:
  https://github.com/u2584604327-a11y/dshe/actions/runs/40842882706
- Original runtime is AArch64 executable inside assets/node-runtime.bin, NOT an x86_64 executable.
- P19 pins the exact Node and bootstrap SHA256. It has NOT run the Node ELF.

## P20 disposable Android 35 test
- New package com.dsh.p20.boundary, not com.dsh.android.
- Host process explicitly has Android INTERNET permission.
- Host **successfully connects to its own 127.0.0.1 ephemeral listener** (positive control).
- Host generates a three-byte fixed-name synthetic PRIVATE application canary
  under its own files directory with mode 0600, validates it exists.
- A bound service is marked android:isolatedProcess=true and android:exported=false.
- Host passes ONLY its synthetic test path and loopback port to this worker.
- Worker reports actual Process.isIsolated()/UID and attempts to read the
  synthetic host-private canary, and to connect to the host loopback listener.
- Host authenticates the worker reply with framework Message.sendingUid and
  Process.isIsolatedUid; it never trusts client-supplied UID alone.
- Network denial only passes on a permission-related kernel/Java socket failure;
  ECONNREFUSED/timeouts must NOT count as an OS permission PASS.
- No internet target, external scanning, actual credentials, user data, Node
  executable, root, Shizuku, ADB app privileges or arbitrary shell tests.
- Builds signed only with a one-time throwaway test certificate and removes it.
- GitHub summary contains only synthetic PASS/FAIL markers, not user data.

## ABI hard boundary and architecture

- Existing Android35 CI emulator: x86_64.
- Exact original DSH Node: AArch64 ELF. **DO NOT** use an x86_64 synthetic
  Node smoke as if the actual executable had been migrated.
- The next real Node execution gate requires an Android ARM64 isolatedProcess
  context. Prefer a disposable ARM64 emulator with verified runtime feasibility
  or user-owned ARM64 debug-only device, never a production DSH overwrite.
- The original Node is linked against Termux files originally located in
  /data/data/com.termux/files/usr/lib. Package file presence is not the same
  as link-time resolution from an isolated UID.
- The security model must not depend on executing arbitrary writable files.
  Android target>=29 restricts execve from writable application data locations.
- Package-native executable/JNI architecture or a verified immutable loader
  must retain original Node bytes/sha and all DT_NEEDED closure; if not
  technically possible under isolated UID, STOP. No unsafe root/ptrace,
  memfd execution bypass or arbitrary host-private directory sharing.
- Until actual original ELF executes in isolated UID, never claim real DSH
  Node migration, strict VM isolation or genuine iOS/Windows identity.

## Hard integration and release gates

1. Prove the actual original AArch64 Node binary in a disposable isolated UID;
   capture Android/ELF linker failures without leaking app secrets.
2. Verify immutable runtime/library source and SELinux, no direct access to
   host-private files, credentials, arbitrary network, localhost privileges,
   shell, plugins or Java bridges.
3. Add real trusted host Binder broker with caller/worker INSTANCE validation,
   scope/size/destination allowlists, expiry, one-time consumption, revocation,
   explicit native user consent, and bounded audit logs.
4. Migrate original DSH runtime invocation graph, preserving streaming,
   conversations, attachments, browser and plugins.
5. Android ARM64 + x86_64 gates, startup ART and on-phone data-preserving
   signer/version verification must all PASS before any v139 release.
6. Signing key remains off GitHub, Actions, release artifacts and PR history.

Status:
P20_ANDROID35_DISPOSABLE_HOST_NETWORK_VS_ISOLATED_WORKER=CI_REQUIRED_BEFORE_PASS
P20_REAL_NODE_ARM64_EXECUTE_IN_ISOLATED_UID=NOT_IMPLEMENTED
P20_PRODUCTION_DSH_NODE_MIGRATION=NO
P20_DSH_REAL_PHONE_UPGRADE=NO
P20_RELEASE=BLOCKED

## CI execution history

- First Android35 run 40844452399: FAILED at test-host setup; no isolation result.
- Second Android35 run 40844827730: FAILED with Android `NetworkOnMainThreadException` during host-positive-control socket creation. This was a test design defect, not a UID isolation finding.
- Candidate follow-up moves both host and isolated socket operations to bounded worker threads. Treat outcome as UNKNOWN until the exact new run finishes and all mandatory markers pass.
