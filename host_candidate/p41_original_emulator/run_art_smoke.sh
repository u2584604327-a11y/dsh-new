#!/usr/bin/env bash
set -euo pipefail
# Fresh disposable x86_64 Android 35 emulator only. No user data, no release key.
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-/usr/local/lib/android/sdk}}"
BT="$SDK/build-tools/35.0.0"
DIR=".p41tmp"
ORIGINAL="$DIR/DSH-vc138-P0-OFFLINE-TEST-fixed-signature.apk"
CANDIDATE="$DIR/ART-ONLY-EPHEMERAL-DO-NOT-INSTALL-ON-OWNER-DEVICE.apk"
test -s "$ORIGINAL" && test -s "$CANDIDATE"
adb wait-for-device
adb root
adb wait-for-device
adb shell id | grep -Eq 'uid=0\(' || { echo "P41_EMULATOR_ROOT_FOR_NETWORK_BLOCK=BLOCKED"; exit 1; }
adb shell command -v iptables >/dev/null
adb shell command -v ip6tables >/dev/null
get_launchable(){
  "$BT/aapt" dump badging "$1" | sed -n "s/^launchable-activity: name='\([^']*\)'.*/\1/p" | head -n 1
}
control_launch="$(get_launchable "$ORIGINAL")"
candidate_launch="$(get_launchable "$CANDIDATE")"
test -n "$control_launch" && test "$control_launch" = "$candidate_launch"
test "$control_launch" = "com.dsh.android.MainActivity" || {
  echo "P41_BASELINE_ACTIVITY_DRIFT=BLOCKED"; exit 1;
}
run_app(){
  local apk="$1" marker="$2" uid output pid
  adb shell pm uninstall com.dsh.android >/dev/null 2>&1 || true
  adb install "$apk" | grep -Fxq Success
  uid="$(adb shell pm list packages -U com.dsh.android | sed -n -E 's/^package:com\.dsh\.android uid:([0-9]+).*/\1/p' | tr -d '\r' | head -n1)"
  test -n "$uid" && [[ "$uid" =~ ^[0-9]+$ ]]
  # Owner-UID firewall on BOTH IP families. If either rule fails do not launch.
  adb shell iptables -w -I OUTPUT 1 -m owner --uid-owner "$uid" -j REJECT
  adb shell ip6tables -w -I OUTPUT 1 -m owner --uid-owner "$uid" -j REJECT
  adb shell iptables -S OUTPUT | grep -F -- "--uid-owner $uid" | grep -Fq REJECT
  adb shell ip6tables -S OUTPUT | grep -F -- "--uid-owner $uid" | grep -Fq REJECT
  adb logcat -c
  output="$(adb shell am start -W -n "com.dsh.android/$control_launch" 2>&1)"
  printf '%s\n' "$output" | grep -Eq 'Status: ok|Status: warning' || {
    echo "P41_${marker}_ACTIVITY_START=BLOCKED"; exit 1;
  }
  sleep 6
  pid="$(adb shell pidof com.dsh.android | tr -d '\r' || true)"
  if ! [[ "$pid" =~ ^[0-9]+$ ]]; then
    echo "P41_${marker}_PROCESS_ALIVE=BLOCKED"; exit 1
  fi
  # Do not upload logcat: contains app/runtime/intent details.
  local crashes
  crashes="$(adb logcat -d -v brief -s AndroidRuntime:E '*:S' \
    | grep -Ec 'FATAL EXCEPTION|Process: com.dsh.android' || true)"
  test "$crashes" = "0" || {
    echo "P41_${marker}_ANDROIDRUNTIME_CRASH=BLOCKED"; exit 1;
  }
  echo "P41_${marker}_FRESH_EMULATOR_ACTIVITY_START=PASS_NARROW"
  echo "P41_${marker}_FRESH_EMULATOR_PROCESS_SURVIVED_6S=PASS_NARROW"
  adb shell am force-stop com.dsh.android
  adb shell iptables -w -D OUTPUT -m owner --uid-owner "$uid" -j REJECT
  adb shell ip6tables -w -D OUTPUT -m owner --uid-owner "$uid" -j REJECT
  adb shell pm uninstall com.dsh.android >/dev/null
}
run_app "$ORIGINAL" ORIGINAL_SIGNED_V138_CONTROL
run_app "$CANDIDATE" PATCHED_TRAMPOLINE_TEST_SIGNER
echo "P41_ANDROID_EMULATOR35_ART_LAUNCH_PARITY=PASS_NARROW"
echo "P41_REAL_DSH_NODE_ISOLATION=NO"
echo "P41_REAL_CHAT_BROWSER_ATTACHMENTS=NOT_TESTED"
echo "P41_OWNER_ANDROID16_DEVICE_AND_FIXED_SIGNATURE=NOT_TESTED"
echo "P41_V139_RELEASE=BLOCKED"
