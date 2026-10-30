#!/usr/bin/env bash
set -euo pipefail
# Temporary same-package integration test: original DSH v138 + P40 trampoline
# plus P43 isolated Service and exported test-only probe Activity.
# Never distribute/install over owner's DSH.
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-/usr/local/lib/android/sdk}}"
if test "${P51_SIDE_BY_SIDE:-0}" = 1; then
  test "${P47_NO_HOST_FALLBACK:-0}" = 1 || {
    echo 'P51_BLOCKED_REQUIRED_P47_NO_HOST_FALLBACK';exit 1;
  }
  if test "${P49_NODE_STAGE:-0}" != 1; then
    test "${P51_X86_SIMULATOR_ONLY:-0}" = 1 || {
      echo 'P51_BLOCKED_EXACT_ARM64_NODE_STAGE_REQUIRED';exit 1;
    }
  fi
fi
BT="$SDK/build-tools/35.0.0"
DIR=.p43tmp
mkdir -p "$DIR/classes" "$DIR/dex"
gh release download dsh-baseline-v135dsh-baseline-v135 \
  --repo "$GH_REPO" --pattern DSH-vc138-P0-OFFLINE-TEST-fixed-signature.apk \
  --dir "$DIR"
ORIGINAL="$DIR/DSH-vc138-P0-OFFLINE-TEST-fixed-signature.apk"
expected="$(PYTHONPATH=host_candidate python -c 'from p35_original_engine_spawn_contract import EXPECTED;print(EXPECTED)')"
test "${#expected}" -eq 64
test "$(stat -c %s "$ORIGINAL")" -eq 147341486
printf '%s  %s\n' "$expected" "$ORIGINAL" | sha256sum -c -
apktool d -f -r --force-manifest "$ORIGINAL" -o "$DIR/decoded"
python host_candidate/p40_exact_trampoline.py patch "$ORIGINAL" "$DIR/decoded" \
  --report "$DIR/p40-offline.json"
if test "${P47_NO_HOST_FALLBACK:-0}" = 1; then
  python host_candidate/p47_no_fallback/p47_gate.py patch "$DIR/decoded"
fi
if test "${P72_ACCESSOR_FIXTURE_ONLY:-0}" = 1; then
  test "${P51_SIDE_BY_SIDE:-0}" = 1 || { echo 'P72_BLOCKED_NOT_SIDECAR';exit 1; }
  python host_candidate/p72_webview_access/patch_exact_webview_accessor.py patch "$DIR/decoded"
fi
python host_candidate/p43_original_service/inject_original_manifest.py inject \
  "$DIR/decoded/AndroidManifest.xml"
if test "${P51_SIDE_BY_SIDE:-0}" = 1; then
  python host_candidate/p51_side_by_side/p51_manifest.py inject \
    "$DIR/decoded/AndroidManifest.xml"
fi
# Apktool 2.7 with --force-manifest and -r preserves resources.arsc byte-for-byte,
# but its rebuilt APK contains a *plain-text* Manifest! Compile ONLY that XML
# with aapt, then replace the invalid plaintext ZIP member with binary AXML.
"$BT/aapt" package -f -M "$DIR/decoded/AndroidManifest.xml" \
  -I "$SDK/platforms/android-35/android.jar" -I "$ORIGINAL" \
  --min-sdk-version 26 --target-sdk-version 28 \
  --version-code 138 --version-name 0.4.1 \
  -F "$DIR/manifest-only.apk"
python - "$DIR/manifest-only.apk" "$DIR/manifest-binary" <<'PY'
import pathlib,sys,zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
 raw=z.read('AndroidManifest.xml')
if len(raw)<128 or raw[:4]!=b'\x03\x00\x08\x00':
 raise RuntimeError("P43_MANIFEST_ONLY_AXML_NOT_BINARY")
