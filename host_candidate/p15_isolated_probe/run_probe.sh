#!/usr/bin/env bash
set -euo pipefail
adb install --no-streaming out/p15-disposable.apk
adb logcat -c
adb shell am start -n com.dsh.p15probe/.P15ProbeActivity
sleep 9
adb logcat -d -s DSH_P15_ISOLATION:I '*:S' > out/p15-logcat-private.txt
for expected in \
  'P15_ISOLATED_UID_DISTINCT=PASS' \
  'P15_PRIVATE_CANARY_READ_DENIED=PASS' \
  'P15_ISOLATED_SERVICE_MANIFEST=PASS' \
  'P15_DSH_NODE_ALREADY_MIGRATED=NO'; do
  grep -Fq "$expected" out/p15-logcat-private.txt || {
    echo "::error::P15 OS isolated-process gate failed: $expected"
    echo 'P15_ACTUAL_EMULATOR_STATUS=FAIL_REDACTED'
    exit 1
  }
done
echo 'P15_ANDROID35_ISOLATED_UID=PASS' >> "$GITHUB_STEP_SUMMARY"
echo 'P15_ANDROID35_HOST_PRIVATE_FILE_DENIAL=PASS' >> "$GITHUB_STEP_SUMMARY"
echo 'P15_DSH_NODE_EXECUTION_MIGRATED=NO' >> "$GITHUB_STEP_SUMMARY"
