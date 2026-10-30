# P14–P16: Token provenance, Android isolation and device-mode audit

Date: 2026-10-29. Private source and test evidence only, no production APK.

## P14 — Token displayed as 0 for local/LAN API

Implementation: host_candidate/patch_token_usage_p14.py. Exact P6 browser-tool ZIP preimage (SHA256 aedb0a6582619c319ff85d13d6ad6f1a060c12d896fbbf1068575356190e7f37), replaced only the nested payload/mobile-ui/lib/client.js. Result SHA256 be8201f11c7a12478d0552efaf129becde6d104ef2da203c2433b3dfc397a69f.

Source and Node validation: https://github.com/u2584604327-a11y/dshe/actions/runs/40833692739 PASS.

Integrated with P13 exact APK fusion and verified emulator launch/native review: https://github.com/u2584604327-a11y/dshe/actions/runs/40833854898 PASS.

Display rules: official nonzero and partial provider values are preserved; when official usage is absent but there is a defensible local estimate, show ≈ and explicitly label 估算; when neither is available, show 未提供 instead of misleading zero. This does not force a LAN model API to send actual usage. Live provider accounting and on-device popup clicks remain UNVERIFIED.

## P15 — original APK strict isolation baseline

Exact signed v138 read-only audit: https://github.com/u2584604327-a11y/dshe/actions/runs/40834057507 PASS.

Original Android Manifest has 2 Service entries, 0 services marked isolatedProcess. The APK includes Node engine, shell/root helpers and browser device preset code. A file named boosandbox.bin does not establish a real OS VM boundary. Production Node isolated UID, generic Node filesystem/network/shell confinement, and per-profile WebView storage isolation remain NOT VERIFIED.

Independent real Android isolated-UID probe source (not DSH product engine): host_candidate/p15_isolated_probe/. It has a separate test package with a service marked isolatedProcess=true, no Android permissions, and an IPC test that verifies the service gets a different UID and cannot read an app-created private canary. The real isolated-process prototype PASSED Android 35 simulator execution: https://github.com/u2584604327-a11y/dshe/actions/runs/40834677353 (SUCCESS). The test verified different UID, inability to read an app-private synthetic canary, and isolatedProcess metadata. This is a standalone test APK; it has NOT migrated any production DSH Node/browser service.

Until Node and browser automation actually migrate behind a proven restricted UID and a trusted native capability broker, DSH cannot be described as a strict virtual machine. An ordinary extra process, WebView storage suffix or JS device profile is insufficient.

Required broker boundaries: explicit user authorization; per-capability and destination allowlist; FD-only, descriptor-pinned, short-lived file grants; immutable content revalidation; no raw credentials to model runtime; camera/mic/geolocation and ADB/Shizuku/Shell default denied; audit, revoke and one-shot consume. Ordinary user-selected image and file sends must remain functional.

## P16 — simulated device profile truth

Source test: https://github.com/u2584604327-a11y/dshe/actions/runs/40834952248 PASS. Profiles include fractional CSS viewport dimensions, which are valid; an earlier too-strict integer-only test was corrected.

A mode can declare UA/viewport/DPR/touch, locale/timezone and selected browser-visible values, while the underlying engine remains Android WebView. The modes do not change actual iPhone/Windows OS identity, hardware, GPU, TLS, IP, Android attestation or UID. Remote sites may observe discrepancies. The UI must label these as simulated browser modes; no guarantee that external websites will regard the host as the named physical device.

Validation before any production claim: use a user-controlled permissioned test page to measure actual network UA, JS navigator UAData, viewport, media settings, cookies across profiles, and storage isolation; report fields individually as applied, unknown, unsupported or inconsistent. Do not bypass site identity/anti-fraud systems.

## Latest release gates

P14_SOURCE_TEST=PASS
P14_ANDROID_FUSION_ART_STARTUP=PASS
P14_REAL_LAN_TOKEN_USAGE=NOT_VERIFIED
P15_ORIGINAL_ISOLATED_SERVICES=0
P15_PRODUCTION_NODE_UID_ISOLATION=NOT_VERIFIED
P15_STANDALONE_ISOLATED_PROBE=PASS_ANDROID35_NOT_DSH_ENGINE
P16_DEVICE_PROFILE_SOURCE_VALIDITY=PASS
P16_SITE_VISIBLE_DEVICE_CONSISTENCY=NOT_VERIFIED
REAL_IOS_WINDOWS_HARDWARE_IDENTITY=NOT_ACHIEVABLE_FROM_WEBVIEW
P13_ORIGINAL_NATIVE_BUTTON_AUTOHOOK=PASS_ANDROID35_LAB
APPROVED_ONE_SHOT_SEND=NOT_CONNECTED
FIXED_CERT_V139_APK=NOT_BUILT
USER_PHONE=UNCHANGED
RELEASE=BLOCKED
