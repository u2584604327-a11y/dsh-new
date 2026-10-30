# P30 user device result and P31 Node FS positive control

## P30 actual-owner device report 2026-10-29
- Android 16 / API36 arm64-v8a, original Node + ten pinned ARM64 ELF PASS.
- Actual framework Binder sendingUid=99054 matches workerUid=99054, both
  isolated: PASS.
- Actual original Node process.getuid()=99054, exit 0: PASS.
- P30 host's own random 32-byte app-private canary created and SHA-256
  verified unchanged after isolated Node finished: PASS.
- Original Node file read: OTHER_ENOENT while host file still exists.
- Fixed native TCP connect 127.0.0.1:9 and 198.51.100.1:443:
  both DENIED_EACCES.

This is the owner's copied local device report, not cryptographic hardware
attestation. It is sufficient to close *these* real Node process UID,
specific test-file non-visibility and TCP-denial experiments as PASS_NARROW.
It is NOT evidence that ENOENT equals an EACCES/EPERM ACL refusal or proof
that SELinux alone caused the pathname failure. Android isolated processes
use separate app UIDs and restricted SELinux access (Chromium sandbox docs).
Virtual-machine or physical device impersonation is not implied.

## P31 incremental new evidence
To avoid mistaking broken Node filesystem APIs for sandbox isolation:
- Run the *original*, hash-pinned Node executable in isolatedProcess.
- Positive filesystem control: use Node fs.openSync(process.execPath,'r'),
  read exactly four bytes at offset zero and compare to ELF 0x7f454c46,
  then close the FD. Never emit real binary bytes.
- Negative test: real Node fs.statSync(parent of fixed canary) and
  fs.statSync(canonical canary) plus fs.readFileSync of the random
  P31-only app-private host canary; record only coarse errno codes.
- Host creates 32-byte canary before Binder, retains its SHA256 digest,
  verifies same file and bytes after Node finishes, then deletes file.
- Enforce actual framework Binder sending UID -> isolated Worker UID ->
  original Node process.getuid chain and exact original ELF hashes.
- Node uses fixed TCP connect to loopback and RFC5737 TEST-NET-2; no
  payload or user chat data. Denial only EACCES/EPERM.
- If Node's own ELF cannot be read, BLOCKED_POSITIVE_FILESYSTEM_CONTROL
  (never claim private-file isolation).
- If Node ELF read succeeds, host canary remains unchanged, Node canary
  stat and read return ENOENT, UID/ELF and two TCP denials all pass,
  classify PASS_NARROW_NODE_FS_WORKS_HOST_PRIVATE_CANARY_INVISIBLE_NOT_ACL_DENIAL.
- If direct private file access is EACCES or EPERM, allow separate
  PASS_STRICT_FIXED... class. Any private read succeeds = FAIL/BLOCKED.
- The cause of ENOENT (path namespace, directory traversal restrictions,
  runtime virtual filesystem or SELinux behavior) is UNKNOWN without
  additional OS-level diagnosis; avoid unsupported mechanism attribution.

## Authorized delivery and cleanup
Separate independent com.dsh.p31.nodeprobe package; min API34; original
Node bytes exactly pinned; zero manifest permissions; temporary signing.
No DSH v138 overwrite, production release, user personal-file scanning,
root/ADB or automatic diagnostics. Private Draft Release only with 3 files.
After private P31 verified, delete previously user-tested P30 Draft
with exact identity checks. Do not delete v138 baseline or GitHub PRs.

## Status
P30_REAL_NODE_UID_MATCH=PASS_OWNER_REPORT
P30_REAL_NODE_2_TCP_EACCES=PASS_OWNER_REPORT
P30_HOST_PRIVATE_CANARY_UNCHANGED=PASS_OWNER_REPORT
P30_ORIGINAL_NODE_PRIVATE_CANARY_PATH=ENOENT_OBSERVED_NOT_ACL_PASS
P31_ORIGINAL_NODE_POSITIVE_FS_CONTROL=AWAITING_ON_DEVICE
P31_REAL_ORIGINAL_NODE_CANARY_PARENT_STAT=AWAITING_ON_DEVICE
P31_REAL_ORIGINAL_NODE_CANARY_FILE_STAT=AWAITING_ON_DEVICE
P31_FULL_DSH_NATIVE_HOST_INTEGRATION=NOT_TESTED
P31_DSH_V139_RELEASE=BLOCKED
