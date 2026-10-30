#!/usr/bin/env bash
set -euo pipefail
DIR=.p41tmp
ORIGINAL="$DIR/DSH-vc138-P0-OFFLINE-TEST-fixed-signature.apk"
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-/usr/local/lib/android/sdk}}"
BT="$SDK/build-tools/35.0.0"
mkdir -p "$DIR"
gh release download dsh-baseline-v135dsh-baseline-v135 \
  --repo "$GH_REPO" --pattern DSH-vc138-P0-OFFLINE-TEST-fixed-signature.apk --dir "$DIR"
test -s "$ORIGINAL"
test "$(stat -c %s "$ORIGINAL")" -eq 147341486
expected="$(PYTHONPATH=host_candidate python -c 'from p35_original_engine_spawn_contract import EXPECTED;print(EXPECTED)')"
test "${#expected}" -eq 64
printf '%s  %s\n' "$expected" "$ORIGINAL" | sha256sum -c -
apktool d -f -r "$ORIGINAL" -o "$DIR/decoded"
python host_candidate/p40_exact_trampoline.py patch "$ORIGINAL" "$DIR/decoded" --report "$DIR/p41-patch.json"
apktool b "$DIR/decoded" -o "$DIR/rebuilt-unsigned.apk"
python host_candidate/p40_exact_trampoline.py verify "$DIR/rebuilt-unsigned.apk"
"$BT/zipalign" -f -P 16 4 "$DIR/rebuilt-unsigned.apk" "$DIR/zipaligned.apk"
"$BT/zipalign" -c -P 16 4 "$DIR/zipaligned.apk"
# ephemeral signer absolutely not compatible with owner's existing fixed-signature app
secret="$(openssl rand -hex 24)"
keytool -genkeypair -alias ephemeral -keyalg RSA -keysize 3072 \
   -validity 1 -storetype PKCS12 -dname "CN=P41 EPHEMERAL ART SMOKE NOT DSH RELEASE" \
   -keystore "$DIR/disposable.p12" -storepass "$secret" -keypass "$secret" -noprompt >/dev/null 2>&1
"$BT/apksigner" sign --ks "$DIR/disposable.p12" --ks-key-alias ephemeral \
  --ks-pass "pass:$secret" --key-pass "pass:$secret" \
  --out "$DIR/ART-ONLY-EPHEMERAL-DO-NOT-INSTALL-ON-OWNER-DEVICE.apk" "$DIR/zipaligned.apk"
unset secret
"$BT/apksigner" verify --verbose "$DIR/ART-ONLY-EPHEMERAL-DO-NOT-INSTALL-ON-OWNER-DEVICE.apk" >/dev/null
"$BT/aapt" dump badging "$ORIGINAL" | grep -Fq "package: name='com.dsh.android'"
"$BT/aapt" dump badging "$DIR/ART-ONLY-EPHEMERAL-DO-NOT-INSTALL-ON-OWNER-DEVICE.apk" | grep -Fq "package: name='com.dsh.android'"
python - "$ORIGINAL" "$DIR/ART-ONLY-EPHEMERAL-DO-NOT-INSTALL-ON-OWNER-DEVICE.apk" <<'PY'
import sys,zipfile,hashlib
original,candidate=[zipfile.ZipFile(n) for n in sys.argv[1:]]
excluded={'AndroidManifest.xml','resources.arsc'}
def protected(z):
 return {x.filename:hashlib.sha256(z.read(x.filename)).hexdigest()
   for x in z.infolist() if x.filename.startswith(('assets/','lib/')) and not x.is_dir()}
base,derived=protected(original),protected(candidate)
if base!=derived: raise RuntimeError('P41_ORIGINAL_LIBRARY_OR_ASSET_DRIFT')
print('P41_ORIGINAL_ASSETS_AND_NATIVE_LIBRARIES_BYTE_PRESERVED=PASS')
PY
echo 'P41_P40_DEX_PASS_THROUGH_TRAMPOLINE_REBUILT=PASS_STATIC'
echo 'P41_EPHEMERAL_SIGNER_NOT_FIXED=YES'
echo 'P41_OWNER_APK_OVERWRITE=NO'
echo 'P41_FINAL_RELEASE=BLOCKED'
