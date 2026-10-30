#!/usr/bin/env bash
set -euo pipefail
adb install --no-streaming out/p23-disposable.apk
adb logcat -c
adb shell am start -n com.dsh.p23.zipcontrol/.P23ControlActivity
found=0
for attempt in $(seq 1 32);do
  adb logcat -d -s DSH_P23_ZIP:I '*:S' > out/p23-local-log.txt
  if grep -Fq 'P23_DIAGNOSTIC_COMPLETED=YES' out/p23-local-log.txt;then
    found=1
    break
  fi
  sleep 1
done
if test "$found" -ne 1;then
  echo '::error::P23 isolated worker did not return diagnostic'
  grep 'P23_' out/p23-local-log.txt | tail -n 20 || true
  exit 1
fi
for required in \
  'P23_ISOLATED_BINDER_UID=PASS' \
  'P23_INSTALLED_APK_READABLE=PASS' \
  'P23_ALL_THREE_ENTRIES_READABLE=PASS' \
  'P23_NATIVE_BRIDGE_INSTALLED=PASS' \
  'P23_ORIGINAL_ARM64_DSH_NODE_EXECUTED=NO' \
  'P23_DSH_PRODUCTION_MIGRATION=NO';do
  if ! grep -Fq "$required" out/p23-local-log.txt;then
    echo "::error::P23 missing mandatory real control: $required"
    grep 'P23_' out/p23-local-log.txt | tail -n 25 || true
    exit 1
  fi
done
# PASS is about verified controls. Failed loader paths remain BLOCKED.
for kind in ASSET_PLAIN ASSET_VERSIONED NATIVE_VERSIONED;do
  line="$(grep -E 'P23_DLOPEN_'"$kind"'_CODE=-?[0-9]+$' out/p23-local-log.txt | tail -n 1 || true)"
  if test -z "$line";then
    echo "::error::P23 $kind never reported a JNI dlopen result"
    exit 1
  fi
  code="$(printf '%s\n' "$line" | sed -E 's/^.*_CODE=([-0-9]+)$/\1/')"
  case "$code" in
    -100|-10|-11|-12|-13)
      echo "::error::P23 $kind did not exercise a valid fixed JNI ZIP probe (code $code)"
      exit 1;;
  esac
  if test "$code" = "22035";then
    echo "P23_${kind}_REAL_BIONIC_DLOPEN=PASS_ANDROID35" | tee -a "$GITHUB_STEP_SUMMARY"
  else
    echo "P23_${kind}_REAL_BIONIC_DLOPEN=BLOCKED_ERROR_${code}" | tee -a "$GITHUB_STEP_SUMMARY"
  fi
done
echo 'P23_INSTALLED_APK_PATH_AND_ALL_NATIVE_BYTES=PASS_ANDROID35' | tee -a "$GITHUB_STEP_SUMMARY"
echo 'P23_REAL_ISOLATED_UID_AUTHENTICATION=PASS_ANDROID35' >> "$GITHUB_STEP_SUMMARY"
echo 'P23_ORIGINAL_DSH_ARM64_NODE_BOOT=NOT_TESTED' >> "$GITHUB_STEP_SUMMARY"
