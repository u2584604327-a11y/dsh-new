#!/usr/bin/env bash
set -euo pipefail
adb install --no-streaming out/p24-disposable.apk
adb logcat -c
adb shell am start -n com.dsh.p24.preload/.P24Activity
found=0
for attempt in $(seq 1 32);do
  adb logcat -d -s DSH_P24_SONAME:I '*:S' > out/p24-local-log.txt
  if grep -Fq 'P24_RESULT_REPORTED=YES' out/p24-local-log.txt;then
    found=1
    break
  fi
  sleep 1
done
if test "$found" -ne 1;then
  echo '::error::P24 isolated process experiment did not return'
  grep 'P24_' out/p24-local-log.txt | tail -n 28 || true
  exit 1
fi
for marker in \
  'P24_BINDER_ISOLATED_UID=PASS' \
  'P24_EXTRACTED_UNVERSIONED_ALIAS=PASS' \
  'P24_NO_PRELOAD_VERSIONED_DEPENDENCY_MISSING=PASS' \
  'P24_PRELOAD_VERSIONED_SONAME_EXEC_AND_CHILD_UID=PASS' \
  'P24_ORIGINAL_ARM64_NODE_EXECUTED=NO' \
  'P24_ORIGINAL_DSH_MIGRATED=NO';do
  if ! grep -Fq "$marker" out/p24-local-log.txt;then
    echo "::error::P24 real isolated UID SONAME experiment missing $marker"
    grep 'P24_' out/p24-local-log.txt | tail -n 25 || true
    exit 1
  fi
done
if grep -Eq 'P24_[A-Z_]+=(FAIL|UNKNOWN)' out/p24-local-log.txt;then
  echo '::error::P24 contains FAIL or UNKNOWN'
  grep 'P24_' out/p24-local-log.txt | tail -n 25 || true
  exit 1
fi
echo 'P24_REAL_ANDROID35_EXTRACTED_ALIAS_FILENAME=PASS' >> "$GITHUB_STEP_SUMMARY"
echo 'P24_REAL_ANDROID35_NO_PRELOAD_VERSIONED_MISSING=PASS_NEGATIVE_CONTROL' >> "$GITHUB_STEP_SUMMARY"
echo 'P24_REAL_ANDROID35_PRELOAD_VERSIONED_SONAME_EXECVE=PASS_POSITIVE_CONTROL' >> "$GITHUB_STEP_SUMMARY"
echo 'P24_REAL_ANDROID35_CHILD_ISOLATED_UID=PASS' >> "$GITHUB_STEP_SUMMARY"
echo 'P24_ACTUAL_ORIGINAL_ARM64_NODE_BOOT=NOT_TESTED' >> "$GITHUB_STEP_SUMMARY"
