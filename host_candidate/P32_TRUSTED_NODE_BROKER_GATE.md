# P32 trusted Android Binder Node broker candidate

## P31 ARM64 physical-phone evidence
The user-provided P31 Android API36 result has been recorded in
host_candidate/P31_OWNER_ANDROID36_RESULT_20261029.md.
The exact original Node and ten libraries passed SHA checks. Isolated
Binder sender, Worker and Node child UIDs all equaled 99055.
Node read its own ELF magic header, but could not stat host-private
canary parent/file and could not read it (all ENOENT) while host SHA256
confirmed file unchanged. Fixed loopback and TEST-NET TCP connect calls
failed with EACCES. This is a scoped owner-reported device proof, NOT a
full filesystem, SELinux cause, generic network, VM or DSH app proof.

## Actual repository blocker
README.md and HOST_INTEGRATION_GATE_STATUS.md identify this as a signed
APK audit/DEX-patch workspace, NOT complete source of native DSH
MainActivity and its running Node bridge. Therefore a new Java class
can compile, yet have NO live invocation edge in the original APK.
Do not mislabel this as migration of DSH or sign v139.

## Concrete new engineering code
- p32_node_ipc/src/com/dsh/p32/P32NodeIpcBroker.java: host-only broker
  REUSES P17CapabilityGate instead of reimplementing its random grant
  ledger, lifetime clock, one-time consume, replay denial or revocation.
- p32_node_ipc/android/com/dsh/p32/P32AndroidBinderPort.java:
  real Android Messenger API35 source verifies framework sendingUid
  through Process.isIsolatedUid, host-minted session, explicit trusted
  host UI approval method, one-time synthetic result and lifecycle revoke.
  No unrestricted file, HTTP/socket, raw path, headers or shell support.
- p32_node_ipc/test/com/dsh/p32/P32NodeIpcBrokerTest.java:
  Java8 deterministic security tests for preapproval denial, strict
  canonical Node frame, token expiry, wrong UID/session, malformed
  input burned, background/death/rebind and 20-way concurrent requests
  with exactly one grant consumption.
- The only allowed operation is METADATA_COUNT with a numeric 1..8
  and maximum 10-second 256-bit grant, bound to authenticated UID
  and current worker session. No arbitrary code or user data.

## Missing real integration
1. Obtain authorized original native MainActivity/Node invocation graph
   source or independently verified ART hook; do not overwrite v138.
2. Connect exact SHA-pinned Node stdout to isolated worker and from there
   through Android Messenger into host adapter. Do not trust Bundle UID.
3. Connect real native UI click approval; no JS/AI/Node initiated grants.
4. Exercise actual Android ART pregrant, one click, replay, wrong UID,
   expiry, background and worker death, and then full DSH regressions.
5. Perform separate diagnostic send/attachment review and FD pinning
   only with explicit user approval. No generic path or URL broker.
6. Original signing key remains offline; no production release.

P31_NODE_REAL_ARM64_ISOLATED_UID_PRIVATE_CANARY_TCP=PASS_NARROW_OWNER_REPORT
P32_JVM_GRANT_AND_CONCURRENT_TESTS=PASS_JAVA8_ONE_OF_20
P32_ANDROID_MESSENGER_SOURCE_COMPILATION=PASS_API35
P32_NODE_STDOUT_TO_REAL_DSH_HOST_IPC=NOT_IMPLEMENTED
P32_DSH_REAL_NATIVE_MAIN_ACTIVITY_WIRED=NO
P32_FIXED_SIGNATURE_V139_RELEASE=BLOCKED


## Real CI / lifecycle evidence (2026-10-29)
Full P32 Java8 + Android35 compilation SUCCESS:
https://github.com/u2584604327-a11y/dshe/actions/runs/40876928271

Verified security test output:
- P32_ONE_SHOT_BINDER_POLICY_SYNTHETIC_TESTS=PASS
- P32_NO_AUTHORIZATION_WITHOUT_TRUSTED_UI=PASS
- P32_SCOPE_STRICT_NODE_STDOUT_AND_SIZE_BOUND=PASS
- P32_TOKEN_EXPIRY_AND_LIFECYCLE_REVOKE=PASS
- P32_PARALLEL_ONESHOT_1_OF_20=PASS
- P32_ACTUAL_DSH_HOST_RUNTIME_CONNECTION=NOT_IMPLEMENTED
- P32_RELEASE=BLOCKED

The real Android35 Messenger adapter compiles in GitHub Actions but has
not been installed into the original DSH App; the class alone cannot
prove an actual Binder handshake or real Node output-to-host routing.
A trusted native service-binding initiation method now arms exactly
one inbound framework-authenticated HELLO; additional unsolicited HELLOs
cannot silently reset an approved live worker instance.

Owner-authorized cleanup of completed private P31 testing Draft:
https://github.com/u2584604327-a11y/dshe/actions/runs/40876928418
Result SUCCESS; separately authenticated releases listing contains no
tag p31-private-positive-fs-control-20261029. Its underlying GitHub
P31 source and owner-provided text evidence remain in the private repo.
No original v138 signed APK Release, credential or production was touched.

P32_NATIVE_BINDER_IPC_ADAPTER_COMPILED=YES
P32_NATIVE_IPC_RUNTIME_GESTURE_AND_REAL_DSH_ART=NOT_TESTED
P32_SIGNED_V139_RELEASE=BLOCKED