out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
(out/'AndroidManifest.xml').write_bytes(raw)
print('P43_ONLY_MANIFEST_COMPILED_TO_BINARY_AXML=PASS')
PY
apktool b "$DIR/decoded" -o "$DIR/rebuilt-unsigned.apk"
(cd "$DIR" && zip -q -d rebuilt-unsigned.apk AndroidManifest.xml)
(cd "$DIR/manifest-binary" && zip -q -0 ../rebuilt-unsigned.apk AndroidManifest.xml)
# apktool reassembles both original DEX files even though only classes.dex is
# patched. Restore the untouched secondary dex verbatim from SHA-pinned v138.
mkdir -p "$DIR/original-secondary"
unzip -p "$ORIGINAL" classes2.dex > "$DIR/original-secondary/classes2.dex"
test -s "$DIR/original-secondary/classes2.dex"
(cd "$DIR" && zip -q -d rebuilt-unsigned.apk classes2.dex)
(cd "$DIR/original-secondary" && zip -q -0 ../rebuilt-unsigned.apk classes2.dex)
if test "${P47_NO_HOST_FALLBACK:-0}" != 1; then
  python host_candidate/p40_exact_trampoline.py verify "$DIR/rebuilt-unsigned.apk"
fi
if test "${P51_SIDE_BY_SIDE:-0}" = 1; then
  python host_candidate/p51_side_by_side/p51_manifest.py verify \
    "$DIR/rebuilt-unsigned.apk"
else
  python host_candidate/p43_original_service/inject_original_manifest.py verify \
    "$DIR/rebuilt-unsigned.apk"
fi
# P74 only for permissionless disposable sidecar: original production P47
# source remains unchanged and rejects all starts by default.
P74_P47_GATE_SOURCE=host_candidate/p47_no_fallback/android/com/dsh/android/p47/P47LaunchGate.java
if test "${P74_FIXTURE_ENGINE_BRIDGE:-0}" = 1; then
  test "${P51_SIDE_BY_SIDE:-0}" = 1 || { echo 'P74_BLOCKED_NO_SIDECAR';exit 1; }
  P74_P47_GATE_SOURCE="$DIR/p74src/com/dsh/android/p47/P47LaunchGate.java"
  python host_candidate/p74_engine_fixture/patch_disposable_p47_gate.py     host_candidate/p47_no_fallback/android/com/dsh/android/p47/P47LaunchGate.java     "$P74_P47_GATE_SOURCE"
fi
if test "${P75_RENDEZVOUS_FIXTURE:-0}" = 1; then
  test "${P51_SIDE_BY_SIDE:-0}" = 1 && test "${P74_FIXTURE_ENGINE_BRIDGE:-0}" = 1 || {
    echo 'P75_BLOCKED_REQUIRES_P51_AND_P74';exit 1;
  }
  python host_candidate/p75_engine_rendezvous/patch_disposable_gate.py "$P74_P47_GATE_SOURCE"
