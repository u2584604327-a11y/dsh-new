#!/usr/bin/env bash
set -euo pipefail
SDK="$ANDROID_HOME"
BT="$SDK/build-tools/35.0.0"
mkdir -p input out delivery
gh release download dsh-baseline-v135dsh-baseline-v135 \
 --repo "$GH_REPO" --pattern DSH-vc138-P0-OFFLINE-TEST-fixed-signature.apk --dir input
printf '%s  %s\n' 3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5 \
 input/DSH-vc138-P0-OFFLINE-TEST-fixed-signature.apk | sha256sum -c -
python3 host_candidate/p21_real_arm64_loader_pack.py \
 input/DSH-vc138-P0-OFFLINE-TEST-fixed-signature.apk \
 --out-native-dir out/p21/lib/arm64-v8a --report out/p21.json
python3 host_candidate/p25_original_node_alias_stager.py \
 --p21-native-dir out/p21/lib/arm64-v8a \
 --out-native-dir out/p28/pkg/lib/arm64-v8a --report out/p25.json
python3 host_candidate/p28_device_probe/emit_runtime_lock.py \
 --p25-report out/p25.json \
 --native-dir out/p28/pkg/lib/arm64-v8a \
 --out out/p28/assets/p28-runtime-lock.json
test "$(find out/p28/pkg/lib/arm64-v8a -maxdepth 1 -name '*.so' -type f | wc -l)" -eq 11
manager="$(command -v sdkmanager || true)"
if test -z "$manager";then
 manager="$(find "$SDK/cmdline-tools" -name sdkmanager -type f -perm /111 2>/dev/null | head -n1 || true)"
fi
test -n "$manager"
"$manager" --sdk_root="$SDK" 'platforms;android-35' 'build-tools;35.0.0'
mkdir -p out/p28/classes out/p28/dex
javac --release 8 -cp "$SDK/platforms/android-35/android.jar" \
 -d out/p28/classes \
 host_candidate/p28_device_probe/android/com/dsh/p28/nodeprobe/P28Activity.java \
 host_candidate/p28_device_probe/android/com/dsh/p28/nodeprobe/P28Worker.java
jar cf out/p28/probe.jar -C out/p28/classes .
"$BT/d8" --min-api 34 --lib "$SDK/platforms/android-35/android.jar" \
 --output out/p28/dex out/p28/probe.jar
"$BT/aapt" package -f -M host_candidate/p28_device_probe/android/AndroidManifest.xml \
 -I "$SDK/platforms/android-35/android.jar" -A out/p28/assets \
 -F out/p28-unsigned.apk
(cd out/p28/dex && zip -q -j ../../p28-unsigned.apk classes.dex)
(cd out/p28/pkg && zip -q -0 -r ../../p28-unsigned.apk lib)
"$BT/zipalign" -f -P 16 4 out/p28-unsigned.apk out/p28-aligned.apk
"$BT/zipalign" -c -P 16 4 out/p28-aligned.apk
python3 - <<'PY'
import hashlib,json,zipfile,struct
with zipfile.ZipFile("out/p28-aligned.apk") as z:
 names=z.namelist()
 if len(set(names))!=len(names):raise ValueError("DUPLICATE_ZIP_ENTRY")
 lock=json.loads(z.read("assets/p28-runtime-lock.json"))
 required={"lib/arm64-v8a/libdshnode_p21_exec.so":lock["node_sha256"]}
 required.update({"lib/arm64-v8a/"+e["alias"]:e["sha256"] for e in lock["libs"]})
 installed={n for n in names if n.startswith("lib/") and not n.endswith("/")}
 if len(required)!=11 or installed!=set(required) or len(lock["preload"])!=6:
  raise ValueError("ORIGINAL_LIBRARY_SET_OR_PRELOAD_MAP_CHANGED")
 for name,sha in required.items():
  item=z.getinfo(name)
  with open("out/p28-aligned.apk","rb") as raw:
   raw.seek(item.header_offset)
   local=raw.read(30)
   if len(local)!=30 or local[:4]!=bytes([0x50,0x4b,0x03,0x04]):
    raise ValueError("BAD_LOCAL_ZIP_HEADER")
   header=struct.unpack("<IHHHHHIIIHH",local)
   offset=item.header_offset+30+header[-2]+header[-1]
  if item.compress_type!=zipfile.ZIP_STORED or offset%16384:
   raise ValueError("ELF_ZIP_NOT_16K_STORED")
  if hashlib.sha256(z.read(name)).hexdigest()!=sha:
   raise ValueError("ORIGINAL_ELF_APK_HASH_MISMATCH")
