# P28 real-device result received from the owner (2026-10-29)

## Provenance and exact scope
The owner installed the separately signed P28 test APK on their own Android
device and pasted the **locally copied app report** into ChatGPT. This is an
owner-reported local measurement, **not** independently signed device
attestation, not GitHub-hosted Android evidence, and not DSH functional integration.

Reported:
- P28 status: `PASS_ORIGINAL_NODE_VERSION_IN_ISOLATED_WORKER`
- Android API: 36; primary ABI: arm64-v8a.
- Host-observed Binder sendingUID is Android isolated UID: PASS.
- Exact original Node and 10 original ARM64 library SHA-256: PASS.
- Original Node `--version` process: exit 0 and `v26.4.0`.
- Phase: `VERSION_AND_HASH_GATE_FINISHED`.
- Note: `NODE_BOOT_ONLY_NOT_EGRESS_OR_FULL_VM_PASS`.

## Honest remaining gates
No independent child-process UID check existed in P28.
No Node-origin attempts to read host-private files or open local/outbound
network sockets occurred. User did not report a kernel SELinux audit,
a proof of virtual machine isolation, DSH native host migration, access
control safety for JS, media or file operations, or a real v139 release.

The earlier "Node executable cannot boot under Android arm64-v8a" blocker
is now resolved for this user's Android API36 test run, **not** generalized
to other devices or every possible workload. P29 must provide real
`process.getuid()` result from the original Node child plus fixed Node-origin
private-app-only canary and localhost/testnet-denial probes. All probes must
fail-closed and must not touch real user data, external services or arbitrary
scripts.

P28_USER_REPORTED_REAL_ARM64_NODE_VERSION=PASS_API36_NODE_v26.4.0
P28_INDEPENDENT_NODE_CHILD_UID=NOT_TESTED
P28_REAL_NODE_EGRESS_AND_PRIVATE_FS=NOT_TESTED
P28_DSH_V139_RELEASE=BLOCKED
