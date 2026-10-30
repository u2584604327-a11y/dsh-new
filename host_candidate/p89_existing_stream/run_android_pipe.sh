#!/usr/bin/env bash
set -euo pipefail
apk=.p43tmp/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk
test -s "$apk"
adb install -r "$apk" >/dev/null
adb shell am force-stop com.dsh.p51.isolatedprobe || true
adb logcat -c
adb shell am start -n com.dsh.p51.isolatedprobe/com.dsh.android.p43.P43ProbeActivity \
  --ez p89_stream_pipe true >/dev/null
for i in $(seq 1 40); do
  logs="$(adb logcat -d -v tag -s P89_ANDROID_PIPE:V '*:S')"
  if grep -Fq 'P89_FINAL_INCREMENTAL_TEXT_AND_TOOL_FRAGMENT_REASSEMBLY=PASS' <<< "$logs"; then break;fi
  if grep -Fq '=FAIL' <<< "$logs";then
    printf '%s\n' "$logs" | grep '=FAIL' | tail -n 10 || true
    exit 1
  fi
  sleep 1
done
grep -Fq 'P89_FIRST_ANDROID_PAINT_WHILE_PIPE_OPEN=PASS' <<< "$logs"
grep -Fq 'P89_FINAL_INCREMENTAL_TEXT_AND_TOOL_FRAGMENT_REASSEMBLY=PASS' <<< "$logs"
grep -Fq 'P89_REASONING_SEPARATE_TOOL_NOT_EXECUTED=PASS' <<< "$logs"
grep -Fq 'P89_DISPOSABLE_PIPE_NOT_ORIGINAL_DSH_NETWORK=YES' <<< "$logs"
echo 'P89_ANDROID35_EXISTING_INPUTSTREAM_UI_AND_TOOLCALLS=PASS'
echo 'P89_ORIGINAL_DSH_NETWORK_TO_CHAT=NOT_WIRED'
echo 'P89_REAL_OMNIGATE_DEVICE_E2E=NOT_VERIFIED'
