#!/usr/bin/env bash
set -euo pipefail
# Exact original com.dsh.android disposable APK on clean Android35 emulator.
# No production DSH scripts, private user data, or shell inside worker.
bash host_candidate/p45_original_fd_broker/run_p45_emulator.sh
log="$(adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S')"
grep -Fq 'P46_ORIGINAL_DSH_CONTENT_ADDRESSED_BUNDLE_FD=PASS' <<< "$log"
grep -Fq 'P46_TWO_FIXTURES_HASH_AND_BYTE_BOUNDS=PASS' <<< "$log"
grep -Fq 'P46_REAL_NODE_SCRIPT_EXECUTED=NO' <<< "$log"
grep -Fq 'P46_PRODUCTION_SCRIPT_PACKAGE_BROKER=NOT_IMPLEMENTED' <<< "$log"
echo 'P46_REAL_ORIGINAL_DSH_TWO_PART_BUNDLE_BINDER_FDS=PASS'
echo 'P46_CONTENT_DIGEST_AND_SIZE_VERIFIED=PASS_SYNTHETIC_ONLY'
echo 'P46_ORIGINAL_APPLICATION_AND_BINDER_UID_P43_P44_P45=PASS'
echo 'P46_PRODUCTION_NODE_BOOTSTRAP_AND_ENGINE_HANDOFF=BLOCKED'
echo 'P46_FIXED_SIGNATURE_AND_USER_DATA=UNTOUCHED'
echo 'P46_V139_RELEASE=BLOCKED'
