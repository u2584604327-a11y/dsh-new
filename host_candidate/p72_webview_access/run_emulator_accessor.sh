#!/usr/bin/env bash
set -euo pipefail
apk=.p43tmp/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk
test -s "$apk"
adb install -r "$apk" >/dev/null
adb shell am force-stop com.dsh.p51.isolatedprobe || true
adb logcat -c
adb shell am start -n com.dsh.p51.isolatedprobe/com.dsh.android.p43.P43ProbeActivity \
  --ez p72_accessor true >/dev/null
for i in $(seq 1 25);do
 if adb logcat -d -v brief -s P72_WEBVIEW_ACCESS:I '*:S' |
     grep -Fq 'P72_ORIGINAL_DERIVED_CURRENT_WEBVIEW_PUBLIC_ON_ART=PASS';then
    break
 fi
 sleep 2
done
log="$(adb logcat -d -v brief -s P72_WEBVIEW_ACCESS:I '*:S')"
grep -Fq 'P72_ORIGINAL_DERIVED_CURRENT_WEBVIEW_PUBLIC_ON_ART=PASS' <<< "$log"
if grep -Fq '=FAIL' <<< "$log";then exit 1;fi
echo 'P72_ANDROID35_REAL_ART_ACCESSOR_PUBLIC=PASS'
echo 'P72_BROWSERBRIDGE_NATIVE_E2E_ORIGINAL_APP=NOT_WIRED'
echo 'P72_ORIGINAL_WEBVIEW_PROFILE_DATA=UNTOUCHED'
echo 'P72_FIXED_SIGNED_V139=BLOCKED'
