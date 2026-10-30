#!/usr/bin/env bash
set -euo pipefail
apk=.p43tmp/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk
test -s "$apk"
adb install -r "$apk" >/dev/null
adb shell am force-stop com.dsh.p51.isolatedprobe || true
adb logcat -c
adb shell am start -n com.dsh.p51.isolatedprobe/com.dsh.android.p43.P43ProbeActivity \
  --ez p73_tools true >/dev/null
for i in $(seq 1 50);do
  if adb logcat -d -v brief -s P73_BROWSER_TOOL:I '*:S' |
      grep -Fq 'P73_BROWSER_READ_SCROLL_FIND_TYPE_CALLBACK_CHAIN=PASS';then break;fi
  sleep 2
done
log="$(adb logcat -d -v brief -s P73_BROWSER_TOOL:I '*:S')"
for step in 0 1 2 3 4;do
  grep -Fq "P73_WEBVIEW_CALLBACK_STEP_$step=PASS" <<< "$log"
done
grep -Fq 'P73_BROWSER_READ_SCROLL_FIND_TYPE_CALLBACK_CHAIN=PASS' <<< "$log"
grep -Fq 'P73_PUBLIC_COMMENT_ACTUALLY_SENT=NO' <<< "$log"
if grep -Fq '=FAIL' <<< "$log";then exit 1;fi
echo 'P73_REAL_ANDROID_WEBVIEW_EVALUATE_JAVASCRIPT_TOOL_CALLBACK=PASS'
echo 'P73_PAGE_READ_SCROLL_COMMENT_FIELD_FIND_AND_DRAFT=PASS'
echo 'P73_COMMENT_PUBLISH_REQUIRES_NATIVE_APPROVAL=PASS'
echo 'P73_REAL_BILIBILI_SITE_LOGIN_AND_COMMENT=NOT_TESTED'
echo 'P73_ORIGINAL_DSH_MODEL_TOOL_RESUME=NOT_WIRED'
echo 'P73_FIXED_SIGNED_V139=BLOCKED'
