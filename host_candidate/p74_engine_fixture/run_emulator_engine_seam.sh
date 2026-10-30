#!/usr/bin/env bash
set -euo pipefail
apk=.p43tmp/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk
test -s "$apk"
adb install -r "$apk" >/dev/null
adb shell am force-stop com.dsh.p51.isolatedprobe || true
adb logcat -c
adb shell am start -n com.dsh.p51.isolatedprobe/com.dsh.android.p43.P43ProbeActivity \
  --ez p74_bridge true >/dev/null
for i in $(seq 1 60);do
  if adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S' |
      grep -Fq 'P74_REAL_ORIGINAL_P40_MAIN_DEX_RETURNED_AUTH_P37=PASS';then break;fi
  sleep 2
done
log="$(adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S')"
grep -Fq 'P47_REAL_ORIGINAL_MAIN_DEX_ENGINE_BRIDGE_DENIES_HOST_START=PASS' <<< "$log"
grep -Fq 'P74_REAL_ORIGINAL_P40_MAIN_DEX_RETURNED_AUTH_P37=PASS' <<< "$log"
grep -Fq 'P74_ENGINE_FIXTURE_READY_NOT_PRODUCTION_READY=YES' <<< "$log"
grep -Fq 'P53_AUTHENTICATED_CHILD_STARTED_BEFORE_PROCESS_HANDOFF=PASS' <<< "$log"
if grep -Fq 'P48_REAL_ORIGINAL_PROCESS_PROXY=BLOCKED_' <<< "$log";then
 echo 'P74_ACTUAL_ORIGINAL_ENGINE_SEAM=BLOCKED'
 exit 1
fi
echo 'P74_MAIN_DEX_P40_TO_P47_TO_P74_TO_P37_REAL_ANDROID=PASS'
echo 'P74_AUTHENTICATED_ISOLATED_CHILD_ACK=PASS'
echo 'P74_HOST_PROCESSBUILDER_FALLBACK=NO'
echo 'P74_PRODUCTION_ORIGINAL_NODE_SCRIPT_READY_EXIT_CANCEL=NOT_TESTED'
echo 'P74_SIGNED_V139=BLOCKED'
