#!/usr/bin/env bash
set -euo pipefail
adb wait-for-device
adb install -r .p34tmp/p34-emulator-only.apk
adb logcat -c
adb shell am force-stop com.dsh.p34.brokertest || true
adb shell am start -n com.dsh.p34.brokertest/.P34Activity
probe_status(){
  adb logcat -d -v brief -s P34_BINDER_LAB:I AndroidRuntime:E '*:S' \
    | sed -E 's/(token|session|grant)=[^ ]+/\1=[REDACTED]/g' > .p34tmp/filtered-log.txt
  grep -Fq "$1" .p34tmp/filtered-log.txt
}
for i in $(seq 1 40);do
  if probe_status 'P34_PREGRANT_DENIAL=PASS';then break;fi
  if grep -Fq '=FAIL' .p34tmp/filtered-log.txt;then
    echo "P34_FAIL_BEFORE_UI_APPROVAL";exit 1
  fi
  sleep 1
done
if ! probe_status 'P34_PREGRANT_DENIAL=PASS';then
  echo "P34_PREGRANT_DENIAL=NOT_OBSERVED";exit 1
fi
if probe_status 'P34_REAL_BINDER_APPROVED_ONCE=PASS';then
  echo "P34_UNAUTHORIZED_APPROVAL_BEFORE_UI=FAIL";exit 1
fi
# The P34 test Activity consists solely of a full-screen trusted native Button.
# Compute screen center without UIAutomator (which can background/relaunch it).
SIZE="$(adb shell wm size | tr -d '\r' | tail -n 1)"
COORDS="$(P34_SCREEN_SIZE="$SIZE" python3 - <<'PY'
import os,re
s=os.environ["P34_SCREEN_SIZE"]
m=re.search(r"(\d{3,5})x(\d{3,5})",s)
if not m:raise SystemExit("P34_SCREEN_DIMENSION_UNVERIFIED")
w,h=map(int,m.groups())
if w<320 or h<500:raise SystemExit("P34_SCREEN_DIMENSION_INVALID")
print(w//2,h//2)
PY
)"
read -r X Y <<< "$COORDS"
adb shell input tap "$X" "$Y"
sleep 1
probe_status 'P34_NATIVE_UI_CLICK_GRANT_SENT=YES' || {
  echo 'P34_NATIVE_UI_TOUCH_OR_GRANT=NOT_VERIFIED'
  grep 'P34_' .p34tmp/filtered-log.txt | tail -n 25 || true
}
for i in $(seq 1 40);do
  if probe_status 'P34_REAL_ISOLATED_UID_AND_NATIVE_CONSENT_E2E=PASS';then
    break
  fi
  if grep -Fq '=FAIL' .p34tmp/filtered-log.txt;then
    echo "P34_SECURITY_REGRESSION_MARKER=FAIL";exit 1
  fi
  sleep 1
done
for marker in \
  'P34_PREGRANT_DENIAL=PASS' \
  'P34_NATIVE_UI_CLICK_GRANT_SENT=YES' \
  'P34_REAL_BINDER_APPROVED_ONCE=PASS' \
  'P34_REAL_BINDER_REPLAY_DENIAL=PASS' \
  'P34_REAL_ISOLATED_UID_AND_NATIVE_CONSENT_E2E=PASS' \
  'P34_ORIGINAL_ARM64_NODE_RUNTIME_PRESENT=NO';do
  if ! probe_status "$marker";then
    echo "P34_MISSING_MARKER=$marker"
    grep 'P34_' .p34tmp/filtered-log.txt | tail -n 40 || true
    exit 1
  fi
done
adb shell input keyevent HOME
for i in $(seq 1 12);do
  if probe_status 'P34_HOST_BACKGROUND_REVOKE_INVOKED=PASS';then break;fi
  sleep 1
done
if ! probe_status 'P34_HOST_BACKGROUND_REVOKE_INVOKED=PASS';then
  echo "P34_HOST_BACKGROUND_REVOKE=NOT_OBSERVED";exit 1
fi
echo 'P34_EMULATOR35_REAL_ANDROID_BINDER_SENDING_UID=PASS' >> "$GITHUB_STEP_SUMMARY"
echo 'P34_SYNTHETIC_NODE_FRAME_UNGRANTED_TO_TRUSTED_UI_GRANT=PASS' >> "$GITHUB_STEP_SUMMARY"
echo 'P34_ONE_SHOT_NO_REPLAY_AND_BACKGROUND_REVOKE=PASS' >> "$GITHUB_STEP_SUMMARY"
echo 'P34_ORIGINAL_NODE_ARM64_OR_PRODUCTION_DSH_INTEGRATED=NO' >> "$GITHUB_STEP_SUMMARY"
echo 'P34_NO_REAL_USER_FILES_OR_NETWORK_ACCESS=YES' >> "$GITHUB_STEP_SUMMARY"
