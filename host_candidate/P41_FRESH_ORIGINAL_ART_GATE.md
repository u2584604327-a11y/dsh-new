# P41 original DSH v138 → P40 trampoline ART simulator validation

This Draft tests the actual original com.dsh.android package on a fresh disposable Android 35 x86_64 emulator:
- Retrieve and SHA-pin exact signed v138 source within private CI.
- Build original v138 P40 single-start pass-through trampoline (NOT isolation), validate reassembled DEX, preserve original assets/libs byte-for-byte.
- Sign only modified **throwaway emulator** package with a random 1-day certificate. Fixed release signing key NEVER used.
- Boot one original control and one modified package in same ephemeral emulator, no personal data. Package UID egress firewall applied on IPv4 and IPv6 before launching; fail if firewall cannot be established. Compare 6-second Activity survival and AndroidRuntime fatal crash markers, not full app functions.
- Original and modified APK artifacts, private keys, logcat and all source bytes destroyed in cleanup. No user-facing APK, no release, no owner-device installation.

Important gates still blocked:
- Probe is x86_64 Android 35, user device ARM64 Android 36.
- No original production Node isolated Worker invocation through P37/P38; no runtime environment, stdin, Shizuku/restart, Browser/WebView bridge or chat attachments parity.
- No certification of runtime signing, no fixed signer access, and no v139 production release.