fi
# A third dex guarantees no replacement of original classes.dex/classes2.dex.
javac --release 8 -cp "$SDK/platforms/android-35/android.jar" \
  -d "$DIR/classes" \
  host_candidate/p43_original_service/android/com/dsh/android/p43/P43IsolatedWorker.java \
  host_candidate/p43_original_service/android/com/dsh/android/p43/P43ProbeActivity.java \
  host_candidate/p43_original_service/android/com/dsh/android/p43/P44VirtualDeviceProfile.java \
  host_candidate/p43_original_service/android/com/dsh/android/p43/P46ResourceBundle.java \
  host_candidate/p43_original_service/android/com/dsh/android/p43/P46FixtureData.java \
  host_candidate/p43_original_service/android/com/dsh/android/p43/P46HostBroker.java \
  host_candidate/p43_original_service/android/com/dsh/android/p43/P46WorkerBundle.java \
  "$P74_P47_GATE_SOURCE" \
  host_candidate/p37_remote_process/src/com/dsh/p37/P37RemoteProcess.java \
  host_candidate/p48_process_proxy/android/com/dsh/android/p48/P48FixedIsolatedChild.java \
  host_candidate/p48_process_proxy/android/com/dsh/android/p48/P48HostProcessProbe.java \
  host_candidate/p50_original_arm64_node/android/com/dsh/android/p50/P50OriginalNodeFixedChild.java \
  host_candidate/p53_child_start/src/com/dsh/android/p53/P53StartOrder.java \
  host_candidate/p67_authenticated_handoff/src/com/dsh/android/p67/P67AuthenticatedHandoff.java \
  host_candidate/p68_android_binder/android/com/dsh/android/p68/P68AndroidBinderIntake.java \
  host_candidate/p71_browser_runtime/src/com/dsh/android/p71/P71ToolReplyOnce.java \
  host_candidate/p71_browser_runtime/android/com/dsh/android/p71/P71WebViewProfileProbe.java \
  host_candidate/p73_webview_callback/android/com/dsh/android/p73/P73BrowserToolCallbackProbe.java \
  host_candidate/p74_engine_fixture/src/com/dsh/android/p74/P74OriginalEngineFixtureHandoff.java \
  host_candidate/p75_engine_rendezvous/src/com/dsh/android/p75/P75EngineStartRendezvous.java \
  host_candidate/p76_original_engine_fd/android/com/dsh/android/p76/P76EngineArchiveFdProbe.java \
  host_candidate/p77_engine_tar_audit/src/com/dsh/android/p77/P77TarAudit.java \
  host_candidate/p78_module_slot/src/com/dsh/android/p78/P78ModuleSlot.java \
  host_candidate/p79_browser_native_mailbox/android/com/dsh/android/p79/P79NativeBrowserMailboxProbe.java \
  host_candidate/p83_hidden_browser/android/com/dsh/android/p83/P83HiddenBrowserPane.java \
  host_candidate/p85_durable_reply/android/com/dsh/android/p85/P85DurableReplyJournal.java \
  host_candidate/p85_durable_reply/android/com/dsh/android/p85/P85RestartProbe.java \
  host_candidate/p87_omnigate_sse/src/com/dsh/android/p87/P87SseDecoder.java \
  host_candidate/p87_omnigate_sse/android/com/dsh/android/p87/P87OpenAiDelta.java \
  host_candidate/p87_omnigate_sse/android/com/dsh/android/p87/P87ChatStreamView.java \
  host_candidate/p87_omnigate_sse/android/com/dsh/android/p87/P87AndroidUiProbe.java \
  host_candidate/p89_existing_stream/src/com/dsh/android/p89/P89ExistingStreamPump.java \
  host_candidate/p89_existing_stream/android/com/dsh/android/p89/P89ToolCallAssembler.java \
  host_candidate/p89_existing_stream/android/com/dsh/android/p89/P89AndroidPipeProbe.java
jar cf "$DIR/p43.jar" -C "$DIR/classes" .
"$BT/d8" --min-api 26 --lib "$SDK/platforms/android-35/android.jar" \
  --output "$DIR/dex" "$DIR/p43.jar"
test -s "$DIR/dex/classes.dex"
test "$(unzip -Z1 "$DIR/rebuilt-unsigned.apk" | grep -Ec '^classes[0-9]+\.dex$' || true)" -eq 1
mv "$DIR/dex/classes.dex" "$DIR/dex/classes3.dex"
cp "$DIR/rebuilt-unsigned.apk" "$DIR/with-p43-dex.apk"
(cd "$DIR/dex" && zip -q -0 ../with-p43-dex.apk classes3.dex)
test "$(unzip -Z1 "$DIR/with-p43-dex.apk" | grep -Ec '^classes3.dex$')" -eq 1
if test "${P49_NODE_STAGE:-0}" = 1; then
  python host_candidate/p49_original_node_stage.py prepare "$ORIGINAL" "$DIR/p49"
  python host_candidate/p49_original_node_stage.py embed "$DIR/with-p43-dex.apk" "$DIR/p49"
