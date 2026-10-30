#!/usr/bin/env bash
set -euo pipefail
adb install --no-streaming out/p22-disposable.apk
adb logcat -c
adb shell am start -n com.dsh.p22.ziplink/.P22ProbeActivity
found=0
for attempt in $(seq 1 32); do
  adb logcat -d -s DSH_P22_ZIPLINK:I '*:S' > out/p22-local-log.txt
  if grep -Fq 'P22_DSH_PRODUCTION_RUNTIME_MIGRATED=NO' out/p22-local-log.txt; then
    found=1
    break
  fi
  sleep 1
done
if test "$found" -ne 1;then
 echo '::error::P22 isolated worker did not return; no dynamic linker result'
 grep 'P22_' out/p22-local-log.txt | tail -n 20 || true
 exit 1
fi
for expected in \
  'P22_BINDER_FRAMEWORK_ISOLATED_UID=PASS' \
  'P22_EXEC_PACKAGE_EXTRACTED_ELF=PASS' \
  'P22_EXEC_VERSIONED_SONAME_FROM_APK_ZIP=PASS' \
  'P22_REAL_ARM64_NODE_EXECUTED=NO' \
  'P22_DSH_PRODUCTION_RUNTIME_MIGRATED=NO'; do
 if ! grep -Fq "$expected" out/p22-local-log.txt;then
  echo "::error::P22 missing expected real test marker $expected"
  grep 'P22_' out/p22-local-log.txt | tail -n 25 || true
  exit 1
 fi
done
if grep -Eq 'P22_[A-Z_]+=(FAIL|UNKNOWN)' out/p22-local-log.txt;then
 echo '::error::P22 emulator linker proof contains FAIL/UNKNOWN'
 grep 'P22_' out/p22-local-log.txt | tail -n 25 || true
 exit 1
fi
echo 'P22_X86_64_ISOLATED_PROCESS_EXECVE=PASS_ANDROID35' >> "$GITHUB_STEP_SUMMARY"
echo 'P22_APK_ZIP_VERSIONED_SONAME_DYNAMIC_RESOLUTION=PASS_ANDROID35' >> "$GITHUB_STEP_SUMMARY"
echo 'P22_ORIGINAL_DSH_ARM64_NODE_EXECVE=NOT_TESTED' >> "$GITHUB_STEP_SUMMARY"
