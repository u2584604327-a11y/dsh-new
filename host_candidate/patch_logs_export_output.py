#!/usr/bin/env python3
"""P7 logs-tool return-value hardening: exact original ZIP and JS SHA only.
The original ZIP is native-created; this only redacts AI-visible tool output.
Not Node UID isolation, mailbox isolation, or general attachment egress control.
"""
import argparse,copy,hashlib,io,json,pathlib,zipfile
ORIGINAL_ZIP_SHA="3e6f281da126b2483d812c11297dd27d41787c29bbe3583221697749c39ff01a"
ORIGINAL_JS_SHA="35a8eb56a1c33e93e97f726f5b8e7f3129f4a6db4220f8137838896d041aa546"
def sha(value):return hashlib.sha256(value).hexdigest()
def patch(original):
    if sha(original)!=ORIGINAL_ZIP_SHA:raise ValueError("UNVERIFIED_NATIVE_LOGS_PLUGIN_ARCHIVE")
    with zipfile.ZipFile(io.BytesIO(original)) as source:
        if source.testzip():raise ValueError("LOGS_TOOL_CRC_FAIL")
        if set(source.namelist())!={"package.json","lib/index.js"}:raise ValueError("UNEXPECTED_LOG_PLUGIN_CONTENTS")
        old=source.read("lib/index.js")
        if sha(old)!=ORIGINAL_JS_SHA:raise ValueError("UNEXPECTED_ORIGINAL_LOG_PLUGIN_JS")
        code=old.decode("utf-8")
        edits=[
          ("生成诊断包（zip），返回路径 —— 模型可据此让用户上传/发送",
           "生成本地诊断包（zip）；只返回已生成状态，不能在聊天内取得路径或发送诊断数据"),
          ("and return its path so the user can send it.",
           "and only report completion status. Do NOT reveal the native path or send the bundle in chat."),
          ("if (typeof value.bundlePath === 'string' && value.bundlePath !== '') {",
           "if (value.needsNativeReview === true) {"),
          ("lines.push(`诊断包已生成: ${value.bundlePath}`);",
           "lines.push('诊断包已在本地生成；必须在可信原生界面逐包预览，工具不会返回路径。');"),
          ("lines.push('可以请用户在设置页「运行日志与诊断」里点「上传给开发者」，或直接把该文件发出来。');",
           "lines.push('不得通过聊天附件直接发送诊断包；原生逐包审批与发送门禁尚未接通。');"),
          ("bundlePath: { type: 'string' },",
           "needsNativeReview: { type: 'boolean' },\n\t\t\t\t\tbundleBytes: { type: 'number' },"),
          ("// summary / export\n\t\t\treturn await sendCommand(home, ++seq, { action });",
           """// Export remains a native-local operation. The native mailbox reply may
            // contain bundlePath, message or nested details with secrets.
            // Never forward ANY untrusted export reply property to the AI.
            if (action === 'export') {
                const reply = await sendCommand(home, ++seq, { action });
                if (reply?.ok !== true) return {
                    ok: false, message: '无法确认诊断包导出成功，请在原生日志页面查看。'
                };
                const result = { ok: true, needsNativeReview: true,
                    message: '诊断包仅在本地生成；请在可信原生界面逐包审阅。当前聊天通道不能发送诊断包。' };
                if (Number.isSafeInteger(reply.bundleBytes) && reply.bundleBytes >= 0 &&
                    reply.bundleBytes <= 16 * 1024 * 1024) result.bundleBytes = reply.bundleBytes;
                return result;
            }
            // Preserve existing summary response behavior.
            return await sendCommand(home, ++seq, { action });""")
        ]
        for old_fragment,new_fragment in edits:
            if code.count(old_fragment)!=1:raise ValueError("PATCH_ANCHOR_NOT_UNIQUE_"+old_fragment[:35])
            code=code.replace(old_fragment,new_fragment,1)
        out=io.BytesIO()
        with zipfile.ZipFile(out,"w") as candidate:
            for entry in source.infolist():
                candidate.writestr(copy.copy(entry),code.encode("utf-8")
                                   if entry.filename=="lib/index.js"
                                   else source.read(entry.filename))
        result=out.getvalue()
        with zipfile.ZipFile(io.BytesIO(result)) as check:
            if check.testzip():raise ValueError("PATCHED_PLUGIN_CRC_FAIL")
            if check.read("package.json")!=source.read("package.json"):
                raise ValueError("PACKAGE_JSON_CHANGED")
        return result,code
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("original_zip")
    parser.add_argument("--output",required=True)
    parser.add_argument("--extract-js",required=True)
    args=parser.parse_args()
    blob,js=patch(pathlib.Path(args.original_zip).read_bytes())
    pathlib.Path(args.output).write_bytes(blob)
    pathlib.Path(args.extract_js).write_text(js,encoding="utf-8")
    print(json.dumps({
        "P7_NESTED_LOG_PLUGIN_ORIGINAL_SHA256":ORIGINAL_ZIP_SHA,
        "P7_NESTED_LOG_PLUGIN_PATCHED_SHA256":sha(blob),
        "P7_JAVASCRIPT_SHA256":sha(js.encode("utf-8")),
        "MODEL_VISIBLE_EXPORT_PATH":"REMOVED",
        "NATIVE_MAILBOX_PATH":"STILL_PRESENT",
        "NODE_SAME_UID_READ_ACCESS":"STILL_PRESENT",
        "GENERAL_ATTACHMENT_UPLOAD_CONTROL":"NOT_VERIFIED",
        "APK_BUILT":"NO"
    },indent=2))
