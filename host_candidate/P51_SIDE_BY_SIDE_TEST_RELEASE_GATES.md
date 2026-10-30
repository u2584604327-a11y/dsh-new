# P51: separately installable Android ARM64 isolation probe (NOT DSH v139)

## Why P51 exists
P50 has passed exact original v138 ARM64 Node ELF + 10 original dependency library **offline** integrity checks and true Android35 x86 original-package P37/Binder regressions. But its original package name `com.dsh.android` with a one-day throwaway signing certificate can NEVER safely replace the user's already installed `com.dsh.android` unless signatures match (not established). We will not uninstall the user's original DSH, overwrite its data or touch production fixed signing material.

## Actual implementation and evidence gates
- From the exact SHA-pinned original v138 APK, build P47+P48+P50 DEX with authentic original ARM64 Node ELF + ten original dependencies verified by P49 SHA lock; all original classes/resources/ELF remain identical to P49 except the purpose-built binary Manifest and original P40 targeted main startup bridge.
- The **P51-only** Manifest is transformed from the P43-injected decoded original to a new package identity `com.dsh.p51.isolatedprobe`, with `android.app.Application` stock Application in lieu of the original DSH Application. **All old Activities, services, broadcast receivers, providers, legacy custom Application initialization, permissions and queries are stripped from the installed app manifest.** Only the exported launcher test Activity `com.dsh.android.p43.P43ProbeActivity` and a nonexported `isolatedProcess` Service remain.
- No declared permissions, no sharedUserId, no backup, no cleartext, not debuggable; explicit `extractNativeLibs=true` allows original hash-pinned ELF to be resolved by `nativeLibraryDir`. Manifest validator asserts exact two components and lone launcher intent filter on text XML before aapt and after binary AXML/signing, and enforces an **incompatible ephemeral signer** as test identity rather than reusing original private signing.
- Original owner DSH package name remains completely distinct, preventing package-manager install replacement. No call to uninstall, install or query the owner's private app data.
- On an ARM64 phone, P43 probe in this distinct package still completes P43–P46 secure same-UID Binder session, P47 original DEX bridge denial and then requests P50 **fixed synthetic Node UID/BOOT/READY stderr/exit**. Worker verifies true isolated UID, exact Node SHA and ten original ELF SHA, immutable native package directory, pinned lock, no INTERNET, hardcoded --eval fixture; P37 Process facade checks authenticated Binder sender UID, session, monotone frames, stdout/stderr, EOF/exit. No user arguments, scripts, user files, network or capabilities are passed.
- Private GitHub Actions static ARM64 job uploads ONLY the permissionless isolated probe APK as private 1-day artifact after passing all P49 ELF/P47/Manifest/signing audits; no public release or persistent original binaries. Android35 x86 emulator job separately builds a NO-ARM64-ELF x86-only P51 variant to validate **side-by-side package installation, Binder/UID, P47 deny, P48 fixed id child/P37 Process and P50 ARM64 skip**. All build artifacts and test keys are deleted after jobs.

## Critical differences and limitations
P51 is derived from the original APK code and SHA-pinned Node ELF, but because it intentionally uses a **different package ID and stock Application, without any original DSH Activities or services**, it is NOT a complete original DSH app test, original MainActivity integration test, Android system VM or proof of production EngineManager, WebView, chat, files or attachments. Its sole value is to safely obtain an ARM64 test result from the P50 fixed Node inside an original-binary-derived isolated Service, without risking the existing DSH install.

GitHub Actions x86 emulator cannot establish P50 ARM64 actual execve. After downloading artifact through private GitHub Actions, user must install only P51 on an ARM64 Android 34+ test-capable device and explicitly open **P51 Isolated Node Test**, then manually copy the status text. No hidden usage reports, diagnostic uploads, network calls, root, Shizuku, credential collection or background changes. The test Activity has no DSH production permissions and does not run production user scripts.

## Release and safety gates
- Original v138 APK immutable; original DSH application install and data untouched; original fixed signing key never requested or accessed.
- No automatic update, uninstall, privilege escalation, production port rotation, remote socket binding, invisible navigation or arbitrary file capabilities.
- If P51 installer package identity, signature difference, exact two components, zero permissions, original SHA, P47 no fallback, P49 ELF integrity, x86 regression or one-day private artifact confinement fails, stop and do not distribute.
- Do not mistake P51's fixed synthetic Node success for original DSH engine startup. P52 onwards must still implement real EngineManager→P37 handoff with production script, READY, network and complete user-facing feature parity before any v139 fixed-signature release.

P51_SAFE_SEPARATE_PACKAGE_APK=UNDER_TEST
P51_ARM64_NODE_EXECVE_IN_P51=NOT_PROVEN
P51_ORIGINAL_DSH_MAINACTIVITY=NOT_RUNNING
P51_OWNER_DSH_INSTALL_AND_DATA=UNCHANGED
P51_FIXED_SIGNED_V139=BLOCKED
