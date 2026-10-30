#!/usr/bin/env bash
set -euo pipefail
adb install --no-streaming out/p26-disposable.apk
adb logcat -c
adb shell am start -n com.dsh.p26.multilib/.P26Activity
found=0
for attempt in $(seq 1 32);do
  adb logcat -d -s DSH_P26_SONAME:I '*:S' > out/p26-local-log.txt
  if grep -Fq 'P26_RESULT_REPORTED=YES' out/p26-local-log.txt;then
    found=1
    break
  fi
  sleep 1
done
if test "$found" -ne 1;then
  echo '::error::P26 isolated process experiment did not return'
  grep 'P26_' out/p26-local-log.txt | tail -n 28 || true
  exit 1
fi
for marker in \
  'P26_BINDER_ISOLATED_UID=PASS' \
  'P26_EXTRACTED_THREE_NATIVE_LIBRARIES=PASS' \
  'P26_NEGATIVE_MISSING_TOP_SONAME=PASS' \
  'P26_TWO_PRELOADS_AND_MISSING_SONAME_SQLITE_EXEC_UID=PASS' \
  'P26_ORIGINAL_ARM64_NODE_EXECUTED=NO' \
  'P26_ORIGINAL_DSH_MIGRATED=NO';do
  if ! grep -Fq "$marker" out/p26-local-log.txt;then
    echo "::error::P26 real isolated UID SONAME experiment missing $marker"
    grep 'P26_' out/p26-local-log.txt | tail -n 25 || true
    exit 1
  fi
done
if grep -Eq 'P26_[A-Z_]+=(FAIL|UNKNOWN)' out/p26-local-log.txt;then
  echo '::error::P26 contains FAIL or UNKNOWN'
  grep 'P26_' out/p26-local-log.txt | tail -n 25 || true
  exit 1
fi
echo 'P26_REAL_ANDROID35_EXTRACTED_3_LIBRARY_FILES=PASS' >> "$GITHUB_STEP_SUMMARY"
echo 'P26_REAL_ANDROID35_NO_PRELOAD_TOP_NEEDED_MISSING=PASS_NEGATIVE_CONTROL' >> "$GITHUB_STEP_SUMMARY"
echo 'P26_REAL_ANDROID35_2_VERSIONED_PRELOAD_WITH_NO_SONAME_EXEC=PASS_POSITIVE_CONTROL' >> "$GITHUB_STEP_SUMMARY"
echo 'P26_REAL_ANDROID35_CHILD_ISOLATED_UID=PASS' >> "$GITHUB_STEP_SUMMARY"
echo 'P26_ACTUAL_ORIGINAL_ARM64_NODE_BOOT=NOT_TESTED' >> "$GITHUB_STEP_SUMMARY"
