# DSH P23 installed APK ZIP loader forensic controls

Date: 2026-10-29. This is independent disposable Android35 x86_64 code; no original ARM64 Node executable.

## Baseline
- P18 actual bound isolatedProcess service and capability broker tested on Android35: PASS.
- P20 host INTERNET positive control vs isolated worker local socket and host-private file denial: PASS.
- P21 original v138 ARM64 Node+10 transitive libraries, 16 KiB ELF and APK ZIP static staging: PASS, **no Node execution**.
- P22 actual Android35 x86_64 execve with versioned DT_NEEDED .so.3: exit 1 CANNOT LINK EXECUTABLE.
- P22 native Bionic dlopen to APK!/lib/x86_64/libp22version.so.3: test returned -21 (dlerror classified "not found").
- Java System.load of the same ZIP path: UnsatisfiedLinkError.
- P22 PR #6 remains Draft, release blocked.

## Actual P23 change

Test case deliberately controls **the same ELF bytes under three archive names**:
1. assets/p23control.so
2. assets/p23control.so.3
3. lib/x86_64/libp22version.so.3

All three must retain byte-identical SHA256, be STORED (no ZIP compression)
and align their ZIP data offsets to 16 KiB. A fixed-purpose JNI bridge
libp23bridge.so, which is installer-extractable, calls native Bionic dlopen
on each path. It cannot accept arbitrary file paths, user URLs, external
network, shell, secrets or DSH tool commands.

The Android35 disposable APK has no Android permissions and contains one
non-exported isolatedProcess service. The worker:
- uses platform ApplicationInfo.sourceDir to resolve its own installed APK;
- checks that the APK is a readable ordinary file;
- opens the actual APK with Java ZipFile inside isolated UID;
- opens each of the three STORED entries and verifies bounded bytes and
  matching SHA256, without printing/exfiltrating paths, content or private data;
- separately loads installed JNI bridge;
- invokes three direct native dlopen fixed-path tests and returns three
  individual codes;
- trusted host checks Binder framework Message.sendingUid is an isolated UID,
  plus the reported UID matches.

P23 CI **only passes characterization gates** when archive access, entry
identity, JNI bridge, actual Binder UID and real executed native variants
have all returned. Individual dlopen FAIL remains explicitly BLOCKED and does
not become a loader PASS.

### Why both success and failures matter
If installed APK and all ZIP entry contents are readable, but dlopen still
reports "not found", that rules out APK entry loss and simple worker filesystem
denial for the measured test package, but does not settle linker namespaces,
ZIP path syntax, Bionic restrictions or dependencies. In particular, the
original v138 ARM64 Node may behave differently.

## Stop conditions

No production APK, original signing key, real phone install, credential
access, root, Shizuku, ADB privileges inside app or production internet
requests. If exact installed controls cannot be observed, FAIL/UNKNOWN.

P23_INSTALLED_APK_POSITIVE_CONTROL=PASS_ANDROID35
P23_BIONIC_ASSET_PLAIN=PASS_ANDROID35
P23_BIONIC_ASSET_VERSIONED=BLOCKED_ERROR_MINUS_21
P23_BIONIC_NATIVE_VERSIONED=BLOCKED_ERROR_MINUS_21
P23_ACTUAL_DSH_ARM64_NODE_BOOT=NOT_TESTED
P23_PRODUCTION_RUNTIME_INTEGRATION=NO
P23_RELEASE=BLOCKED


## Executed evidence — final 2026-10-29

GitHub Actions run: https://github.com/u2584604327-a11y/dshe/actions/runs/40854762433

Real Android35 x86_64 emulator results:
- P23_INSTALLED_APK_PATH_AND_ALL_NATIVE_BYTES=PASS_ANDROID35
- P23_REAL_ISOLATED_UID_AUTHENTICATION=PASS_ANDROID35
- P23_ASSET_PLAIN_REAL_BIONIC_DLOPEN=PASS_ANDROID35
- P23_ASSET_VERSIONED_REAL_BIONIC_DLOPEN=BLOCKED_ERROR_-21
- P23_NATIVE_VERSIONED_REAL_BIONIC_DLOPEN=BLOCKED_ERROR_-21
- P23_ORIGINAL_DSH_ARM64_NODE_BOOT=NOT_TESTED

The three ZIP ELF entries have exactly identical bytes, are all STORED,
16 KiB aligned, and verifiably readable from the installed isolated worker.
The same ELF loads when addressed as assets/p23control.so but not as
assets/p23control.so.3 or lib/x86_64/libp22version.so.3.
Within-assets comparison controls for byte identity and location prefix.
This rules out source asset loss and blanket ZIP loading denial for this
measured test package; filename suffix is a differentiating factor. The
exact internal Bionic reason is still not proven: test code -21 only
means dlerror contained "not found". Do not extrapolate to all devices,
versions, app targetSDKs or sonames.

## P24 design implication and stop

Original AArch64 Node DT_NEEDED includes .so.3, .so.78 and .so.1.
P23 has NOT demonstrated that renaming versioned library ZIP entries
to .so can satisfy DT_NEEDED of an unmodified exact original Node binary.

Follow-on options require independent feasibility and safety review:
1. A platform-supported installer-immutable native library/embedding layout,
   with compatible names/SONAME resolution for all original dependencies,
   no executable copying to writable private directories.
2. A separately reviewed JNI/libnode rebuilding strategy; such a new
   binary must NOT be described as SHA-identical to original v138 Node.
3. On actual ARM64 Android, verify execution, SELinux and Binder gates,
   blocked direct filesystem/network/shell escape, and real DSH regression.

Never patch original ELF and claim binary identity unchanged, weaken
isolatedProcess, grant root/Shizuku/ADB, or sign/publish v139 prematurely.
