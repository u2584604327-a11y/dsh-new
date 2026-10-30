# P25 immutable v138 ARM64 Node + 10 dynamic library alias staging

## Purpose and evidence source

P24 Android35 x86_64 live emulation PASS:
https://github.com/u2584604327-a11y/dshe/actions/runs/40856304638

In P24 a real DT_NEEDED libp24version.so.3 executable failed without
LD_PRELOAD and succeeded with LD_PRELOAD of installer-extracted libp24version.so,
whose embedded DT_SONAME remained libp24version.so.3. The executed native
child getuid matched its isolatedProcess UID.

That is single-synthetic-library evidence only, not proof about original Node.

## New P25 exact-input static verifier

- Download exact original v138 signed APK only to disposable CI runner; verify
  APK, asset ZIPs, original Node binary hashes and 16KiB PT_LOAD alignments.
- Run already verified P21 recursive DT_NEEDED source intake for actual original
  AArch64 Node and 10 dependent ELF libraries, using their original bytes.
- Read ELF DT_SONAME and DT_NEEDED for all 10; require each library SONAME to
  equal the original recorded dependency name, reject missing SONAME or
  out-of-closure deps. Explicitly detect cycles among versioned dependencies.
- Create 10 collision-free Android installer-extractable lib*.so filenames.
  Six version-suffixed libraries acquire deterministic alias filenames, but
  their bytes, ELF DT_SONAME and DT_NEEDED remain completely unchanged.
- Generate dependency-before-dependent preload ordering for six aliased
  versioned libraries; do NOT claim it is sufficient to boot original Node.
- Put original unmodified Node ELF plus 10 immutable library aliases in a
  16KiB-aligned, unsigned, transient APK for package structure validation.
- Never place original APK, Node or libraries into Git repo, PR artifacts,
  public releases, production or user's phone. Delete staging files after CI.

## Non-negotiable unsupported claims

No real original AArch64 Node isolatedProcess execve or Android ARM64 linker
result; no guarantee that preloading six libraries resolves all original
Termux/RunPath issues; no full DSH native host integration, real permissions
broker or JS engine confinement. No authentic simulated iPhone or Windows UID.

## Future real ARM64 gate

Test this source-only candidate in a disposable, authorized ARM64 Android
environment (emulator with verified ABI/OS compatibility or user-owned debug
device) against exact SHA-256 original Node and libraries:
- One-to-one original binary hash identity and all ELF DT_NEEDED;
- android:isolatedProcess=true plus Binder framework caller UID/one-shot approval;
- Only --version, no arbitrary scripts, network, user files or production tools;
- No LD_PRELOAD fallback to writable executable/data paths, no root/ptrace;
- Positive native linker version output and native child UID;
- Real Node direct filesystem, loopback/outbound denial by OS;
- Only after all gates: integrate DSH Node/JS/attachments/browser/plugins and
  run full regressions with original signer preserved out of GitHub.

P25_ORIGINAL_ARM64_ALIAS_STATIC=PASS
P25_ANDROID_ARM64_MULTI_LIBRARY_EXECVE=NOT_TESTED
P25_ORIGINAL_DSH_NATIVE_HOST_MIGRATION=NO
P25_RELEASE=BLOCKED


## Final verified P25 CI and exact exception

CI: https://github.com/u2584604327-a11y/dshe/actions/runs/40857414215
GitHub job: SUCCESS. Exact pinned original v138 APK and signed ELF metadata
verified using P21, then original 11 actual ARM64 ELF files were
byte-preserved under native installer-compatible filenames. All packaged
unsigned/16KiB aligned. No original binaries uploaded as artifacts.

The first run FAILED because original libsqlite3.so has no DT_SONAME record.
A second read-only audit of ALL TEN libraries found only this exception.
The final P25 static gate accepts a missing SONAME ONLY for this exact
original libsqlite3.so, which remains package-installed under the exact
libsqlite3.so filename and is NOT part of the six versioned preload aliases.

Android Bionic may fall back to filename when DT_SONAME is absent, but that
runtime behavior for original ARM64 libsqlite3.so is NOT TESTED.
No general-purpose permission to omit or falsify SONAME has been introduced.

Verified status:
P25_EXACT_NODE_SHA_UNMODIFIED=PASS_STATIC
P25_ALL_TEN_LIBRARY_SHA_UNMODIFIED=PASS_STATIC
P25_SIX_VERSIONED_ALIAS_DT_SONAME_PRESERVED=PASS_STATIC
P25_LIBSQLITE3_NO_SONAME_EXCEPTION=IDENTIFIED_STATIC_RUNTIME_UNKNOWN
P25_16K_UNSIGNED_APK_NATIVE_PACKAGE=PASS_STATIC
P25_MULTIPLE_VERSIONED_LIBS_ANDROID_LD_PRELOAD=NOT_TESTED
P25_REAL_ARM64_NODE_ISOLATED_EXECVE=NOT_TESTED
P25_FULL_DSH_INTEGRATION=NO
P25_RELEASE=BLOCKED
