#!/usr/bin/env bash
# Disposable test APK, same throwaway signing identity as lab app.
# No production signer, no upload, no Android app sources changed.
set -euo pipefail
: "${SDK_ROOT:?}"
mkdir -p out/instrument-classes out/instrument-dex
src="host_candidate/test-only/com/dsh/p1/smoketest/DshInstrumentation.java"
src_p12="host_candidate/test-only/com/dsh/p1/smoketest/P12LogViewerInstrumentation.java"
src_p13="host_candidate/test-only/com/dsh/p1/smoketest/P13AutoHookInstrumentation.java"
manifest="host_candidate/test-only/AndroidManifest.xml"
test -s "$src" && test -s "$src_p12" && test -s "$src_p13" && test -s "$manifest" && test -s out/p5-native.jar
javac --release 8 -cp "$SDK_ROOT/platforms/android-35/android.jar:out/p5-native.jar" \
  -d out/instrument-classes "$src" "$src_p12" "$src_p13"
jar cf out/p5-ui-instrumentation.jar -C out/instrument-classes .
"$SDK_ROOT/build-tools/35.0.0/d8" --min-api 26 \
  --lib "$SDK_ROOT/platforms/android-35/android.jar" \
  --output out/instrument-dex out/p5-ui-instrumentation.jar
test -s out/instrument-dex/classes.dex
"$SDK_ROOT/build-tools/35.0.0/aapt" package -f \
  -M "$manifest" -I "$SDK_ROOT/platforms/android-35/android.jar" \
  -F out/P5_INSTRUMENTATION_UNSIGNED_DO_NOT_SHARE.apk
(cd out/instrument-dex && zip -q -j ../P5_INSTRUMENTATION_UNSIGNED_DO_NOT_SHARE.apk classes.dex)
"$SDK_ROOT/build-tools/35.0.0/zipalign" -f 4 \
  out/P5_INSTRUMENTATION_UNSIGNED_DO_NOT_SHARE.apk \
  out/P5_INSTRUMENTATION_ALIGNED_DO_NOT_SHARE.apk
"$SDK_ROOT/build-tools/35.0.0/zipalign" -c 4 \
  out/P5_INSTRUMENTATION_ALIGNED_DO_NOT_SHARE.apk
"$SDK_ROOT/build-tools/35.0.0/aapt" dump badging \
  out/P5_INSTRUMENTATION_ALIGNED_DO_NOT_SHARE.apk | grep -F "name='com.dsh.p1.smoketest'"
echo 'P5_P12_INSTRUMENTATION_JAVAC_AND_D8=PASS' >> "$GITHUB_STEP_SUMMARY"
echo 'P5_INSTRUMENTATION_APK_UNSIGNED=CREATED_RUNNER_ONLY' >> "$GITHUB_STEP_SUMMARY"