print("P28_11_EXACT_ARM64_ELF_ORIGINAL_BYTES_AND_APK_16K=PASS_STATIC")
PY
"$BT/aapt" dump badging out/p28-aligned.apk > out/p28/badging.txt
grep -Fq "package: name='com.dsh.p28.nodeprobe'" out/p28/badging.txt
# Some aapt builds omit the optional native-code badging line for
# ZIP-added ELF. The stronger gate above checks the full actual ZIP entry set,
# ARM64 source SHA and 16KiB-aligned STORED payload directly.
if grep -Fq "native-code: 'arm64-v8a'" out/p28/badging.txt;then
 echo 'P28_AAPT_NATIVE_CODE_ARM64_SUMMARY=OBSERVED'
else
 echo 'P28_AAPT_NATIVE_CODE_SUMMARY=OMITTED_ZIP_NATIVE_IDENTITY_CHECKED'
fi
"$BT/aapt" dump permissions out/p28-aligned.apk > out/p28/perms.txt
if grep -Fq 'uses-permission:' out/p28/perms.txt;then
 echo "::error::P28 requests prohibited Android permissions";exit 1
fi
test "$(grep -Ec 'android:isolatedProcess="true"' \
 host_candidate/p28_device_probe/android/AndroidManifest.xml)" -eq 1
PASSWORD="$(openssl rand -hex 20)"
keytool -genkeypair -alias p28only -keyalg RSA -keysize 3072 \
 -validity 30 -storetype PKCS12 \
 -dname 'CN=P28 THROWAWAY OFFLINE TEST NOT ORIGINAL DSH' \
 -keystore out/p28-test-key.p12 -storepass "$PASSWORD" \
 -keypass "$PASSWORD" -noprompt >/dev/null 2>&1
"$BT/apksigner" sign --ks out/p28-test-key.p12 --ks-key-alias p28only \
 --ks-pass "pass:$PASSWORD" --key-pass "pass:$PASSWORD" \
 --out delivery/P28-Private-ARM64-Node-Isolation-Probe.apk out/p28-aligned.apk
"$BT/apksigner" verify delivery/P28-Private-ARM64-Node-Isolation-Probe.apk
"$BT/zipalign" -c -P 16 4 delivery/P28-Private-ARM64-Node-Isolation-Probe.apk
"$BT/aapt" dump permissions delivery/P28-Private-ARM64-Node-Isolation-Probe.apk > out/p28/signed-perms.txt
if grep -Fq 'uses-permission:' out/p28/signed-perms.txt;then
 echo "::error::Signed test APK requests prohibited permissions";exit 1
fi
(cd delivery && sha256sum P28-Private-ARM64-Node-Isolation-Probe.apk > SHA256SUMS.txt)
cat > delivery/README-P28-PRIVATE.txt <<'TEXT'
Private Android ARM64 offline test app, NOT DSH v139 or com.dsh.android update.
Separate package: com.dsh.p28.nodeprobe; temporary independent signer.
No Android permissions, no automatic uploads or user-file requests.
Contains original v138 Node ELF + 10 libraries: DO NOT share publicly.
Android API 34+ arm64-v8a hardware only; install APK within artifact ZIP.
Tap 开始离线检测 to run ONLY original Node --version in isolatedProcess.
Tap 复制本地检测结果 to copy the report manually.
PASS proves only version boot and host-to-isolated UID Binder verification.
Original Node child UID was not separately measured; network/FS isolation
and DSH app integration are NOT TESTED. Original v138 stays installed.
Future test APK may require uninstall because signer is ephemeral.
TEXT
echo 'P28_ORIGINAL_11_ARM64_ELF_VERIFIED=PASS_STATIC' >> "$GITHUB_STEP_SUMMARY"
echo 'P28_TEST_APP_NO_PERMISSIONS_EPHEMERAL_SIGNER=PASS_STATIC' >> "$GITHUB_STEP_SUMMARY"
echo 'P28_REAL_ARM64_ANDROID_NODE_BOOT=NOT_TESTED' >> "$GITHUB_STEP_SUMMARY"
echo 'P28_RELEASE=BLOCKED' >> "$GITHUB_STEP_SUMMARY"
