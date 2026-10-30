#!/usr/bin/env bash
set -euo pipefail
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-/usr/local/lib/android/sdk}}"
BT="$SDK/build-tools/35.0.0"
mkdir -p .p34tmp/classes .p34tmp/dex
javac --release 8 -cp "$SDK/platforms/android-35/android.jar" \
 -d .p34tmp/classes \
 host_candidate/p17_capability/src/com/dsh/p17/P17CapabilityGate.java \
 host_candidate/p32_node_ipc/src/com/dsh/p32/P32NodeIpcBroker.java \
 host_candidate/p32_node_ipc/android/com/dsh/p32/P32AndroidBinderPort.java \
 host_candidate/p34_binder_android/android/com/dsh/p34/brokertest/P34Activity.java \
 host_candidate/p34_binder_android/android/com/dsh/p34/brokertest/P34IsolatedWorker.java
jar cf .p34tmp/classes.jar -C .p34tmp/classes .
"$BT/d8" --min-api 34 --lib "$SDK/platforms/android-35/android.jar" \
  --output .p34tmp/dex .p34tmp/classes.jar
"$BT/aapt" package -f \
  -M host_candidate/p34_binder_android/android/AndroidManifest.xml \
  -I "$SDK/platforms/android-35/android.jar" \
  -F .p34tmp/unsigned.apk
(cd .p34tmp/dex && zip -q -j ../unsigned.apk classes.dex)
"$BT/zipalign" -f 4 .p34tmp/unsigned.apk .p34tmp/aligned.apk
"$BT/zipalign" -c 4 .p34tmp/aligned.apk
"$BT/aapt" dump permissions .p34tmp/aligned.apk > .p34tmp/permissions.txt
if grep -Fq 'uses-permission:' .p34tmp/permissions.txt;then
  echo "::error::P34 test APK must request zero permissions";exit 1
fi
test "$(grep -c 'android:isolatedProcess="true"' \
 host_candidate/p34_binder_android/android/AndroidManifest.xml)" -eq 1
PASS="$(openssl rand -hex 20)"
keytool -genkeypair -alias ephemeral -keyalg RSA -keysize 3072 \
  -validity 1 -storetype PKCS12 -dname 'CN=P34 ISOLATED BINDER CI ONLY' \
  -keystore .p34tmp/test.p12 -storepass "$PASS" \
  -keypass "$PASS" -noprompt >/dev/null 2>&1
"$BT/apksigner" sign --ks .p34tmp/test.p12 --ks-key-alias ephemeral \
  --ks-pass "pass:$PASS" --key-pass "pass:$PASS" \
  --out .p34tmp/p34-emulator-only.apk .p34tmp/aligned.apk
"$BT/apksigner" verify .p34tmp/p34-emulator-only.apk
"$BT/aapt" dump badging .p34tmp/p34-emulator-only.apk \
  | grep -Fq "package: name='com.dsh.p34.brokertest'"
echo 'P34_DISPOSABLE_REAL_BINDER_TEST_APK_COMPILATION=PASS' >> "$GITHUB_STEP_SUMMARY"
echo 'P34_ANDROID_PERMISSIONS=ZERO' >> "$GITHUB_STEP_SUMMARY"
echo 'P34_ORIGINAL_NODE_OR_SIGNER_INCLUDED=NO' >> "$GITHUB_STEP_SUMMARY"