fi
"$BT/zipalign" -f -P 16 4 "$DIR/with-p43-dex.apk" "$DIR/aligned.apk"
"$BT/zipalign" -c -P 16 4 "$DIR/aligned.apk"
password="$(openssl rand -hex 20)"
keytool -genkeypair -alias temporary -keyalg RSA -keysize 3072 -validity 1 \
  -storetype PKCS12 -dname 'CN=P43 ORIGINAL DSH EMBEDDED WORKER EPHEMERAL ONLY' \
  -keystore "$DIR/ephemeral.p12" -storepass "$password" \
  -keypass "$password" -noprompt >/dev/null 2>&1
"$BT/apksigner" sign --ks "$DIR/ephemeral.p12" --ks-key-alias temporary \
  --ks-pass "pass:$password" --key-pass "pass:$password" \
  --out "$DIR/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk" "$DIR/aligned.apk"
unset password
"$BT/apksigner" verify "$DIR/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk"
if test "${P51_SIDE_BY_SIDE:-0}" = 1; then
  python host_candidate/p51_side_by_side/p51_manifest.py verify \
    "$DIR/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk"
fi
if test "${P49_NODE_STAGE:-0}" = 1; then
  python host_candidate/p49_original_node_stage.py verify \
    "$ORIGINAL" "$DIR/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk"
fi
if test "${P47_NO_HOST_FALLBACK:-0}" = 1; then
  python host_candidate/p47_no_fallback/p47_gate.py verify "$DIR/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk"
fi
if test "${P72_ACCESSOR_FIXTURE_ONLY:-0}" = 1; then
  python host_candidate/p72_webview_access/patch_exact_webview_accessor.py verify "$DIR/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk"
fi
python - "$ORIGINAL" "$DIR/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk" <<'PY'
import sys,zipfile,hashlib,os
from androguard.core.dex import DEX
with zipfile.ZipFile(sys.argv[1]) as orig, zipfile.ZipFile(sys.argv[2]) as derived:
 def protected(z):
  return {n:hashlib.sha256(z.read(n)).hexdigest()
          for n in z.namelist() if n.startswith(('assets/','lib/')) and not n.endswith('/')}
 if os.environ.get("P49_NODE_STAGE")=="1":
  original_protected=protected(orig)
  rebuilt_protected=protected(derived)
  if any(rebuilt_protected.get(name)!=sha for name,sha in original_protected.items()):
   raise RuntimeError("P49_ORIGINAL_ASSET_OR_NATIVE_LIB_DRIFT")
 else:
  if protected(orig)!=protected(derived):raise RuntimeError("P43_ASSET_OR_NATIVE_LIB_DRIFT")
 def old_dex(z):
  return [n for n in z.namelist() if n in ('classes.dex','classes2.dex')]
 for dex_name in old_dex(orig):
  if dex_name=='classes2.dex' and orig.read(dex_name)!=derived.read(dex_name):
   raise RuntimeError("P43_ORIGINAL_CLASSES2_DEX_DRIFT")
 classes=DEX(derived.read('classes3.dex'))
 names={c.get_name() for c in classes.get_classes()}
 for expected in ('Lcom/dsh/android/p43/P43IsolatedWorker;',
                  'Lcom/dsh/android/p43/P43ProbeActivity;',
                  'Lcom/dsh/android/p43/P44VirtualDeviceProfile;',
                  'Lcom/dsh/android/p43/P46ResourceBundle;',
                  'Lcom/dsh/android/p43/P46FixtureData;',
                  'Lcom/dsh/android/p43/P46HostBroker;',
                  'Lcom/dsh/android/p43/P46WorkerBundle;',
                  'Lcom/dsh/android/p47/P47LaunchGate;',
                  'Lcom/dsh/p37/P37RemoteProcess;',
                  'Lcom/dsh/android/p48/P48FixedIsolatedChild;',
                  'Lcom/dsh/android/p48/P48HostProcessProbe;',
                  'Lcom/dsh/android/p50/P50OriginalNodeFixedChild;',
                  'Lcom/dsh/android/p53/P53StartOrder;',
                  'Lcom/dsh/android/p67/P67AuthenticatedHandoff;',
                  'Lcom/dsh/android/p68/P68AndroidBinderIntake;',
                  'Lcom/dsh/android/p71/P71ToolReplyOnce;',
                  'Lcom/dsh/android/p71/P71WebViewProfileProbe;',
                  'Lcom/dsh/android/p73/P73BrowserToolCallbackProbe;',
                  'Lcom/dsh/android/p74/P74OriginalEngineFixtureHandoff;',
                  'Lcom/dsh/android/p75/P75EngineStartRendezvous;',
                  'Lcom/dsh/android/p76/P76EngineArchiveFdProbe;',
                  'Lcom/dsh/android/p77/P77TarAudit;',
                  'Lcom/dsh/android/p78/P78ModuleSlot;',
                  'Lcom/dsh/android/p79/P79NativeBrowserMailboxProbe;',
                  'Lcom/dsh/android/p83/P83HiddenBrowserPane;',
                  'Lcom/dsh/android/p85/P85DurableReplyJournal;',
                  'Lcom/dsh/android/p85/P85RestartProbe;',
                  'Lcom/dsh/android/p87/P87SseDecoder;',
                  'Lcom/dsh/android/p87/P87OpenAiDelta;',
                  'Lcom/dsh/android/p87/P87ChatStreamView;',
                  'Lcom/dsh/android/p87/P87AndroidUiProbe;'):
  if expected not in names:raise RuntimeError('P43_SERVICE_CLASS_MISSING')
