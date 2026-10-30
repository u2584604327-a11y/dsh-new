# DSH P18 — Legacy AI privileged shell / root failclose

Date: 2026-10-29. Applies only to **experimental SHA-pinned v138→v139 lab fusion**, not to the user's installed v138.

## Why this matters

Exact original signed v138 APK contains:
- `assets/shell-tool.zip`, SHA256 `f34284d3518c1b5c5cd800b44db50b448bd844492a13e15d380b14b6448f2611`, registering a model-visible `shell` tool running commands via the device's adbd as Android shell UID 2000 if available. Its own comments warn that this bypasses the app's write sandbox.
- `assets/root-tool.zip`, SHA256 `d67301442216463dcf340d5c549b203d9c5ec3a7ebb07e8d25c54f1af24b95c1`, registering model-visible `root` invoking an actual `su` runtime, UID 0 when available.
- `assets/dsh-android-shell.mjs` and `assets/dsh-android-root.mjs` remain in the original APK. Their presence and ability to be reached through **other** generic Node APIs cannot be ruled out by changing only plugin registration.

These are extra escape routes beyond the P11 safe summary-only `logs` plugin. A separate-UID sandbox is incompatible with a privileged tool that openly bypasses the intended broker.

## P18 code and effect

- `host_candidate/patch_privileged_tools_p18.py` patches only nested `lib/index.js` in the two exact signed-v138 plugin ZIP assets. It verifies original APK asset SHA, archive CRC/entry list, and byte-identical untouched package metadata.
- Both `export function apply(ctx)` methods return before registering `shell`/`root`, even if legacy runner environment variables are present.
- An unreachable fallback `execute()` path also returns a fixed denial without executing the old privileged runner.
- Result shell ZIP SHA256: `51dac0e5c82a38e03318535b6d0d1ac9fe52d2b020ba508efc82af0947df1187`.
- Result root ZIP SHA256: `8f54d9871357a79df0acb997169becc03282eb64f3e191ff0cdba4bf7492b7f1`.
- **Tradeoff:** model-facing `shell` UID2000 and `root` UID0 tools are deliberately unavailable in P18 candidate until an explicitly approved trusted broker is integrated. This is an intentional behavior reduction for a strictly isolated mode, NOT feature parity.
- No original `bash`, ordinary photo/file sending, Node core engine, installed phone APK, original signature, Node credentials or old logs were changed by this P18 patch.
- **Critical caveat:** generic app-UID `bash` and Node filesystem/network mechanisms remain operational. P18 alone cannot claim strict isolation, no arbitrary shell, or a full virtual machine.

## Evidence

- P18 exact nested-resource patch and real Node plugin registration test PASS: https://github.com/u2584604327-a11y/dshe/actions/runs/40836893499
- P13/P14/P5 with P18 overlay Android 35 fusion/ART/UI regression: https://github.com/u2584604327-a11y/dshe/actions/runs/40837022330 — **SUCCESS**. Exact P18 resources present in lab APK, Android install and offline ART compile, MainActivity startup, P13 cold-process original LogViewer automatic hook and P5/P12 tests pass. This does NOT prove the actual engine's runtime tool registry state or ordinary attachment parity, which require separate in-app acceptance.
- P17 authentic Android Binder sendingUid and one-shot consent/burn/replay/deny proof PASS (standalone): https://github.com/u2584604327-a11y/dshe/actions/runs/40836348358

## Next security gate

Map all remaining original executable escape paths, including built-in model `bash`, Node child_process, shell JS runners, plugin installers, localhost bridge, root helper and WebView bridge; migrate the actual untrusted Node runtime into a distinct isolated UID. The trusted host must authenticate Android Binder caller UID and enforce P17-style narrow grants. Until that migration and negative-path tests pass, do not release.

```text
P18_PRIVILEGED_SHELL_UID2000_TOOL_REGISTERED=NO_SOURCE_TEST
P18_PRIVILEGED_ROOT_UID0_TOOL_REGISTERED=NO_SOURCE_TEST
P18_COMBINED_ANDROID_ART_AND_NATIVE_UI=PASS_ANDROID35_LAB
P18_BUILTIN_BASH_TOOL=ORIGINAL_UNCHANGED
P18_GENERIC_NODE_FS_NETWORK_SHELL=NOT_ISOLATED
P18_USER_APP_FUNCTIONAL_PARITY=NOT_VERIFIED
P17_BROKER_ON_ANDROID35=PASS_STANDALONE
FULL_V139_STRICT_ISOLATION=NO
REAL_PHONE=UNCHANGED
PRODUCTION_RELEASE=BLOCKED
```
