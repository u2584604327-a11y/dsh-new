# P26 multi-SONAME preload + original SQLite missing-SONAME analogue

Date: 2026-10-29. Disposable x86_64 test-only code.

## Why this is needed

P24 verified real Android35 x86_64 isolatedProcess LD_PRELOAD works
for ONE synthetic versioned DT_NEEDED library:
https://github.com/u2584604327-a11y/dshe/actions/runs/40856304638

P25 static inspect of the EXACT original signed v138 AArch64 Node found
TEN actual dependent ELF libraries, SIX versioned SONAMEs and ONE original
libsqlite3.so with missing DT_SONAME. All were packaged under installer
compatible .so filenames without changing bytes and with 16KiB alignment:
https://github.com/u2584604327-a11y/dshe/actions/runs/40857414215

P24 one-library PASS cannot prove actual multi-library preload or
Bionic filename fallback when SONAME is missing.

## P26 synthetic three-library real OS test

NDK builds native x86_64:
- file libp26core.so, ELF DT_SONAME libp26core.so.1;
- file libp26top.so, ELF DT_SONAME libp26top.so.2,
  DT_NEEDED libp26core.so.1;
- file libp26sqlite.so, intentionally no DT_SONAME;
- file libp26exec.so, DT_NEEDED libp26top.so.2 and libp26sqlite.so.

All are installer-extractable .so filenames, never writable-home executables.
The actual native program calls BOTH the top transitive library and the
no-SONAME sqlite-like library and prints only its actual getuid() on success.

A real Android35 isolatedProcess worker:
- runs the exact same libp26exec.so without LD_PRELOAD (must fail with
  missing top.so.2 dependency, FAIL if native executes without it);
- runs with the exact package-managed immutable core.so then top.so
  filenames listed in LD_PRELOAD, colon separated;
- requires native output matching the worker isolated Process.myUid(),
  exit 0, and success of both transitive and missing-SONAME dependencies;
- host verifies actual Binder Message.sendingUid isolation.
- no Android permissions, network, user files, root, Shizuku, ADB in app,
  arbitrary command, real original Node execution, or production signer.

## Limits

It is a controlled analogue, NOT original ARM64 Node or original SQLite.
No ARM64 OS linker/SELinux verification, six-library simultaneous preload,
Termux RUNPATH, actual Node --version, direct Node egress, or full DSH
host integration. Never claim a strict VM or device identity spoof.

P26_ANDROID35_NATIVE_THREE_LIBRARY_LOAD=PASS_ANDROID35
P26_ORIGINAL_ARM64_NODE_EXECUTED=NO
P26_PRODUCTION_DSH_MIGRATED=NO
P26_RELEASE=BLOCKED


## Confirmed actual Android35 x86_64 runtime evidence

GitHub Actions: https://github.com/u2584604327-a11y/dshe/actions/runs/40858208156
Actual job: SUCCESS.

The pipeline verified native NDK ELF:
- core SONAME libp26core.so.1;
- top SONAME libp26top.so.2 and DT_NEEDED core.so.1;
- sqlite-like native ELF has NO DT_SONAME;
- PIE executable DT_NEEDED top.so.2 and sqlite.so.

All four real native ELF entries were installed by PackageManager under plain
.so names and accessed only from isolatedProcess. The runtime script
required all real Binder/UID and process-exit markers:
- P26_BINDER_ISOLATED_UID=PASS
- P26_EXTRACTED_THREE_NATIVE_LIBRARIES=PASS
- P26_NEGATIVE_MISSING_TOP_SONAME=PASS
- P26_TWO_PRELOADS_AND_MISSING_SONAME_SQLITE_EXEC_UID=PASS
- P26_ORIGINAL_ARM64_NODE_EXECUTED=NO
- P26_ORIGINAL_DSH_MIGRATED=NO

The first failed CI attempt was a test workflow Java path typo,
not evidence of native incompatibility. Corrected in commit
18f983421bda88b70fb85a65b8359179b42d23df, later real CI PASS.

**Never upgrade original signed v138 Node based only on this analogue.**
It proves feasibility for three synthetic x86_64 native dependencies
and an original-analogous missing-SONAME case, not actual AArch64 Node,
six exact ICU/OpenSSL/SQLite dependencies, active Termux paths, JavaScript
runtime permission confinement, browser bridges, or real phone behavior.
