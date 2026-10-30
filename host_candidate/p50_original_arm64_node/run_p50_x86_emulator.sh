#!/usr/bin/env bash
set -euo pipefail
# P50 deliberately does NOT load or execute original arm64 Node on x86.
# P48 real process/UID and P43-P47 regressions must remain functional.
bash host_candidate/p48_process_proxy/run_original_emulator.sh
logs="$(adb logcat -d -v brief -s P43_HOST_BINDER:I '*:S')"
grep -Fq 'P50_X86_OR_MISSING_LOCK_ORIGINAL_NODE_NOT_REQUESTED=YES' <<< "$logs"
if grep -Fq 'P50_REAL_ORIGINAL_DSH_PACKAGE_EXACT_NODE_IN_ISOLATED_UID=PASS' <<< "$logs";then
  echo 'P50_FALSE_CLAIM_ARM64_NODE_RAN_ON_X86=BLOCKED'
  exit 1
fi
echo 'P50_X86_NON_ARM64_SKIP_ORIGINAL_NODE=PASS'
echo 'P50_ORIGINAL_DSH_P48_ISOLATED_SYSTEM_CHILD_REGRESSION=PASS'
echo 'P50_ORIGINAL_DSH_REAL_ARM64_NODE_EXECUTION=NOT_TESTED'
echo 'P50_ENGINEMANAGER_PRODUCTION_RUNTIME=NOT_WIRED'
echo 'P50_FIXED_SIGNED_V139=BLOCKED'
