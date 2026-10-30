#!/usr/bin/env bash
set -euo pipefail
p6=.p79_private/DSH_V139_P6_NODE_CREDENTIAL_LOG_REDACTION_AND_ASSET_STAGING.zip
test -s "$p6"
python - "$p6" > .p79_private/mailbox-names.txt <<'PY'
import pathlib,re,sys
from host_candidate.p70_browser_mailbox.audit_native_browser_mailbox import get_files
cmd,res=get_files(pathlib.Path(sys.argv[1]).read_bytes())
for name in (cmd,res):
 if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}",name) or name in (".",".."):
  raise SystemExit("P79_P6_FILE_NAME_BOUNDARY_REVIEW_REQUIRED")
 print(name)
PY
cmd="$(sed -n '1p' .p79_private/mailbox-names.txt)"
res="$(sed -n '2p' .p79_private/mailbox-names.txt)"
test -n "$cmd" && test -n "$res" && test "$cmd" != "$res"
apk=.p43tmp/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk
test -s "$apk"
adb install -r "$apk" >/dev/null
adb shell am force-stop com.dsh.p51.isolatedprobe || true
adb logcat -c
adb shell am start -n com.dsh.p51.isolatedprobe/com.dsh.android.p43.P43ProbeActivity \
  --ez p79_mailbox true --es p79_cmd "$cmd" --es p79_res "$res" >/dev/null
for i in $(seq 1 65);do
 logs="$(adb logcat -d -v brief -s P79_BROWSER_MAILBOX:I '*:S')"
 if grep -Fq 'P79_REAL_ANDROID_FILE_MAILBOX_WEBVIEW_REPLY_CHAIN=PASS' <<< "$logs";then break;fi
 if grep -Fq '=FAIL' <<< "$logs";then echo 'P79_NATIVE_MAILBOX=FAIL';exit 1;fi
 sleep 2
done
logs="$(adb logcat -d -v brief -s P79_BROWSER_MAILBOX:I '*:S')"
for i in 0 1 2 3 4 5;do
 grep -Fq "P79_FILE_COMMAND_NATIVE_RESULT_STEP_$i=PASS" <<< "$logs"
done
grep -Fq 'P79_REAL_ANDROID_FILE_MAILBOX_WEBVIEW_REPLY_CHAIN=PASS' <<< "$logs"
grep -Fq 'P79_COMMENT_PUBLISHED=NO' <<< "$logs"
grep -Fq 'P79_ORIGINAL_DSH_MODEL_CONTINUATION=NOT_WIRED' <<< "$logs"
echo 'P79_PINNED_P6_FILE_NAMES_TO_NATIVE_MAILBOX=PASS'
echo 'P79_ANDROID35_REAL_WEBVIEW_NATIVE_FILE_REPLY=PASS'
echo 'P79_ORIGINAL_BROWSER_TO_MODEL_RESULT=NOT_WIRED'
echo 'P79_FIXED_SIGNED_V139=BLOCKED'
