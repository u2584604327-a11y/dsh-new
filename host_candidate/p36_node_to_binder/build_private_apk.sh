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
 --out-native-dir out/p36/pkg/lib/arm64-v8a --report out/p25.json
python3 host_candidate/p28_device_probe/emit_runtime_lock.py \
 --p25-report out/p25.json \
 --native-dir out/p36/pkg/lib/arm64-v8a \
 --out out/p36/assets/p28-runtime-lock.json
test "$(find out/p36/pkg/lib/arm64-v8a -maxdepth 1 -name '*.so' -type f | wc -l)" -eq 11
manager="$(command -v sdkmanager || true)"
if test -z "$manager";then
 manager="$(find "$SDK/cmdline-tools" -name sdkmanager -type f -perm /111 2>/dev/null | head -n1 || true)"
fi
test -n "$manager"
"$manager" --sdk_root="$SDK" 'platforms;android-35' 'build-tools;35.0.0'
mkdir -p out/p36/classes out/p36/dex
javac --release 8 -cp "$SDK/platforms/android-35/android.jar" \
 -d out/p36/classes \
 host_candidate/p17_capability/src/com/dsh/p17/P17CapabilityGate.java \
 host_candidate/p32_node_ipc/src/com/dsh/p32/P32NodeIpcBroker.java \
 host_candidate/p32_node_ipc/android/com/dsh/p32/P32AndroidBinderPort.java \
 host_candidate/p36_node_to_binder/android/com/dsh/p36/nodebridge/P36Activity.java \
 host_candidate/p36_node_to_binder/android/com/dsh/p36/nodebridge/P36IsolatedNodeWorker.java
jar cf out/p36/probe.jar -C out/p36/classes .
"$BT/d8" --min-api 34 --lib "$SDK/platforms/android-35/android.jar" \
 --output out/p36/dex out/p36/probe.jar
"$BT/aapt" package -f -M host_candidate/p36_node_to_binder/android/AndroidManifest.xml \
 -I "$SDK/platforms/android-35/android.jar" -A out/p36/assets \
 -F out/p36-unsigned.apk
(cd out/p36/dex && zip -q -j ../../p36-unsigned.apk classes.dex)
(cd out/p36/pkg && zip -q -0 -r ../../p36-unsigned.apk lib)
"$BT/zipalign" -f -P 16 4 out/p36-unsigned.apk out/p36-aligned.apk
"$BT/zipalign" -c -P 16 4 out/p36-aligned.apk
python3 - <<'PY'
import hashlib,json,zipfile,struct
with zipfile.ZipFile("out/p36-aligned.apk") as z:
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
  with open("out/p36-aligned.apk","rb") as raw:
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
print("P36_11_EXACT_ARM64_ELF_ORIGINAL_BYTES_AND_APK_16K=PASS_STATIC")
PY
"$BT/aapt" dump badging out/p36-aligned.apk > out/p36/badging.txt
grep -Fq "package: name='com.dsh.p36.nodebridge'" out/p36/badging.txt
# Some aapt builds omit the optional native-code badging line for
# ZIP-added ELF. The stronger gate above checks the full actual ZIP entry set,
# ARM64 source SHA and 16KiB-aligned STORED payload directly.
if grep -Fq "native-code: 'arm64-v8a'" out/p36/badging.txt;then
 echo 'P36_AAPT_NATIVE_CODE_ARM64_SUMMARY=OBSERVED'
else
 echo 'P36_AAPT_NATIVE_CODE_SUMMARY=OMITTED_ZIP_NATIVE_IDENTITY_CHECKED'
fi
"$BT/aapt" dump permissions out/p36-aligned.apk > out/p36/perms.txt
if grep -Fq 'uses-permission:' out/p36/perms.txt;then
 echo "::error::P36 requests prohibited Android permissions";exit 1
fi
test "$(grep -Ec 'android:isolatedProcess="true"' \
 host_candidate/p36_node_to_binder/android/AndroidManifest.xml)" -eq 1
