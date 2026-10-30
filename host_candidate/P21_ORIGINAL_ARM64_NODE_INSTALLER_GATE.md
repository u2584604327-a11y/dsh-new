# P21: real original v138 ARM64 Node runtime packaging — source candidate

Date: 2026-10-29.

## Verified previous stages
- P18 one-shot Binder and explicit native gesture: PASS on standalone Android35.
- P19 Node + bootstrap static archive dependency file presence: PASS.
- P20 isolated UID: host INTERNET positive-control + isolated child loopback denied by OS; private synthetic canary denied: PASS standalone Android35.

## New P21 implementation
- Reads ONLY exact signed v138 APK SHA256 3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5.
- Opens exact hash-pinned assets/node-runtime.bin and bootstrap-aarch64.zip.
- Reads exact AArch64 Node ELF and recursive DT_NEEDED graph.
- Produces candidate lib/arm64-v8a/libdshnode_p21_exec.so containing original executable without ELF mutation, plus all ten actual AArch64 required shared libraries, preserving original NEEDED names.
- Generates a standalone isolatedProcess Android source probe, bound via Messenger, which would execute only original SHA-verified Node with --version.
- API35 Android app has no INTERNET/storage permissions, no plugins, no user data, no arbitrary args or shell endpoint.
- Ordinary CI compiles and creates unsigned disposable ARM64 package, then deletes it. Does not install or sign it.

## Current concrete blocker

Android official NDK docs: APK native library extraction matches lib/<abi>/lib<name>.so, not arbitrary version-suffixed sonames. Android bionic documentation confirms only lib*.so extracted for non-debuggable apps until API35.

Six of the ten actual linked libraries have versioned suffixes:
libcrypto.so.3, libssl.so.3, libz.so.1,
libicui18n.so.78, libicuuc.so.78, libicudata.so.78.

Therefore an APK containing all eleven ELF entries is **not sufficient** to demonstrate that Android35 will extract the versioned libraries, or that original immutable Node will resolve them. A failed --version startup must not be repaired by weakening SELinux, copying executable native libs to a writable app-private directory, rewriting the original Node binary, granting Shizuku/ADB/root, or assuming the host app Termux data paths.

Official references:
- https://developer.android.com/ndk/guides/abis
- https://android.googlesource.com/platform/bionic/+/HEAD/android-changes-for-ndk-developers.md
- https://developer.android.com/about/versions/10/behavior-changes-10

## P21 second-stage direct-from-APK immutable linker candidate

A second source-only candidate now addresses the *staging* limitation without
changing original Node bytes or writing executables to user-writable directories:

- Preserve extractNativeLibs=true for original Node executable renamed to the
  installer-extractable libdshnode_p21_exec.so (SHA256 unchanged).
- Place ALL ten direct/transitive native libraries in the same APK. Six keep
  their exact original DT_NEEDED versioned sonames.
- Store ALL eleven ELF entries uncompressed, and align their data offsets to
  16384-byte boundaries, including the six .so.N entries. Verify all original
  ELF PT_LOAD segments are themselves 16 KiB aligned (0x4000).
- A candidate isolated worker sets LD_LIBRARY_PATH to the package-managed
  nativeLibraryDir plus its installed base.apk!/lib/arm64-v8a archive search
  path, then attempts only SHA-pinned original bin/node --version.
- This relies on Android Bionic support for directly reading an aligned,
  uncompressed native ELF from a ZIP. Whether the **execve child linker**
  honors that search path under isolatedProcess, the app linker namespace and
  SELinux remains **NOT TESTED**.
- Both direct and fallback paths must refuse arbitrary writable-home
  executable copies, altered original Node bytes and relaxed permissions.

Static source, Java compile, signed-original hash and uncompressed 16 KiB ZIP
alignment all PASS in latest CI:
https://github.com/u2584604327-a11y/dshe/actions/runs/40847949453

DO NOT infer actual Node execution from those static PASS results.

## Required next safe gate

1. Verify Android package/extraction semantics for API35 and API36 with real arm64 system environments. Use a non-production ARM64 hardware/emulator owned by the user; hosted x86_64 emulator cannot run this original ARM64 Node directly.
2. Choose an installer-immutable versioned-soname mapping mechanism that preserves both exact original binary integrity and OS isolated UID confinement. Validate real native linker behavior and SELinux. If not possible, stop, and propose separately audited Android-native embedded Node architecture with its own binary identity.
3. Run the bound isolated worker against exact ELF, and verify Binder sendingUid, runtime SHA256, successful --version, app-private file denial and outbound/loopback denial **from the actual Node process**, not merely from Java.
4. Only then integrate the real DSH Node call sites; test ordinary images/files, streaming, browser, log privacy, tools and interaction before signed release.

## Honest status

P21_REAL_NODE_NATIVE_LIBRARY_CANDIDATE=STATIC_CI_PASS
P21_ALL_11_ZIP_NATIVE_ELFS_4096_ALIGNED=STATIC_CI_PASS
P21_DIRECT_ZIP_LINKER_RESOLUTION=NOT_TESTED
P21_API35_VERSIONED_LIB_INSTALLER_EXTRACTION=BLOCKED_6
P21_REAL_ARM64_NODE_ISOLATED_UID_EXECUTE=NOT_RUN
P21_REAL_NODE_EGRESS_DENIAL=NOT_TESTED
P21_DSH_PRODUCT_NODE_MIGRATION=NO
P21_REAL_DEVICE_APK_UPGRADE=NO
P21_RELEASE=BLOCKED

## 16 KiB check evidence

Original signed Node and all ten of its actual transitive ELF dependencies
have PT_LOAD alignment 0x4000, verified by readelf -l -W. P21 source gate
rejects any package that does not preserve this. All 11 uncompressed native
ELF ZIP data offsets are aligned to 16 KiB even for versioned .so.N entries;
Android SDK zipalign -c -P 16 4 passes. This addresses package alignment
for both 4 KiB and 16 KiB page-size devices, **not** runtime linker or
isolatedProcess/SELinux proof.

Android official guidance:
https://developer.android.com/guide/practices/page-sizes
https://developer.android.com/tools/zipalign
