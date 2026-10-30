#!/usr/bin/env python3
"""Source-locked evidence-only original v138 bubble send/JavaBridge method locator.

No model text, UI content, URLs, cookies, private literals, or original source
leaves the runner. Matching a log literal NEVER proves this is the live path.
"""
import argparse, collections, hashlib, json, pathlib, re, zipfile
SOURCE_SHA="3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
PHRASES={
    "气泡注入结果":"BUBBLE_INSERT_RESULT",
    "气泡发送结果":"BUBBLE_CLICK_RESULT",
    "气泡":"BUBBLE_GENERAL",
    "余额刷新":"BALANCE_REFRESH",
    "Shizuku":"PRIVILEGE_SHIZUKU",
    "主线程超过":"MAIN_STALL_WATCHDOG",
}
APIS={
    "WEBVIEW_EVAL_JS":("Landroid/webkit/WebView;->evaluateJavascript(",),
    "WEBVIEW_LOAD_URL":("Landroid/webkit/WebView;->loadUrl(",),
    "HANDLER_POST":("Landroid/os/Handler;->post(",),
    "LOGGING":("Landroid/util/Log;->",),
    "JSON_GET":("Lorg/json/JSONObject;->opt", "Lorg/json/JSONObject;->get"),
    "JS_INTERFACE":("Landroid/webkit/JavascriptInterface;",),
}
def sha(data): return hashlib.sha256(data).hexdigest()
def categories(s):
    found={kind for phrase,kind in PHRASES.items() if phrase in s}
    if "BUBBLE_GENERAL" in found and len(found)>1:found.discard("BUBBLE_GENERAL")
    return found
def api_categories(ins):
    result=collections.Counter()
    for name,prefixes in APIS.items():
        count=sum(1 for invoke in ins if any(prefix in invoke for prefix in prefixes))
        if count:result[name]=count
    return result
def audit(apk):
    from androguard.core.dex import DEX
    if sha(apk)!=SOURCE_SHA:raise ValueError("P90_UNPINNED_APK")
    result=[]
    with zipfile.ZipFile(__import__("io").BytesIO(apk)) as z:
        if z.testzip() is not None:raise ValueError("P90_BAD_ZIP_CRC")
        entries=[(n,z.read(n)) for n in z.namelist() if re.fullmatch(r"classes\d*\.dex",n)]
    if len(entries)!=2:raise ValueError("P90_UNEXPECTED_DEX_COUNT")
    for dexname,raw in entries:
        d=DEX(raw)
        for cls in d.get_classes():
            owner=cls.get_name()
            if not owner.startswith("Lcom/dsh/android/"):continue
            for m in cls.get_methods():
                if m.get_code() is None:continue
                labels=set()
                calls=[]
                for _,ins in m.get_instructions_idx():
                    if ins.get_name().startswith("const-string"):
                        try: labels.update(categories(str(d.get_cm_string(ins.get_ref_kind()))))
                        except (AttributeError,IndexError,TypeError,ValueError):pass
                    elif ins.get_name().startswith("invoke-"):
                        calls.append(ins.get_output())
                if not labels:continue
                key=owner+"::"+m.get_name()+m.get_descriptor()
                result.append({
                    "method_sha12":sha(key.encode())[:12],
                    "surface":"ANDROID_MAIN" if "MainActivity" in owner else
                              ("ANDROID_BRIDGE" if "Bridge" in owner else "OTHER_APP"),
                    "dex":"PRIMARY" if dexname=="classes.dex" else "SECONDARY",
                    "labels":sorted(labels),
                    "api_categories":dict(sorted(api_categories(calls).items())),
                })
    labels=collections.Counter(t for row in result for t in row["labels"])
    # Do not emit raw original strings/method names or runtime user content.
    return {
        "pinned_original_apk":True,
        "matching_method_count":len(result),
        "matched_log_family_counts":dict(sorted(labels.items())),
        "method_categories":sorted(result,key=lambda r:(r["labels"],r["method_sha12"]))[:60],
        "original_bubble_send_receipt_to_confirmed_chat_turn_proven":False,
        "original_main_stall_cause_proven":False,
    }
def selftest():
    assert categories("气泡发送结果: SENT")=={"BUBBLE_CLICK_RESULT"}
    assert categories("气泡注入结果: len=0")=={"BUBBLE_INSERT_RESULT"}
    assert categories("余额刷新(启动) 未登录")=={"BALANCE_REFRESH"}
    assert api_categories(["v1, Landroid/webkit/WebView;->evaluateJavascript(...)"])["WEBVIEW_EVAL_JS"]==1
    print("P90_SYNTHETIC_ORIGINAL_OWNER_CLASSIFIER=PASS")
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--original")
    parser.add_argument("--selftest",action="store_true")
    args=parser.parse_args()
    if args.selftest:selftest()
    else:
        if not args.original:parser.error("original pinned APK required")
        report=audit(pathlib.Path(args.original).read_bytes())
        print("P90_PINNED_ORIGINAL_LOG_OWNER_CATEGORIES="+json.dumps(report,sort_keys=True,ensure_ascii=True))
        print("P90_ORIGINAL_BUBBLE_SEND_SUCCESS_INTEGRATION=NOT_PROVEN")
