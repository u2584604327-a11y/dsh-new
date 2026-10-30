#!/usr/bin/env bash
set -euo pipefail
apk=.p43tmp/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk
test -s "$apk"
adb install -r "$apk" >/dev/null
app=com.dsh.p51.isolatedprobe
component="$app/com.dsh.android.p43.P43ProbeActivity"
adb shell am force-stop "$app" || true
adb logcat -c
adb shell am start -n "$component" --ez p71_profile true >/dev/null
for n in $(seq 1 50); do
  if adb logcat -d -v brief -s P71_WEBVIEW_PROFILE:I '*:S' |
    grep -Fq 'P71_COOKIE_DOMSTORAGE_SYNTHETIC_SEEDED=PASS';then break;fi
  sleep 2
done
adb logcat -d -v brief -s P71_WEBVIEW_PROFILE:I '*:S' |
  grep -Fq 'P71_COOKIE_DOMSTORAGE_SYNTHETIC_SEEDED=PASS'
adb shell am force-stop "$app"
sleep 2
adb logcat -c
adb shell am start -n "$component" --ez p71_profile true >/dev/null
for n in $(seq 1 50); do
  if adb logcat -d -v brief -s P71_WEBVIEW_PROFILE:I '*:S' |
    grep -Fq 'P71_COOKIE_DOMSTORAGE_SURVIVE_FORCE_STOP=PASS';then break;fi
  sleep 2
done
logs="$(adb logcat -d -v brief -s P71_WEBVIEW_PROFILE:I '*:S')"
grep -Fq 'P71_COOKIE_DOMSTORAGE_SURVIVE_FORCE_STOP=PASS' <<< "$logs"
if grep -Fq '=FAIL' <<< "$logs";then exit 1;fi
echo 'P71_ANDROID35_WEBVIEW_PROFILE_PERSIST_AFTER_FORCE_STOP=PASS'
echo 'P71_REAL_BILIBILI_LOGIN=NOT_TESTED'
echo 'P71_ORIGINAL_DSH_BROWSER_PROFILE=NOT_MODIFIED'
echo 'P71_ORIGINAL_MODEL_TOOL_RESULT=NOT_WIRED'
