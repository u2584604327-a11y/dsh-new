#!/usr/bin/env bash
set -euo pipefail
adb install --no-streaming out/p20-disposable.apk
adb logcat -c
adb shell am start -n com.dsh.p20.boundary/.P20BoundaryActivity
done_marker=0
for i in $(seq 1 30); do
  adb logcat -d -s DSH_P20_BOUNDARY:I '*:S' > out/p20-probe-log-local.txt
  if grep -Fq 'P20_REAL_DSH_NODE_PROCESS_MIGRATED=NO' out/p20-probe-log-local.txt; then
    done_marker=1
    break
  fi
  sleep 1
done
if test "$done_marker" -ne 1; then
  echo '::error::P20 boundary probe did not reach final IPC reply; no PASS'
  grep 'P20_' out/p20-probe-log-local.txt | tail -n 25 || true
  exit 1
fi
for marker in \
  'P20_HOST_INTERNET_LOOPBACK_POSITIVE_CONTROL=PASS' \
  'P20_FRAMEWORK_ISOLATED_UID=PASS' \
  'P20_HOST_PRIVATE_CANARY_UNREADABLE=PASS' \
  'P20_HOST_INTERNET_CHILD_LOOPBACK_DENIED_BY_OS=PASS' \
  'P20_REAL_DSH_NODE_PROCESS_MIGRATED=NO' \
  'P20_ARM64_NODE_EXECUTION_ON_X86_64_EMULATOR=NOT_TESTED'; do
  if ! grep -Fq "$marker" out/p20-probe-log-local.txt; then
    echo "::error::P20 missing required isolated UID security proof: $marker"
    grep 'P20_' out/p20-probe-log-local.txt | tail -n 25 || true
    exit 1
  fi
done
if grep -Eq 'P20_[A-Z_]+=(FAIL|UNKNOWN)' out/p20-probe-log-local.txt; then
  echo '::error::P20 unexpectedly failed/unknown boundary'
  exit 1
fi
echo 'P20_HOST_UID_INTERNET_POSITIVE_CONTROL=PASS' >> "$GITHUB_STEP_SUMMARY"
echo 'P20_ISOLATED_UID_PRIVATE_CANARY_UNREADABLE=PASS_ANDROID35' >> "$GITHUB_STEP_SUMMARY"
echo 'P20_CHILD_LOOPBACK_DENIED_BY_OS=PASS_ANDROID35' >> "$GITHUB_STEP_SUMMARY"
echo 'P20_REAL_ARM64_NODE_ISOLATED_EXECUTION=NOT_TESTED' >> "$GITHUB_STEP_SUMMARY"
echo 'P20_PRODUCTION_DSH_PRIVILEGE_BOUNDARY=NOT_VERIFIED' >> "$GITHUB_STEP_SUMMARY"