PASSWORD="$(openssl rand -hex 20)"
keytool -genkeypair -alias p36only -keyalg RSA -keysize 3072 \
 -validity 30 -storetype PKCS12 \
 -dname 'CN=P36 THROWAWAY OFFLINE TEST NOT ORIGINAL DSH' \
 -keystore out/p36-test-key.p12 -storepass "$PASSWORD" \
 -keypass "$PASSWORD" -noprompt >/dev/null 2>&1
"$BT/apksigner" sign --ks out/p36-test-key.p12 --ks-key-alias p36only \
 --ks-pass "pass:$PASSWORD" --key-pass "pass:$PASSWORD" \
 --out delivery/P36-Private-ARM64-Original-Node-Binder-Bridge.apk out/p36-aligned.apk
"$BT/apksigner" verify delivery/P36-Private-ARM64-Original-Node-Binder-Bridge.apk
# V4 signing may generate a separate .idsig sidecar; the APK already
# carries installable V2/V3 signatures and the private delivery MUST have
# exactly 3 audited files. Remove only this ephemeral sidecar.
rm -f delivery/P36-Private-ARM64-Original-Node-Binder-Bridge.apk.idsig
"$BT/zipalign" -c -P 16 4 delivery/P36-Private-ARM64-Original-Node-Binder-Bridge.apk
"$BT/aapt" dump permissions delivery/P36-Private-ARM64-Original-Node-Binder-Bridge.apk > out/p36/signed-perms.txt
if grep -Fq 'uses-permission:' out/p36/signed-perms.txt;then
 echo "::error::Signed test APK requests prohibited permissions";exit 1
fi
(cd delivery && sha256sum P36-Private-ARM64-Original-Node-Binder-Bridge.apk > SHA256SUMS.txt)
cat > delivery/README-P36-PRIVATE.txt <<'TEXT'
P36: PRIVATE original Node -> real Android Binder -> trusted native UI one-shot.
Android API34+, arm64-v8a only. com.dsh.p36.nodebridge: separate test app,
NOT original DSH and NOT a v139 update. Ephemeral signer, zero permissions.
This privately stored test APK contains the EXACT original signed-v138 Node
binary and 10 immutable ARM64 ELF libs. Never redistribute or publish.
The isolated Worker starts the real original Node binary and checks all
11 ELF SHA-256 against source APK lock before sending a fixed output frame.
Its fixed --eval program ONLY prints process.getuid and JSON canonical
{"op":"METADATA_COUNT","limit":3}. No other JS, network, file, chat,
images, credentials, private diagnostic payload, arbitrary tool execution.
Actual host broker is P32AndroidBinderPort + original P17 grant ledger.
1) Tap "启动原版 Node 隔离测试".
2) Wait until PHASE=AWAITING_TRUSTED_NATIVE_APPROVAL appears.
3) Tap "原生 UI：批准一次固定合成计数" only once.
4) Check complete PASS plus denial-before, approval-once, replay denial.
5) Tap copy report and share the status-only text privately.
This DOES NOT demonstrate original DSH MainActivity, browser/tools,
EngineManager Process/reader/latch migration, arbitrary JS, VM spoofing
or full v139 sandbox. No user DSH binaries, accounts or keys are replaced.
Private Draft GitHub Release only. Do not publish. Production remains BLOCKED.
TEXT
echo 'P36_ORIGINAL_11_ARM64_ELF_VERIFIED=PASS_STATIC' >> "$GITHUB_STEP_SUMMARY"
echo 'P36_TEST_APP_NO_PERMISSIONS_EPHEMERAL_SIGNER=PASS_STATIC' >> "$GITHUB_STEP_SUMMARY"
echo 'P36_REAL_ARM64_ANDROID_NODE_BOOT=NOT_TESTED' >> "$GITHUB_STEP_SUMMARY"
echo 'P36_RELEASE=BLOCKED' >> "$GITHUB_STEP_SUMMARY"
