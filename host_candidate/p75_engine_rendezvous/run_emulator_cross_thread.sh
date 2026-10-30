#!/usr/bin/env bash
set -euo pipefail
apk=.p43tmp/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk
test -s "$apk"
adb install -r "$apk" >/dev/null
adb shell am force-stop com.dsh.p51.isolatedprobe || true
adb logcat -c
adb shell am start -n com.dsh.p51.isolatedprobe/com.dsh.android.p43.P43ProbeActivity \
  --ez p75_rendezvous true >/dev/null
for i in $(seq 1 50);do
  if adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S' |
     grep -Fq 'P75_REAL_ORIGINAL_P40_ASYNC_THREAD_RETURNED_IDENTICAL_P37=PASS';then
    break
  fi
  sleep 2
done
logs="$(adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S')"
grep -Fq 'P47_REAL_ORIGINAL_MAIN_DEX_ENGINE_BRIDGE_DENIES_HOST_START=PASS' <<< "$logs"
grep -Fq 'P75_ORIGINAL_P40_BRIDGE_WAITING_ON_OTHER_THREAD=PASS' <<< "$logs"
grep -Fq 'P75_REAL_BINDER_CHILD_STARTED_DELIVERED_ACROSS_THREADS=PASS' <<< "$logs"
grep -Fq 'P75_REAL_ORIGINAL_P40_ASYNC_THREAD_RETURNED_IDENTICAL_P37=PASS' <<< "$logs"
grep -Fq 'P53_AUTHENTICATED_CHILD_STARTED_BEFORE_PROCESS_HANDOFF=PASS' <<< "$logs"
grep -Fq 'P68_ANDROID_BINDER_P67_P37_CHILD_HANDOFF=PASS' <<< "$logs"
if grep -Eq 'P43_EMBEDDED_ISOLATED_SERVICE_FAIL=|P48_REAL_ORIGINAL_PROCESS_PROXY=BLOCKED_' <<< "$logs";then
  echo 'P75_ENGINE_BRIDGE_RESULT=BLOCKED'
  exit 1
fi
echo 'P75_ORIGINAL_MAIN_DEX_P40_ASYNC_CALL_WAITED_FOR_REAL_BINDER_P37=PASS'
echo 'P75_NO_HOST_PROCESSBUILDER_FALLBACK=PASS'
echo 'P75_PRODUCTION_ENGINE_COROUTINE_NODE_JS_READY_EXIT_CANCEL=NOT_TESTED'
echo 'P75_FORMAL_FIXED_SIGNED_V139=BLOCKED'
