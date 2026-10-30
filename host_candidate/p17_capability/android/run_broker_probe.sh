#!/usr/bin/env bash
set -euo pipefail
adb install --no-streaming out/p17-disposable.apk
adb logcat -c
adb shell am start -n com.dsh.p17.probe/.P17BrokerProbeActivity
# Do not click until real Binder authentication and pre-grant denial have
# happened; fixed sleeps hid CI races and gave misleading failure evidence.
ready=0
for _ in $(seq 1 20); do
  if adb logcat -d -s DSH_P17_BROKER:I '*:S' | grep -Fq 'P17_PREGRANT_DENIED=PASS'; then
    ready=1
    break
  fi
  sleep 1
done
if test "$ready" != 1; then
  echo "::error::P18 pre-grant state not reached; no simulated user approval"
  adb logcat -d -s DSH_P17_BROKER:I '*:S' | grep -E 'P17_|P18_' | tail -n 25 || true
  exit 1
fi
# Use the actual Android UI hierarchy to locate the test-only user gesture.
# Never approximate display density or click arbitrary screen locations.
adb shell uiautomator dump /sdcard/p17-ui-test.xml >/dev/null
adb exec-out cat /sdcard/p17-ui-test.xml > out/p17-ui-test.xml
if ! python3 - <<'PY' > out/p17-tap-point.txt; then
import re,xml.etree.ElementTree as ET
root=ET.parse("out/p17-ui-test.xml").getroot()
nodes=list(root.iter("node"))
found=[n for n in nodes if n.attrib.get("content-desc")=="P17_APPROVE_ONCE"]
if len(found)!=1:
    # The emulator contains only synthetic test UI. Print bounded metadata,
    # not the entire hierarchy or private files.
    print("P18_UI_TREE_NODE_COUNT="+str(len(nodes)),file=__import__("sys").stderr)
    print("P18_PROBE_PACKAGE_VISIBLE="+str(any(n.attrib.get("package")=="com.dsh.p17.probe" for n in nodes)),file=__import__("sys").stderr)
    raise SystemExit("P18_TEST_BUTTON_A11Y_LOCATOR_NOT_FOUND")
if found[0].attrib.get("enabled")!="true":
    raise SystemExit("P18_TEST_BUTTON_NOT_ENABLED")
m=re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",found[0].attrib.get("bounds",""))
if not m:raise SystemExit("P18_UI_BOUNDS_MISSING")
x1,y1,x2,y2=map(int,m.groups())
if not(x2>x1 and y2>y1):raise SystemExit("P18_BAD_BUTTON_BOUNDS")
print((x1+x2)//2,(y1+y2)//2)
PY
  echo '::error::P18 trusted test-only UI locator failed; no tap performed'
  adb shell dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity' | tail -n 4 || true
  adb logcat -d -s DSH_P17_BROKER:I '*:S' |
    grep -E 'P17_|P18_' | tail -n 25 || true
  exit 1
fi
read -r tapx tapy < out/p17-tap-point.txt
rm -f out/p17-tap-point.txt
# Exactly one test-only input tap. Never silently retry a privileged gesture.
adb shell input tap "$tapx" "$tapy"
adb shell rm -f /sdcard/p17-ui-test.xml
rm -f out/p17-ui-test.xml
approved=0
for _ in $(seq 1 20); do
  adb logcat -d -s DSH_P17_BROKER:I '*:S' > out/p17-private-log.txt
  if grep -Fq 'P17_ARBITRARY_FILE_SCOPE_DENIED=PASS' out/p17-private-log.txt; then
    approved=1
    break
  fi
  sleep 1
done
if test "$approved" != 1; then
  # Only bounded, synthetic probe markers are printed; never app log contents.
  echo '::error::P18 real user-click / Binder grant / query transition incomplete'
  grep -E 'P17_|P18_' out/p17-private-log.txt | tail -n 40 || true
  exit 1
fi
for marker in \
 'P17_REAL_BINDER_UID=PASS' \
 'P17_PREGRANT_DENIED=PASS' \
 'P18_USER_CLICK_RECEIVED=YES' \
 'P17_TRUSTED_UI_GRANT=PASS' \
 'P17_ONE_SHOT_APPROVED=PASS' \
 'P17_REPLAY_DENIED=PASS' \
 'P17_ARBITRARY_FILE_SCOPE_DENIED=PASS' \
 'P17_DSH_NODE_MIGRATED=NO'; do
  if ! grep -Fq "$marker" out/p17-private-log.txt; then
    echo "::error::P17 real Binder broker violation; expected fixed marker $marker"
    exit 1
  fi
done
if grep -Eq 'P17_.*=FAIL' out/p17-private-log.txt; then
  echo '::error::P17 unexpected broker failure'
  exit 1
fi
# Real Activity lifecycle regression: leaving the trusted foreground UI
# must revoke all outstanding grants. No new approval or privileged send.
adb shell input keyevent KEYCODE_HOME
revoked=0
for _ in $(seq 1 10); do
  if adb logcat -d -s DSH_P17_BROKER:I '*:S' |
       grep -Fq 'P18_ALL_GRANTS_REVOKED=UI_BACKGROUND'; then
    revoked=1
    break
  fi
  sleep 1
done
if test "$revoked" != 1; then
  echo '::error::P18 foreground-loss revocation marker absent'
  adb logcat -d -s DSH_P17_BROKER:I '*:S' |
    grep -E 'P17_|P18_' | tail -n 30 || true
  exit 1
fi
echo 'P18_UI_BACKGROUND_GRANTS_REVOKED=PASS_ANDROID35' >> "$GITHUB_STEP_SUMMARY"
echo 'P17_BINDER_SENDING_UID_ISOLATED=PASS_ANDROID35' >> "$GITHUB_STEP_SUMMARY"
echo 'P17_HOST_UI_EXPLICIT_GRANT=PASS_ANDROID35' >> "$GITHUB_STEP_SUMMARY"
echo 'P17_ONE_SHOT_REPLAY_AND_RAW_FILE_DENIAL=PASS_ANDROID35' >> "$GITHUB_STEP_SUMMARY"
echo 'P17_DSH_NODE_ACTUAL_ISOLATED_MIGRATION=NO' >> "$GITHUB_STEP_SUMMARY"
echo 'P18_UI_GESTURE_OBSERVED_AND_APPROVAL_DELIVERED=PASS_ANDROID35' >> "$GITHUB_STEP_SUMMARY"
echo 'P18_SERVICE_DISCONNECT_REVOCATION=SOURCE_PRESENT_NOT_RUNTIME_VERIFIED' >> "$GITHUB_STEP_SUMMARY"
