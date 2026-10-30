#!/usr/bin/env bash
set -euo pipefail
apk=.p43tmp/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk
test -s "$apk"
adb install -r "$apk" >/dev/null
adb shell am force-stop com.dsh.p51.isolatedprobe || true
adb logcat -c
adb shell am start -n com.dsh.p51.isolatedprobe/com.dsh.android.p43.P43ProbeActivity \
  --es p85_restart_mode seed >/dev/null
for i in $(seq 1 35);do
 logs="$(adb logcat -d -v brief -s P85_RESTART:I '*:S')"
 if grep -Fq 'P85_REAL_ANDROID_PRE_FORCESTOP_DURABLE_START_AND_TERMINAL=PASS' <<< "$logs";then break;fi
 sleep 1
done
grep -Fq 'P85_REAL_ANDROID_PRE_FORCESTOP_DURABLE_START_AND_TERMINAL=PASS' <<< "$logs"
adb shell am force-stop com.dsh.p51.isolatedprobe
sleep 2
adb shell am start -n com.dsh.p51.isolatedprobe/com.dsh.android.p43.P43ProbeActivity \
  --es p85_restart_mode recover >/dev/null
for i in $(seq 1 35);do
 logs="$(adb logcat -d -v brief -s P85_RESTART:I '*:S')"
 if grep -Fq 'P85_REAL_ANDROID_FORCESTOP_DURABLE_TOOL_OUTCOMES=PASS' <<< "$logs";then break;fi
 sleep 1
done
grep -Fq 'P85_ANDROID_PROCESS_RESTART_INFLIGHT_UNKNOWN_NO_REPLAY=PASS' <<< "$logs"
grep -Fq 'P85_ANDROID_PROCESS_RESTART_COMMITTED_REPLY_RECOVERED=PASS' <<< "$logs"
grep -Fq 'P85_INVALID_REQUEST_ID_REJECTED=PASS' <<< "$logs"
grep -Fq 'P85_REAL_ANDROID_FORCESTOP_DURABLE_TOOL_OUTCOMES=PASS' <<< "$logs"
grep -Fq 'P85_PUBLIC_COMMENT_POSTED=NO' <<< "$logs"
if grep -Fq 'P85_RESTART_PROBE=FAIL_SAFE' <<< "$logs";then exit 1;fi
echo 'P85_ANDROID35_FORCESTOP_RELAUNCH_DURABLE_REPLY_UNKNOWN_NO_REPLAY=PASS'
bash host_candidate/p83_hidden_browser/run_emulator_hidden.sh
echo 'P85_P79_NATIVE_TOOL_CALLBACK_PERSISTS_BEFORE_RESULT_MAILBOX=PASS'
echo 'P85_REAL_ORIGINAL_DSH_MODEL_CONTINUATION=NOT_WIRED'
echo 'P85_FIXED_SIGNED_V139=BLOCKED'
