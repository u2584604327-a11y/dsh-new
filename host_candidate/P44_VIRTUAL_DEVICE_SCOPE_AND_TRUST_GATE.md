# P44: Original DSH APK simulated-device profile over verified isolated Binder

## Actual scope
P43 proved real Android (API 35 emulator) original DSH package can start an isolatedProcess Service with a real isolated UID and authenticated host Binder. P44 adds a small immutable, versioned and bounded **virtual device profile control plane** into that SAME real original DSH experimental APK, still built from exact pinned signed v138.

It is a **simulated view for opted-in DSH-controlled code**; it cannot alter Android Build.*, protected system settings, identifiers, attestation, hardware sensors, IP address, other apps, or make an entire Android OS. No effects beyond the small test handshake yet.

### Verifiable additions
- Synthetic predeclared profile sandbox-a, 390x844, en-US, UTC, network deny, storage broker-only. This is a test fixture, not a persisted user-selected virtual device.
- Strict protocol `p44-1`, canonical bounded integers, locale, timezone and profile identifier; invalid injections, replay-like malformed strings and elevated access selectors rejected.
- Trusted original DSH ProbeActivity generates 256-bit session, submits synthetic profile over same authenticated original-app-to-isolated Android Messenger channel, and validates returned SHA256 digest plus explicit worker claims that this is NOT a real VM or hardware identity change.
- Original P43 service still enforces framework-supplied `Message.sendingUid`, one-shot session, isolated worker UID, and nonexported Service.
- P44 pure Java JVM negative cases and fresh Android35 original DSH experimental package on-emulator Binder acceptance.
- P43 strict original assets/native libs/classes2 dex SHA, exact manifest permissions and SDK settings, original MainActivity boot parity remain enforced.

### NOT accomplished / DO NOT OVERCLAIM
No WebView navigator/UA interception, custom Chrome profile, actual location replacement, virtual sensor provider, hypervisor/independent guest kernel, per-profile filesystem data broker, production Node isolated EngineManager, chat/browser/file functions, runtime user UI, or owner-device signing. A profile descriptor is NOT a capability. No silent fallback to original unsandboxed Node is allowed in any future production integration.

P44 is deliberately transient in private GitHub CI with disposable signing key and exported test-only Activity; no APK release, production fixed signature, user install, test data upload or merge. A real Android guest VM would require AVF/pKVM or a separately packaged system-level runtime and supported permissions, and cannot be claimed by a normal APK.

P44_ACTUAL_ORIGINAL_DSH_VM=NO
P44_ORIGINAL_DSH_SIMULATED_PROFILE_OVER_BINDER=UNDER_TEST
P44_PRODUCTION_V139=BLOCKED