print("P43_ORIGINAL_ASSETS_LIBRARIES_AND_SECONDARY_DEX=PASS_SHA")
print("P43_ORIGINAL_P40_TRAMPOLINE_AND_P43_CLASSES3=PASS_STATIC")
PY
"$BT/aapt" dump permissions "$ORIGINAL" \
  | grep -E '^uses-permission:' | sort > "$DIR/original-perms.txt" || true
"$BT/aapt" dump permissions "$DIR/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk" \
  | grep -E '^uses-permission:' | sort > "$DIR/candidate-perms.txt" || true
if test "${P51_SIDE_BY_SIDE:-0}" = 1; then
  test ! -s "$DIR/candidate-perms.txt" || {
    echo 'P51_BLOCKED_SIDE_BY_SIDE_HAS_PERMISSIONS';exit 1;
  }
  original_cert="$("$BT/apksigner" verify --print-certs "$ORIGINAL" \
    | sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | head -n1)"
  test -n "$original_cert"
  derived_cert="$("$BT/apksigner" verify --print-certs \
    "$DIR/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk" \
    | sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | head -n1)"
  test -n "$derived_cert" && test "$derived_cert" != "$original_cert" || {
    echo 'P51_BLOCKED_TEST_SIGNATURE_NOT_DISTINCT';exit 1;
  }
  echo 'P51_NO_PERMISSIONS_AND_SEPARATE_SIGNER=PASS'
  echo 'P51_ORIGINAL_DSH_PACKAGE_CANNOT_BE_UPDATED_BY_THIS_APK=PASS'
else
  diff -u "$DIR/original-perms.txt" "$DIR/candidate-perms.txt"
fi
if test "${P51_SIDE_BY_SIDE:-0}" = 1; then
  echo 'P51_ORIGINAL_COMPONENTS_INTENTIONALLY_DISABLED=PASS'
  echo 'P51_ORIGINAL_APPLICATION_INITIALIZATION_NOT_TESTED=YES'
else
  echo 'P43_APK_ORIGINAL_COMPONENTS_AND_APPLICATION_PRESERVED=PASS_STATIC'
fi
echo 'P43_ISOLATED_SERVICE_EMBEDDED_IN_REAL_ORIGINAL_PACKAGE=PASS_STATIC'
echo 'P43_REAL_NODE_ENGINE_ISOLATED=NO'
echo 'P43_V139_RELEASE=BLOCKED'
