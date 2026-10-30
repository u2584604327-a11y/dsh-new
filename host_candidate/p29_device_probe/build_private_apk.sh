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
 --out-native-dir out/p29/pkg/lib/arm64-v8a --report out/p25.json
python3 host_candidate/p28_device_probe/emit_runtime_lock.py \
 --p25-report out/p25.json \
 --native-dir out/p29/pkg/lib/arm64-v8a \
 --out out/p29/assets/p28-runtime-lock.json
test "$(find out/p29/pkg/lib/arm64-v8a -maxdepth 1 -name '*.so' -type f | wc -l)" -eq 11
manager="$(command -v sdkmanager || true)"
if test -z "$manager";then
 manager="$(find "$SDK/cmdline-tools" -name sdkmanager -type f -perm /111 2>/dev/null | head -n1 || true)"
fi
test -n "$manager"
"$manager" --sdk_root="$SDK" 'platforms;android-35' 'build-tools;35.0.0'
mkdir -p out/p29/classes out/p29/dex
javac --release 8 -cp "$SDK/platforms/android-35/android.jar" \
 -d out/p29/classes \
 host_candidate/p29_device_probe/android/com/dsh/p29/nodeprobe/P29Activity.java \
 host_candidate/p29_device_probe/android/com/dsh/p29/nodeprobe/P29Worker.java
jar cf out/p29/probe.jar -C out/p29/classes .
"$BT/d8" --min-api 34 --lib "$SDK/platforms/android-35/android.jar" \
 --output out/p29/dex out/p29/probe.jar
"$BT/aapt" package -f -M host_candidate/p29_device_probe/android/AndroidManifest.xml \
 -I "$SDK/platforms/android-35/android.jar" -A out/p29/assets \
 -F out/p29-unsigned.apk
(cd out/p29/dex && zip -q -j ../../p29-unsigned.apk classes.dex)
(cd out/p29/pkg && zip -q -0 -r ../../p29-unsigned.apk lib)
"$BT/zipalign" -f -P 16 4 out/p29-unsigned.apk out/p29-aligned.apk
"$BT/zipalign" -c -P 16 4 out/p29-aligned.apk
python3 - <<'PY'
import hashlib,json,zipfile,struct
with zipfile.ZipFile("out/p29-aligned.apk") as z:
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
  with open("out/p29-aligned.apk","rb") as raw:
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
print("P29_11_EXACT_ARM64_ELF_ORIGINAL_BYTES_AND_APK_16K=PASS_STATIC")
PY
"$BT/aapt" dump badging out/p29-aligned.apk > out/p29/badging.txt
grep -Fq "package: name='com.dsh.p29.nodeprobe'" out/p29/badging.txt
# Some aapt builds omit the optional native-code badging line for
# ZIP-added ELF. The stronger gate above checks the full actual ZIP entry set,
# ARM64 source SHA and 16KiB-aligned STORED payload directly.
if grep -Fq "native-code: 'arm64-v8a'" out/p29/badging.txt;then
 echo 'P29_AAPT_NATIVE_CODE_ARM64_SUMMARY=OBSERVED'
else
 echo 'P29_AAPT_NATIVE_CODE_SUMMARY=OMITTED_ZIP_NATIVE_IDENTITY_CHECKED'
fi
"$BT/aapt" dump permissions out/p29-aligned.apk > out/p29/perms.txt
if grep -Fq 'uses-permission:' out/p29/perms.txt;then
 echo "::error::P29 requests prohibited Android permissions";exit 1
fi
test "$(grep -Ec 'android:isolatedProcess="true"' \
 host_candidate/p29_device_probe/android/AndroidManifest.xml)" -eq 1
PASSWORD="$(openssl rand -hex 20)"
keytool -genkeypair -alias p29only -keyalg RSA -keysize 3072 \
 -validity 30 -storetype PKCS12 \
 -dname 'CN=P29 THROWAWAY OFFLINE TEST NOT ORIGINAL DSH' \
 -keystore out/p29-test-key.p12 -storepass "$PASSWORD" \
 -keypass "$PASSWORD" -noprompt >/dev/null 2>&1
"$BT/apksigner" sign --ks out/p29-test-key.p12 --ks-key-alias p29only \
 --ks-pass "pass:$PASSWORD" --key-pass "pass:$PASSWORD" \
 --out delivery/P29-Private-ARM64-Node-Boundary-Probe.apk out/p29-aligned.apk
"$BT/apksigner" verify delivery/P29-Private-ARM64-Node-Boundary-Probe.apk
"$BT/zipalign" -c -P 16 4 delivery/P29-Private-ARM64-Node-Boundary-Probe.apk
"$BT/aapt" dump permissions delivery/P29-Private-ARM64-Node-Boundary-Probe.apk > out/p29/signed-perms.txt
if grep -Fq 'uses-permission:' out/p29/signed-perms.txt;then
 echo "::error::Signed test APK requests prohibited permissions";exit 1
fi
(cd delivery && sha256sum P29-Private-ARM64-Node-Boundary-Probe.apk > SHA256SUMS.txt)
cat > delivery/README-P29-PRIVATE.txt <<'TEXT'
P29: Owner-authorized private ARM64 Android OS boundary probe.
Independent package com.dsh.p29.nodeprobe, NOT DSH v139 and NOT P28.
Temporary signer: uninstall previous P29 before another ephemeral signed rebuild.
Requires Android 14+ API34, arm64-v8a. No manifest permissions.
DO NOT PUBLISH this APK: contains original v138 Node ELF + ten libraries.
Open the P29 app and explicitly tap 开始安全隔离实测.
Host creates exactly one 32-byte canary in THIS TEST APP's private files.
Node runs only embedded fixed code and reports getuid, read denial, and
TCP connection attempts to 127.0.0.1:9 and 198.51.100.1:443.
No user files, chat data, or messages are sent; no diagnostic upload.
TIMEOUT / ECONNREFUSED / missing canary are NOT counted as denial PASS.
Tap 复制测试报告 and paste the report privately into your ChatGPT conversation.
Even a full PASS is limited to this Node process, test operations and Android
configuration. It is not general DSH isolation, VM identity or v139 release.
The P28 test app and original installed DSH are never overwritten.
TEXT
echo 'P29_ORIGINAL_11_ARM64_ELF_VERIFIED=PASS_STATIC' >> "$GITHUB_STEP_SUMMARY"
echo 'P29_TEST_APP_NO_PERMISSIONS_EPHEMERAL_SIGNER=PASS_STATIC' >> "$GITHUB_STEP_SUMMARY"
echo 'P29_REAL_ARM64_ANDROID_NODE_BOOT=NOT_TESTED' >> "$GITHUB_STEP_SUMMARY"
echo 'P29_RELEASE=BLOCKED' >> "$GITHUB_STEP_SUMMARY"
