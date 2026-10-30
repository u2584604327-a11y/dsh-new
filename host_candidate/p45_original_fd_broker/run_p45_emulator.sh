#!/usr/bin/env bash
set -euo pipefail
# All operations are limited to disposable Android emulator. No owner APK/data.
bash host_candidate/p43_original_service/run_original_apk_binder_emulator.sh
# P43 run script uninstalls disposable APK after proof. Logcat survives uninstall.
log="$(adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S')"
grep -Fq 'P45_ORIGINAL_DSH_HOST_PRIVATE_ASSET_FD_TO_ISOLATED_WORKER=PASS' <<< "$log"
grep -Fq 'P45_BOUNDED_SYNTHETIC_ASSET_SHA256=PASS' <<< "$log"
grep -Fq 'P45_ROOT_REQUIRED=NO' <<< "$log"
grep -Fq 'P45_HOST_PATH_SHARED=NO' <<< "$log"
grep -Fq 'P45_PRODUCTION_ENGINE_SCRIPT_BROKER=NOT_IMPLEMENTED' <<< "$log"
grep -Fq 'P44_ORIGINAL_DSH_PROFILE_TO_ISOLATED_WORKER=PASS' <<< "$log"
echo 'P45_REAL_ORIGINAL_DSH_READONLY_FD_BROKER_SYNTHETIC=PASS'
echo 'P45_ISOLATED_WORKER_RECEIVED_APPROVED_TEST_BYTES=PASS'
echo 'P45_HOST_PRIVATE_PATH_NOT_TRANSFERRED=PASS'
echo 'P45_TEMP_ROOT_AND_ROOT_EXPLOIT_USED=NO'
echo 'P45_PRODUCTION_NODE_SCRIPT_RUNTIME_BROKER=NOT_IMPLEMENTED'
echo 'P45_REAL_DSH_V139_APK=BLOCKED'
