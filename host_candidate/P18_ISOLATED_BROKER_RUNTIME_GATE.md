# DSH P18 — authenticated isolated Binder broker, gesture and lifecycle gate

Date: 2026-10-29. **Disposable prototype only**; do not install as the existing DSH package.

## Evidence inherited from P15 and P17

- P15 Android 35 isolated UID + private host-file refusal passed only in a separate probe:
  https://github.com/u2584604327-a11y/dshe/actions/runs/40834677353
- P17 JVM one-time scope-bound ledger passed; P17 Android Binder/UI test **failed**:
  https://github.com/u2584604327-a11y/dshe/actions/runs/40835974704
  Unit job succeeded. Android job compiled/installed/started; its shell runner reported
  `P17_TRUSTED_UI_GRANT=PASS` missing. Do not mislabel it as an Android PASS.
- P17 ledger remains host-only, bounded to METADATA_COUNT; no arbitrary
  file, camera, clipboard, shell, network, diagnostics, credentials or URLs.

## P18 changes (not a DSH production integration)

1. Reject duplicate/replayed worker HELLO, invalid or unexpected isolated UID,
   malformed protocol data, and orphaned connection state. Worker records its
   framework-authenticated initial host sender UID and Messenger endpoint.
2. Revocation is explicit on Activity background, destroy, new binding, service
   disconnect, null binding, and binding death. A failed grant send revokes the
   just-minted token. UI clicks cannot mint tokens unless pregrant failure was
   received and the known bound worker is still connected.
3. Android test waits for verified pregrant denial before locating the actual
   enabled UI button. It performs **one** synthetic adb tap, never silently retries
   a privileged action, waits for the complete Binder result, and prints only
   fixed synthetic probe markers on failure. Returning to HOME must produce
   `P18_ALL_GRANTS_REVOKED=UI_BACKGROUND`.
4. Added 64-thread JVM concurrent-consume regression: a single grant can be
   accepted only once despite simultaneous calls; invalid scope must burn it.
5. GitHub PR test runs JVM and disposable Android 35 jobs; jobs generate only
   temporary test signing material and do not upload APK artifacts or secrets.

## Remaining constraints / stop conditions

- The P18 Android 35 emulator result is **UNVERIFIED until the specific PR run finishes**.
- This probe does **not** migrate DSH's original Node runtime, browser, shell,
  plugins or device functions to an isolated UID; the installed original still
  contains privileged same-UID execution paths. Do not call it a VM or strict
  privacy isolation.
- Activity background revocation deliberately disables further in-session grants
  until a fresh trusted handshake; a production lifecycle/resume protocol
  and Binder death-recipient coverage remain to be designed and tested.
- The next real-engine gate requires an immutable executable payload that an
  isolated UID can read, a strictly enumerated host capability protocol,
  independent file/network/child-process bypass tests, and confidential data
  inaccessible from the real worker. Do not forward arbitrary paths,
  FileDescriptors or user-controlled URLs through the broker.
- Full original DSH Android/native host code is not present in this audit repo.
  Existing P5 DEX packaging without an invocation edge is not a working
  Node-isolation integration.
- No default-branch merge, release APK, real-phone install, original signing
  certificate upload, production mutation, root/ADB privileged bypass, or
  OS/device identity claims. Keep user v138 installed and unchanged.

### Release status (as of PR creation)

```text
P15_ISOLATED_PROBE=PASS_STANDALONE
P17_JVM_LEDGER=PASS
P17_ANDROID_BINDER_GESTURE=FAIL_PREVIOUS_RUN
P18_PATCHED_SOURCE=COMMITTED_BRANCH_ONLY
P18_JVM_CONCURRENCY=WAITING_FOR_PR_CI
P18_ANDROID_GESTURE_AND_BACKGROUND_REVOKE=WAITING_FOR_PR_CI
PRODUCTION_DSH_NODE_ISOLATED=NO
ORIGINAL_CERTIFICATE_V139=NO
REAL_PHONE_PRESERVING_UPGRADE=NO
RELEASE=BLOCKED
```
