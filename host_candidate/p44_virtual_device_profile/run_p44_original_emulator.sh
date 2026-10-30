#!/usr/bin/env bash
set -euo pipefail
# P44 extends P43 actual original DSH APK emulator E2E with a bounded
# synthetic virtual profile; it never creates an OS VM or changes hardware ID.
bash host_candidate/p43_original_service/run_original_apk_binder_emulator.sh
log="$(adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S')"
grep -Fq 'P44_ORIGINAL_DSH_PROFILE_TO_ISOLATED_WORKER=PASS' <<< "$log"
grep -Fq 'P44_HOST_SELECTED_VIRTUAL_PROFILE_HASH_VALIDATED=PASS' <<< "$log"
grep -Fq 'P44_ACTUAL_SYSTEM_VM=NO' <<< "$log"
grep -Fq 'P44_REAL_DEVICE_IDENTITY_MODIFIED=NO' <<< "$log"
echo 'P44_ORIGINAL_DSH_HOST_TO_ISOLATED_PROFILE_BINDER=PASS'
echo 'P44_PROFILE_VIRTUAL_VIEW_ONLY=PASS'
echo 'P44_FULL_ANDROID_SYSTEM_VM=NO'
echo 'P44_PHYSICAL_DEVICE_IDENTITY_NOT_CHANGED=PASS'
echo 'P44_REAL_ENGINEMANAGER_NODE_ISOLATED=NO'
echo 'P44_V139_RELEASE=BLOCKED'
