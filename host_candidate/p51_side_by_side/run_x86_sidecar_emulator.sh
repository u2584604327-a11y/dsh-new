#!/usr/bin/env bash
set -euo pipefail
# Only the disposable x86 emulator; no original-package install/uninstall.
pkg=com.dsh.p51.isolatedprobe
file=.p43tmp/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk
test -s "$file"
adb wait-for-device
if adb shell pm list packages com.dsh.android | tr -d '\r' | grep -Fxq 'package:com.dsh.android';then
  echo 'P51_BLOCKED_ORIGINAL_DSH_PACKAGE_ALREADY_EXISTS_ON_EMULATOR'
  exit 1
fi
cleanup(){
  adb shell am force-stop "$pkg" >/dev/null 2>&1 || true
  adb uninstall "$pkg" >/dev/null 2>&1 || true
}
trap cleanup EXIT
adb install "$file" | grep -Fxq Success
adb shell pm list packages "$pkg" | tr -d '\r' | grep -Fxq "package:$pkg"
if adb shell pm list packages com.dsh.android | tr -d '\r' | grep -Fxq 'package:com.dsh.android';then
  echo 'P51_BLOCKED_ORIGINAL_PACKAGE_CREATED';exit 1
fi
adb logcat -c
adb shell am start -W -n "$pkg/com.dsh.android.p43.P43ProbeActivity" \
  | grep -Eq 'Status: ok|Status: warning'
passed=false
for i in $(seq 1 30);do
  logs="$(adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S')"
  if grep -Fq 'P48_REAL_ORIGINAL_PROCESS_PROXY=BLOCKED_' <<< "$logs" ||
     grep -Fq 'P43_EMBEDDED_ISOLATED_SERVICE_FAIL=' <<< "$logs";then
     echo 'P51_SEPARATE_PACKAGE_BINDER_OR_PROCESS_PROXY=BLOCKED';exit 1
  fi
  if grep -Fq 'P51_SIDE_BY_SIDE_TEST_NOT_ORIGINAL_DSH=YES' <<< "$logs" &&
     grep -Fq 'P47_NO_HOST_PROCESSBUILDER_FALLBACK=PASS' <<< "$logs" &&
     grep -Fq 'P43_REAL_ORIGINAL_APK_BINDER_ISOLATED_UID=PASS' <<< "$logs" &&
     grep -Fq 'P48_ORIGINAL_APK_ISOLATED_CHILD_UID_MATCHES_BINDER=PASS' <<< "$logs" &&
     grep -Fq 'P48_P37_PROCESS_STDOUT_EOF_WAIT_EXIT=PASS' <<< "$logs" &&
     grep -Fq 'P50_X86_OR_MISSING_LOCK_ORIGINAL_NODE_NOT_REQUESTED=YES' <<< "$logs";then
    passed=true;break
  fi
  sleep 1
done
test "$passed" = true || {
  echo 'P51_SEPARATE_PACKAGE_RUNTIME=NOT_VERIFIED';exit 1;
}
adb shell pidof "$pkg" >/dev/null
echo 'P51_DISTINCT_PACKAGE_INSTALL_AND_LAUNCH=PASS'
echo 'P51_NONEXPORTED_ISOLATED_BINDER_UID=PASS'
echo 'P51_P37_PROCESS_STDOUT_WAIT_AND_EXIT=PASS_X86_FIXED_WITNESS'
echo 'P51_REAL_ORIGINAL_DSH_INSTALL_NOT_TOUCHED=PASS'
echo 'P51_REAL_ARM64_NODE_BOOT=NOT_TESTED_X86'
echo 'P51_PRODUCTION_DSH_APPLICATION_AND_CHAT_PARITY=NOT_TESTED'
echo 'P51_FORMAL_FIXED_SIGNED_V139=BLOCKED'
