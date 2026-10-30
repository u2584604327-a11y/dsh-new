# P31 owner-reported Android API36 original Node real process evidence

## Source and validity
Owner installed the separately signed P31 test APK on their personal
arm64-v8a Android API36 device and copied the application text report
into the ChatGPT conversation (2026-10-29). These are genuine local
device-app observations **as reported by owner**, not remote cryptographic
hardware attestation, or Android platform logcat/SELinux root-cause proof.

## Exact owner-reported result
P31_STATUS=PASS_NARROW_NODE_FS_WORKS_HOST_PRIVATE_CANARY_INVISIBLE_NOT_ACL_DENIAL
ANDROID_API=36
ANDROID_PRIMARY_ABI=arm64-v8a
HOST_BINDER_SENDING_UID=99055
WORKER_REPORTED_UID=99055
WORKER_BINDER_ISOLATED_UID=PASS
HOST_PRIVATE_CANARY_CREATED=PASS
HOST_PRIVATE_CANARY_STABLE_AFTER=PASS
EXACT_ORIGINAL_NODE_11_ELF_SHA=PASS
REAL_NODE_CHILD_UID=99055
NODE_CHILD_UID_EQUALS_WORKER=PASS
REAL_NODE_OWN_ELF_HEADER_READ=PASS_ELF_MAGIC
REAL_NODE_HOST_CANARY_PARENT_STAT=OTHER_ENOENT
REAL_NODE_HOST_CANARY_STAT=OTHER_ENOENT
REAL_NODE_PRIVATE_CANARY_READ=OTHER_ENOENT
FILE_ACCESS_DENIED_BY_ERRNO=NOT_PROVEN
NODE_FILESYSTEM_POSITIVE_CONTROL=PASS
FILE_NOT_VISIBLE_WHILE_HOST_CANARY_EXISTS=OBSERVED
REAL_NODE_LOOPBACK_TCP=DENIED_EACCES
REAL_NODE_TESTNET_TCP=DENIED_EACCES
NODE_PROBE_EXIT=0
PHASE=FIXED_CHILD_BOUNDARY_PROBE_FINISHED
NOTE=DIRECT_CANARY_READ_ENOENT_NOT_ACL_DENIAL
DSH_FULL_NATIVE_HOST_INTEGRATION=NO
STRONG_VM_OR_DEVICE_IMPERSONATION=NOT_PROVEN
V139_RELEASE=BLOCKED

## Conservative interpretation
- All three observed UIDs match at isolated UID 99055, original pinned
  Node read its own ELF signature successfully and returned exit 0.
- Host P31 canary was byte-stable; Node could not stat the host-private
  directory/file or read the file (ENOENT). The positive file read rules
  out "all Node fs operations nonfunctional" but does not establish a
  specific SELinux/filesystem namespace cause nor prove EACCES/EPERM.
- Fixed TCP connect attempts to 127.0.0.1:9 and RFC5737 reserved
  198.51.100.1:443 both failed with explicit EACCES. This validates
  these concrete operations only, not all networking or future host bridges.
- Original untrusted Node **not** wired into real DSH MainActivity,
  browser, tools, attachments, streaming, API keys or native app dialogs.
- This evidence is sufficient to close isolated original Node elementary
  runtime/UID, private canary visibility and fixed TCP test gates,
  but production v139 remains blocked.

NEXT_REQUIREMENT=TRUSTED_HOST_BINDER_AUTHORIZER_AND_ACTUAL_DSH_WIRING
DSH_FULL_HOST_SOURCE_IN_THIS_REPOSITORY=NO
DO_NOT_SIGN_OR_RELEASE_V139=YES
