#!/usr/bin/env bash
set -euo pipefail
p6=.p86_private/DSH_V139_P6_NODE_CREDENTIAL_LOG_REDACTION_AND_ASSET_STAGING.zip
test -s "$p6"
python - "$p6" > .p86_private/names <<'PY'
import pathlib,re,sys
from host_candidate.p70_browser_mailbox.audit_native_browser_mailbox import get_files
names=get_files(pathlib.Path(sys.argv[1]).read_bytes())
assert len(names)==2 and names[0]!=names[1]
for item in names:
 assert re.fullmatch(r"[A-Za-z0-9._-]{1,80}",item) and item not in (".","..")
 print(item)
PY
cmd="$(sed -n '1p' .p86_private/names)"
res="$(sed -n '2p' .p86_private/names)"
apk=.p43tmp/P43-ORIGINAL-DSH-EPHEMERAL-EMULATOR-ONLY.apk
test -s "$apk"
adb install -r "$apk" >/dev/null
adb shell am force-stop com.dsh.p51.isolatedprobe || true
adb logcat -c
adb shell am start -n com.dsh.p51.isolatedprobe/com.dsh.android.p43.P43ProbeActivity \
 --ez p86_external true --es p86_cmd "$cmd" --es p86_res "$res" >/dev/null
for i in $(seq 1 40);do
 lines="$(adb logcat -d -v tag -s P86_NATIVE_REPLY:I '*:S')"
 if grep -Fq 'P86_NATIVE_WEBVIEW_READY' <<< "$lines";then break;fi
 sleep 1
done
grep -Fq 'P86_NATIVE_WEBVIEW_READY' <<< "$lines"
node host_candidate/p86_node_android_relay/test_p86_node_android.mjs \
 .p86_private/p70-browser.js "$cmd" "$res"
lines="$(adb logcat -d -v tag -s P86_NATIVE_REPLY:I '*:S')"
test "$(grep -Ec 'P86_NATIVE_REPLY: p86[a-z0-9]+\|[01]\|[A-Z_]+' <<< "$lines")" -eq 6
grep -Fq 'P86_NATIVE_REPLY: p86postcomment01|0|NATIVE_USER_CONFIRMATION_REQUIRED' <<< "$lines"
echo 'P86_REAL_NODE_P6_TO_ANDROID35_WEBVIEW_WITH_TEST_RELAY=PASS'
echo 'P86_PRODUCTION_ANDROID_NODE_AND_ORIGINAL_MODEL=NOT_WIRED'
echo 'P86_FIXED_SIGNED_V139=BLOCKED'
