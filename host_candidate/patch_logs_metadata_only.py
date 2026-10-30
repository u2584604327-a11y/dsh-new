#!/usr/bin/env python3
"""P11 Node-model logs tool summary-only boundary, not same-UID isolation."""
import argparse,copy,io,json,pathlib,zipfile
from patch_logs_export_output import patch as patch_p7,sha

def patch(original):
    p7,js=patch_p7(original)
    entry="async execute(args) {"
    needle="const action = args?.action ?? 'summary';"
    if js.count(entry)!=1:raise ValueError("NON_UNIQUE_EXECUTE")
    begin=js.index(entry)+len(entry)
    rest=js[begin:]
    if rest.count(needle)!=1:raise ValueError("NON_UNIQUE_ACTION")
    policy="""
            // P11: raw log lines, crash files and ZIPs are NOT granted to AI.
            // No command is sent to the native mailbox for these actions.
            if (action !== 'summary') {
                return {ok:false,message:'日志全文、崩溃现场和诊断包导出均须可信原生授权；AI 仅可查看统计计数。'};
            }
            const native = await sendCommand(home, ++seq, {action:'summary'});
            if (native?.ok !== true) {
                return {ok:false,message:'原生日志统计不可用；未转发原生错误详情。'};
            }
            const raw = native.counts && typeof native.counts === 'object'
                && !Array.isArray(native.counts) ? native.counts : {};
            const count = (key) => Number.isSafeInteger(raw[key])
                && raw[key] >= 0 && raw[key] <= 10000000 ? raw[key] : 0;
            return {ok:true,headline:'仅显示脱敏统计计数；未读取日志全文',
                counts:{total:count('total'),warn:count('warn'),error:count('error'),
                    crash:count('crash'),pending:count('pending'),
                    scope:'总数/警告/错误为本次运行；现场与待处理为跨会话累计'},
                message:'未检索到错误不等于错误从未出现。'};
"""
    at=rest.index(needle)+len(needle)
    js=js[:begin]+rest[:at]+policy+rest[at:]
    start=js.index("const DESCRIPTION = "+chr(96))
    end=js.index(chr(96)+";",start)+2
    js=js[:start]+("const DESCRIPTION = 'Only summary: bounded numeric diagnostic "
            "counts. Raw logs, crashes, diagnostic bundles, private paths and "
            "native error strings are not accessible via this tool. This is "
            "not an OS filesystem isolation boundary.';")+js[end:]
    old="enum: ['summary', 'read', 'crashes', 'export'],"
    if js.count(old)!=1:raise ValueError("ACTION_SCHEMA_PREIMAGE_MISMATCH")
    js=js.replace(old,"enum: ['summary'],",1)
    out=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(p7)) as z,zipfile.ZipFile(out,'w') as dst:
        if z.testzip():raise ValueError("P7_CRC_FAIL")
        if set(z.namelist())!={'package.json','lib/index.js'}:
            raise ValueError("P7_ENTRY_SCOPE_CHANGED")
        for entry in z.infolist():
            dst.writestr(copy.copy(entry),js.encode()
                         if entry.filename=='lib/index.js' else z.read(entry.filename))
    result=out.getvalue()
    with zipfile.ZipFile(io.BytesIO(result)) as z:
        if z.testzip():raise ValueError("P11_CRC_FAIL")
    return result,js

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument("original_zip")
    p.add_argument("--output",required=True);p.add_argument("--extract-js",required=True)
    a=p.parse_args()
    original=pathlib.Path(a.original_zip).read_bytes()
    blob,js=patch(original)
    pathlib.Path(a.output).write_bytes(blob)
    pathlib.Path(a.extract_js).write_text(js,encoding='utf-8')
    print(json.dumps({"P11_ZIP_SHA256":sha(blob),
        "P11_ORIGINAL_SHA256":sha(original),"AI_LOGS_TOOL":"SUMMARY_ONLY",
        "RAW_LOG_CRASH_EXPORT_MAILBOX_COMMANDS":"DENIED_BY_TOOL",
        "NATIVE_SUMMARY_OUTPUT":"WHITELISTED_COUNTS_ONLY",
        "SAME_UID_GENERIC_NODE_ACCESS":"NOT_BLOCKED",
        "ANDROID_RUNTIME":"NOT_VERIFIED","PRODUCTION_SIGNED_APK":"NO"},indent=2))
