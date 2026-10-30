#!/usr/bin/env bash
set -euo pipefail
apk=.p43tmp/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk
test -s "$apk"
adb install -r "$apk" >/dev/null
adb shell am force-stop com.dsh.p51.isolatedprobe || true
adb logcat -c
adb shell am start -n com.dsh.p51.isolatedprobe/com.dsh.android.p43.P43ProbeActivity \
  --ez p87_stream_ui true >/dev/null
for i in $(seq 1 45);do
 logs="$(adb logcat -d -v tag -s P87_STREAM_UI:I '*:S')"
 if grep -Fq 'P87_ANDROID_MAIN_THREAD_INCREMENTAL_TEXTVIEW_TWO_PAINTS=PASS' <<< "$logs";then break;fi
 if grep -Fq '=FAIL' <<< "$logs";then
   printf '%s\n' "$logs" | grep -E 'P87_STREAM_UI_.*=FAIL' | tail -n 10 || true
   exit 1
 fi
 sleep 1
done
grep -Fq 'P87_THINKING_EVENT_NO_FAKE_DONE=PASS' <<< "$logs"
grep -Fq 'P87_ANDROID_FIRST_CONTENT_PAINT_BEFORE_DONE=PASS' <<< "$logs"
grep -Fq 'P87_ANDROID_MAIN_THREAD_INCREMENTAL_TEXTVIEW_TWO_PAINTS=PASS' <<< "$logs"
grep -Fq 'P87_REASONING_NOT_RENDERED_AS_ANSWER=PASS' <<< "$logs"
grep -Fq 'P87_ANDROID_SYNTHETIC_SSE_NO_ORIGINAL_DSH_NETWORK=YES' <<< "$logs"
echo 'P87_ANDROID35_NATIVE_TEXTVIEW_RENDER_BEFORE_SSE_DONE=PASS'
echo 'P87_OMNIGATE_DSH_PRODUCTION_NETWORK_UI=NOT_WIRED'
echo 'P87_FIXED_SIGNED_V139=BLOCKED'
