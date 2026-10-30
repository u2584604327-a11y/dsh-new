#!/usr/bin/env python3
"""P33 exact v138 DEX Android-native runtime invocation edge map.

Read-only: records method/class names and bounded direct call edges only.
Never outputs APK strings, tokens, URL/path literals or raw DEX/APK bytes.
Does not patch APK or assert that indirect/runtime Node call edges are complete.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import re
import zipfile

from loguru import logger
logger.disable("androguard")
from androguard.core.dex import DEX

V138_SHA = "3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
APP = "Lcom/dsh/android/"
INVOKE = re.compile(r"(L[^\s,;]+;)->([^\s(,]+)\(([^)]*)\)")
CATEGORIES = {
    "ACTIVITY_BOOT": re.compile(r"(?i)(MainActivity|DshApplication|Launcher|onCreate|onStart|onResume)"),
    "NODE_RUNTIME": re.compile(r"(?i)(node|runtime|engine|bootstrap|termux|server|process|mini.*server)"),
    "BRIDGE_TOOL": re.compile(r"(?i)(bridge|plugin|tool|api|provider|session|websocket)"),
    "WEBVIEW_BROWSER": re.compile(r"(?i)(webview|browser|javascript|websocket|webdriver)"),
    "DIAGNOSTIC": re.compile(r"(?i)(loguploader|logcommandbridge|diagnosticbundle|uploadpending)"),
}
# Exact invoked Java API names. No app strings or literal runtime file paths are emitted.
EXTERNAL_ANCHORS = {
    "PROCESS_START": (("Ljava/lang/ProcessBuilder;", ("start",)), ("Ljava/lang/Runtime;", ("exec",))),
    "NATIVE_LOAD": (("Ljava/lang/System;", ("load", "loadLibrary")), ("Ljava/lang/Runtime;", ("load", "loadLibrary"))),
    "WEBVIEW_BRIDGE": (("Landroid/webkit/WebView;", ("addJavascriptInterface", "evaluateJavascript", "loadUrl")),),
    "SERVICE_IPC": (("Landroid/content/Context;", ("bindService", "startService", "sendBroadcast")),
                    ("Landroid/content/ContextWrapper;", ("bindService", "startService", "sendBroadcast"))),
    "NATIVE_NETWORK": (("Ljava/net/Socket;", ("connect",)), ("Ljava/net/HttpURLConnection;", ("getOutputStream",))),
}
MAX_NATIVE_INVOKES = 300000
MAX_APP_EDGES = 150000


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def short_method(method):
    # Use full argument descriptor to distinguish overloads; keep bounded.
    args = method.get_descriptor().split(")", 1)[0] + ")"
    return method.get_class_name() + "->" + method.get_name() + args


def category_for(method_id):
    return [key for key, p in CATEGORIES.items() if p.search(method_id)]


def anchor_for(cls, name):
    return [category for category, rules in EXTERNAL_ANCHORS.items()
            if any(cls == c and name in methods for c, methods in rules)]


def analyze(path):
    if sha_file(path) != V138_SHA:
        raise ValueError("P33_V138_SOURCE_SHA_MISMATCH")
    with zipfile.ZipFile(path) as apk:
        if apk.testzip() is not None:
            raise ValueError("P33_ORIGINAL_APK_ZIP_CRC_FAIL")
        names = [n for n in apk.namelist()
                 if re.fullmatch(r"classes(?:[2-9][0-9]*)?\.dex", n)]
        if not names or "classes.dex" not in names:
            raise ValueError("P33_BASELINE_DEX_MISSING")
        blobs = {n: apk.read(n) for n in names}
    methods = set()
    app_edges = set()
    reverse = collections.defaultdict(set)
    anchors = []
    category_methods = collections.defaultdict(set)
    class_method_count = collections.Counter()
    selected = {}
    invokes = 0
    unparsed = 0
    oversized_method_ids = 0
    for dex_name, data in sorted(blobs.items()):
        dex = DEX(data)
        for klass in dex.get_classes():
            cls = klass.get_name()
            if not cls.startswith(APP):
                continue
            for meth in klass.get_methods():
                if meth.get_code() is None:
                    continue
                origin = short_method(meth)
                if len(origin) > 450:
                    oversized_method_ids += 1
                    # Valid generated Kotlin/Java signatures can be long.
                    # Keep only a safe, reproducible bounded identity:
                    # these generated callers may lose exact reverse joins.
                    origin = origin[:340] + "#sha256:" + hashlib.sha256(
                        origin.encode("utf-8")).hexdigest()[:20]
                methods.add(origin)
                class_method_count[cls] += 1
                for kind in category_for(origin):
                    category_methods[kind].add(origin)
                    if len(selected) < 550:
                        selected[origin] = {
                            "method": origin, "dex": dex_name,
                            "code_off": meth.get_code_off(),
                            "insn_count": meth.get_code().get_insns_size(),
                        }
                for pc, insn in meth.get_instructions_idx():
                    if not insn.get_name().startswith("invoke-"):
                        continue
                    invokes += 1
                    if invokes > MAX_NATIVE_INVOKES:
                        raise ValueError("P33_TOO_MANY_INVOKES")
                    parsed = INVOKE.search(insn.get_output())
                    if not parsed:
                        unparsed += 1
                        continue
                    target_cls, target_name, args = parsed.groups()
                    target = parsed.group(0)
                    if target_cls.startswith(APP):
                        app_edges.add((origin, target))
                        reverse[target].add(origin)
                        if len(app_edges) > MAX_APP_EDGES:
                            raise ValueError("P33_TOO_MANY_APP_EDGES")
                    for key in anchor_for(target_cls, target_name):
                        anchors.append({
                            "family": key,
                            "caller": origin,
                            "callee": target,
                            "dex": dex_name,
                            "pc": pc,
                            "code_off": meth.get_code_off(),
                        })
    anchors = sorted(anchors, key=lambda x:(x["family"], x["caller"], x["pc"]))
    by_family = collections.defaultdict(list)
    for a in anchors:
        by_family[a["family"]].append(a)
    # For each actual invoke anchor, find app direct callers and then their
    # direct callers. This is static reverse reachability, not execution proof.
    focus = [a for a in anchors
             if a["family"] in ("PROCESS_START", "NATIVE_LOAD", "WEBVIEW_BRIDGE", "SERVICE_IPC")]
    paths = []
    for a in focus:
        if len(paths) >= 100:
            break
        direct = sorted(reverse.get(a["caller"], []))
        preceding = sorted({c for p in direct for c in reverse.get(p, [])})
        paths.append({
            "family": a["family"], "sink_caller": a["caller"],
            "api": a["callee"], "dex": a["dex"],
            "code_off": a["code_off"], "pc": a["pc"],
            "direct_app_callers": direct[:12], "direct_caller_total": len(direct),
            "preceding_app_callers": preceding[:10],
            "preceding_total": len(preceding)
        })
    summary = {
        "status": "P33_READ_ONLY_EXACT_V138_STATIC_DEX_GRAPH",
        "exact_baseline_sha256": V138_SHA,
        "dex_files": [{"filename":n, "sha256":hashlib.sha256(b).hexdigest()}
                      for n,b in sorted(blobs.items())],
        "app_classes_with_code":len(class_method_count),
        "app_methods_with_code":len(methods),
        "app_to_app_direct_invokes":len(app_edges),
        "all_invocations_scanned":invokes,
        "unparsed_invokes_count":unparsed,
        "method_identifiers_over_450_hashed":oversized_method_ids,
        "category_counts":{k:len(v) for k,v in sorted(category_methods.items())},
        "candidate_classes": [
            {"class":c,"methods_with_code":n,
             "category_hits":[k for k,p in CATEGORIES.items() if p.search(c)]}
            for c,n in sorted(class_method_count.items())
            if any(p.search(c) for p in CATEGORIES.values())
        ][:180],
        "direct_api_anchor_counts":{key:len(by_family.get(key,[]))
                                    for key in sorted(EXTERNAL_ANCHORS)},
        "direct_api_anchor_samples":{key:xs[:30] for key,xs in sorted(by_family.items())},
        "two_hop_reverse_callsites":paths,
        "interesting_method_code_locations":list(selected.values())[:100],
        "original_node_runtime_isolated_uid": "PROVEN_ONLY_IN_SEPARATE_P31_DISPOSABLE_APP",
        "original_main_activity_and_runtime_invocation_hook": "UNVERIFIED",
        "reflection_jni_node_nested_js_dynamic_dispatch": "NOT_COVERED",
        "real_webview_tool_chat_api_streaming_integration": "NOT_VERIFIED",
        "all_privileged_diagnostic_egress_closed": "NOT_VERIFIED",
        "original_v138_apk_modified": False,
        "p33_v139_production_release": "BLOCKED",
    }
    if summary["app_methods_with_code"] < 2000:
        raise ValueError("P33_APP_CODE_GRAPH_SUSPICIOUSLY_SMALL")
    if summary["app_to_app_direct_invokes"] < 3000:
        raise ValueError("P33_APP_DIRECT_EDGE_GRAPH_SUSPICIOUSLY_SMALL")
    if sum(summary["direct_api_anchor_counts"].values()) < 2:
        raise ValueError("P33_KNOWN_PLATFORM_BOUNDARY_ANCHORS_ABSENT")
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("signed_v138_apk")
    p.add_argument("--report", required=True)
    a = p.parse_args()
    result = analyze(a.signed_v138_apk)
    pathlib.Path(a.report).write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "P33_ORIGINAL_BASELINE_SHA": "PASS",
        "P33_DEX_APP_METHODS": result["app_methods_with_code"],
        "P33_APP_DIRECT_EDGES": result["app_to_app_direct_invokes"],
        "P33_PLATFORM_BOUNDARY_ANCHORS": result["direct_api_anchor_counts"],
        "P33_REAL_PROCESS_START_CALLSITES": [
            {"caller":x["caller"],"target":x["callee"],
             "dex":x["dex"],"code_off":x["code_off"],"pc":x["pc"]}
            for x in result["direct_api_anchor_samples"].get("PROCESS_START", [])[:16]
        ],
        "P33_REAL_WEBVIEW_BRIDGE_CALLSITES": [
            {"caller":x["caller"],"target":x["callee"],
             "dex":x["dex"],"code_off":x["code_off"],"pc":x["pc"]}
            for x in result["direct_api_anchor_samples"].get("WEBVIEW_BRIDGE", [])[:16]
        ],
        "P33_NODE_STATIC_UPSTREAM_CALLERS": [
            {"sink_caller":x["sink_caller"],
             "direct_app_callers":x["direct_app_callers"][:6]}
            for x in result["two_hop_reverse_callsites"]
            if x["family"] == "PROCESS_START"
        ][:12],
        "P33_NATIVE_HOST_WIRING": "NOT_CONNECTED_STATIC_REVIEW_ONLY",
        "P33_EXTERNAL_REFLECTION_JNI_NODE_ASSET_DISPATCH": "NOT_COVERED",
        "P33_V139_RELEASE": "BLOCKED",
    }, indent=2))


if __name__ == "__main__":
    main()
