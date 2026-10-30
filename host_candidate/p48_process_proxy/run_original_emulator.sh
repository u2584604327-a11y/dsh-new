#!/usr/bin/env bash
set -euo pipefail
adb wait-for-device
adb root
adb wait-for-device
adb shell id | grep -Eq 'uid=0\('
file=.p43tmp/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk
test -s "$file"
adb shell pm uninstall com.dsh.android >/dev/null 2>&1 || true
adb install "$file" | grep -Fxq Success
uid="$(adb shell pm list packages -U com.dsh.android | sed -n -E 's/^package:com\.dsh\.android uid:([0-9]+).*/\1/p' | tr -d '\r' | head -n1)"
[[ "$uid" =~ ^[0-9]+$ ]]
adb shell iptables -w -I OUTPUT 1 -m owner --uid-owner "$uid" -j REJECT
adb shell ip6tables -w -I OUTPUT 1 -m owner --uid-owner "$uid" -j REJECT
adb shell iptables -S OUTPUT | grep -F -- "--uid-owner $uid" | grep -Fq REJECT
adb shell ip6tables -S OUTPUT | grep -F -- "--uid-owner $uid" | grep -Fq REJECT
adb logcat -c
launch="$(${ANDROID_HOME:-${ANDROID_SDK_ROOT:-/usr/local/lib/android/sdk}}/build-tools/35.0.0/aapt dump badging "$file" | sed -n "s/^launchable-activity: name='\([^']*\)'.*/\1/p" | head -n1)"
test -n "$launch"
adb shell am start -W -n "com.dsh.android/$launch" | grep -Eq 'Status: ok|Status: warning'
sleep 4
adb shell pidof com.dsh.android >/dev/null
echo "P43_ORIGINAL_DSH_MAIN_ACTIVITY_ART_LAUNCH=PASS_NARROW"
adb shell am start -W -n com.dsh.android/com.dsh.android.p43.P43ProbeActivity \
  | grep -Eq 'Status: ok|Status: warning'
passed=false
for i in $(seq 1 20); do
  adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S' \
    | grep -Fq 'P43_REAL_ORIGINAL_APK_BINDER_ISOLATED_UID=PASS' && { passed=true; break; }
  if adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S' \
    | grep -Fq 'P43_EMBEDDED_ISOLATED_SERVICE_FAIL='; then
      echo "P43_REAL_BINDER_ISOLATED_UID=BLOCKED"; exit 1
  fi
  sleep 1
done
test "$passed" = true || { echo "P43_EMBEDDED_WORKER_START_OR_APP_INIT=NOT_VERIFIED"; exit 1; }
# P48 real original host / isolated system child / P37 Process facade.
# No ARM64 original Node executable is installed or launched in this phase.
p48_passed=false
for i in $(seq 1 20); do
  logs="$(adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S')"
  if grep -Fq 'P48_REAL_ORIGINAL_PROCESS_PROXY=BLOCKED_' <<< "$logs"; then
    echo 'P48_P37_ISOLATED_PROCESS_PROXY=BLOCKED_REPORTED'
    exit 1
  fi
  if grep -Fq 'P48_ORIGINAL_APK_ISOLATED_CHILD_UID_MATCHES_BINDER=PASS' <<< "$logs" &&
     grep -Fq 'P48_P37_PROCESS_STDOUT_EOF_WAIT_EXIT=PASS' <<< "$logs" &&
     grep -Fq 'P48_HOST_DID_NOT_EXECUTE_CHILD=PASS_SCOPE_LIMITED' <<< "$logs" &&
     grep -Fq 'P47_REAL_ORIGINAL_MAIN_DEX_ENGINE_BRIDGE_DENIES_HOST_START=PASS' <<< "$logs"; then
    p48_passed=true;break
  fi
  sleep 1
done
test "$p48_passed" = true || {
  echo 'P48_ACTUAL_ISOLATED_CHILD_AND_P37_PROXY=NOT_VERIFIED'
  exit 1
}
echo 'P48_REAL_ORIGINAL_DSH_ISOLATED_CHILD_P37_PROCESS_PROXY=PASS'
echo 'P48_REAL_ORIGINAL_DSH_CHILD_UID_EQUALS_BINDER_UID=PASS'
echo 'P48_REAL_ORIGINAL_DSH_PROCESS_WAIT_STDOUT_EOF=PASS'
echo 'P48_P47_PRIMARY_ENGINE_START_STILL_FAIL_CLOSED=PASS'
echo 'P48_PRODUCTION_DSH_NODE_EXECUTED=NO'
echo 'P48_ANDROID_16_ARM64_REAL_NODE_IN_ORIGINAL_APK=NOT_TESTED'
echo 'P48_FIXED_SIGNED_V139_RELEASE=BLOCKED'
echo "P43_REAL_ORIGINAL_DSH_APK_ISOLATED_BINDER=PASS"
echo "P43_ORIGINAL_APP_HAS_REAL_ISOLATED_SERVICE=PASS"
echo "P43_REAL_NODE_OR_PRODUCTION_ENGINEMANAGER_ISOLATED=NO"
echo "P43_X86_EMULATOR_ACTUAL_ARM64_NODE=NOT_TESTED"
echo "P43_FIXED_SIGNER_USED=NO"
echo "P43_V139_RELEASE=BLOCKED"
adb shell am force-stop com.dsh.android
adb shell iptables -w -D OUTPUT -m owner --uid-owner "$uid" -j REJECT
adb shell ip6tables -w -D OUTPUT -m owner --uid-owner "$uid" -j REJECT
adb shell pm uninstall com.dsh.android >/dev/null
