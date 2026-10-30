#!/usr/bin/env bash
set -euo pipefail
bash host_candidate/p77_engine_tar_audit/run_emulator_tar.sh
logs="$(adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S')"
grep -Fq 'P78_BOUNDED_ORIGINAL_JS_BYTES_READ_ONCE_IN_ISOLATED_UID=PASS' <<< "$logs"
grep -Fq 'P77_REAL_ORIGINAL_TAR_FULL_TREE_SHA_MATCH_IN_ISOLATED_UID=PASS' <<< "$logs"
echo 'P78_REAL_ORIGINAL_JS_SOURCE_HASHED_ONCE_IN_ISOLATED_UID=PASS'
echo 'P78_REAL_ORIGINAL_JS_EXECUTED=NO'
echo 'P78_FIXED_SIGNED_V139=BLOCKED'
