#!/usr/bin/env bash
set -euo pipefail
apk=.p43tmp/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk
test -s "$apk"
adb install -r "$apk" >/dev/null
adb shell am force-stop com.dsh.p51.isolatedprobe || true
adb logcat -c
adb shell am start -n com.dsh.p51.isolatedprobe/com.dsh.android.p43.P43ProbeActivity \
  --ez p75_rendezvous true --ez p76_archive true >/dev/null
for i in $(seq 1 75);do
  logs="$(adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S')"
  if grep -Fq 'P76_REAL_ORIGINAL_ENGINE_GZIP_READONLY_FD_ISOLATED_SHA=PASS' <<< "$logs" &&
     grep -Fq 'P75_REAL_ORIGINAL_P40_ASYNC_THREAD_RETURNED_IDENTICAL_P37=PASS' <<< "$logs";then
    break
  fi
  if grep -Fq 'P76_ORIGINAL_ARCHIVE_TRANSPORT=FAIL_' <<< "$logs";then
    echo 'P76_ENGINE_TRANSFER_FAILED';exit 1
  fi
  sleep 2
done
logs="$(adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S')"
grep -Fq 'P76_REAL_ORIGINAL_ENGINE_GZIP_READONLY_FD_ISOLATED_SHA=PASS' <<< "$logs"
grep -Fq 'P76_ISOLATED_SOURCE_ARCHIVE_NOT_EXECUTED=YES' <<< "$logs"
grep -Fq 'P75_REAL_ORIGINAL_P40_ASYNC_THREAD_RETURNED_IDENTICAL_P37=PASS' <<< "$logs"
grep -Fq 'P68_ANDROID_BINDER_P67_P37_CHILD_HANDOFF=PASS' <<< "$logs"
grep -Fq 'P47_REAL_ORIGINAL_MAIN_DEX_ENGINE_BRIDGE_DENIES_HOST_START=PASS' <<< "$logs"
if grep -Eq 'P76_ORIGINAL_ARCHIVE_TRANSPORT=FAIL_|P48_REAL_ORIGINAL_PROCESS_PROXY=BLOCKED_' <<< "$logs";then
 echo 'P76_ORIGINAL_ASSET_ISOLATED_TRANSFER=BLOCKED';exit 1
fi
echo 'P76_ORIGINAL_ENGINE_BIN_SHA256_VERIFIED_ACROSS_REAL_BINDER_FD=PASS'
echo 'P76_ORIGINAL_ENGINE_GZIP_BYTES_NOT_EXTRACTED_OR_EXECUTED=YES'
echo 'P76_P75_ENGINE_PROCESS_BROKER_AND_ASSET_FD_COEXIST=PASS'
echo 'P76_REAL_NODE_JS_IMPORT_READY_EXIT_CANCEL=NOT_IMPLEMENTED'
echo 'P76_FIXED_SIGNED_V139=BLOCKED'
