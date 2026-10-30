#!/usr/bin/env bash
set -euo pipefail
bash host_candidate/p76_original_engine_fd/run_emulator_archive.sh
logs="$(adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S')"
grep -Fq 'P77_REAL_ORIGINAL_TAR_FULL_TREE_SHA_MATCH_IN_ISOLATED_UID=PASS' <<< "$logs"
echo 'P77_REAL_ORIGINAL_TAR_MEMBERS_AND_SHA_MATCH_ANDROID=PASS'
echo 'P77_JS_MODULE_EXECUTED=NO'
echo 'P77_FIXED_SIGNED_V139=BLOCKED'
