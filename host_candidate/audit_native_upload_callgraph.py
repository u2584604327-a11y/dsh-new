#!/usr/bin/env python3
"""Read-only, bounded APK native upload graph audit. Does NOT patch or ship an APK.

Input must match an independently verified v138 APK. Emits *method-level* metadata
only, never arbitrary DEX strings, file contents, network secrets or logs.
Direct DEX invokes are informative but cannot prove reflection, JNI or Node egress.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, re, zipfile

from androguard.core.dex import DEX

EXPECTED_APK = "3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
APPLICATION_PREFIX = "Lcom/dsh/android/"
SENSITIVE_CLASSES = (
    "Lcom/dsh/android/log/LogUploader;",
    "Lcom/dsh/android/LogViewerActivity;",
    "Lcom/dsh/android/LogCommandBridge;",
    "Lcom/dsh/android/DshApplication;",
)
NETWORK_HINTS = (
    "Ljava/net/HttpURLConnection;",
    "Ljava/net/HttpsURLConnection;",
    "Ljavax/net/ssl/HttpsURLConnection;",
    "Ljava/net/URL;",
    "Lokhttp3/Call;",
    "Lokhttp3/OkHttpClient;",
    "Lokhttp3/RealCall;",
    "Lokhttp3/RequestBody;",
    "Lcom/squareup/okhttp/",
)
INVOKE_TARGET = re.compile(r"(L[^\s,;]+;)->([^\s(,]+)\(([^)]*)\)")
MAX_EDGE_COUNT = 500000


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def method_id(method):
    # DexMethod.get_descriptor() includes the return type; invoke textual output
    # from androguard lists the name and arguments only. Canonicalize both
    # to the same class + method + argument descriptor key.
    args = method.get_descriptor().split(")", 1)[0] + ")"
    return method.get_class_name() + "->" + method.get_name() + args


def audit(apk_path):
    if file_sha256(apk_path) != EXPECTED_APK:
        raise ValueError("UNVERIFIED_V138_BASELINE")
    with zipfile.ZipFile(apk_path) as apk:
        if apk.testzip() is not None:
            raise ValueError("APK_CRC_FAILED")
        dex_files = sorted((name for name in apk.namelist()
                            if re.fullmatch(r"classes(?:[2-9][0-9]*)?\.dex",name)),
                           key=lambda name: (len(name), name))
        if "classes.dex" not in dex_files:
            raise ValueError("PRIMARY_DEX_ABSENT")
        raw_dex = [(name,apk.read(name)) for name in dex_files]
    edges = set()
    callers_by_callee = collections.defaultdict(set)
    network_sites = []
    inspected = 0
    app_methods = set()
    targets = {}
    unexplained_invokes = []
    for dex_name, raw in raw_dex:
        dex = DEX(raw)
        for cls in dex.get_classes():
            class_name = cls.get_name()
            if not class_name.startswith(APPLICATION_PREFIX):
                continue
            for method in cls.get_methods():
                code = method.get_code()
                if not code:
                    continue
                origin = method_id(method)
                app_methods.add(origin)
                inspected += 1
                if class_name in SENSITIVE_CLASSES:
                    targets[origin] = {
                        "class": class_name, "name": method.get_name(),
                        "dex": dex_name, "code_off": method.get_code_off(),
                        "insns_size": code.get_insns_size()
                    }
                for position, instruction in method.get_instructions_idx():
                    op_name = instruction.get_name()
                    if not op_name.startswith("invoke-"):
                        continue
                    match = INVOKE_TARGET.search(instruction.get_output())
                    if not match:
                        if len(unexplained_invokes)<25:
                            unexplained_invokes.append({"caller":origin,"opcode":op_name})
                        continue
                    callee_cls, callee_name, _ = match.groups()
                    callee = match.group(0)
                    if callee_cls.startswith(APPLICATION_PREFIX):
                        edges.add((origin, callee))
                        callers_by_callee[callee].add(origin)
                    if any(callee_cls.startswith(prefix) for prefix in NETWORK_HINTS):
                        network_sites.append({
                            "caller":origin,"dex":dex_name,
                            "pc":position,"callee":callee,
                        })
                    if len(edges)+len(network_sites) > MAX_EDGE_COUNT:
                        raise ValueError("CALL_GRAPH_BOUND_EXCEEDED")
    uploader_targets = sorted(key for key in targets
                              if key.startswith("Lcom/dsh/android/log/LogUploader;->"))
    summaries = []
    for target in uploader_targets:
        callers = sorted(callers_by_callee.get(target, []))
        summaries.append({
            "method": target, "direct_caller_count":len(callers),
            "direct_callers":callers[:100],
            "callers_truncated":len(callers)>100,
            "has_code":True,
        })
    native_send = [site for site in network_sites
                   if any(x in site["caller"] for x in ("LogUploader;", "LogViewerActivity;", "LogCommandBridge;", "DshApplication;"))]
    # No complete guarantee: dynamic reflection and native code are outside this scan.
    return {
        "status":"STATIC_CALL_GRAPH_REVIEW_ONLY",
        "baseline_sha256":EXPECTED_APK,
        "dex_files": [{"name":n,"sha256":hashlib.sha256(raw).hexdigest()}
                      for n,raw in raw_dex],
        "app_methods_scanned":inspected,
        "direct_app_invocation_pairs":len(edges),
        "relevant_native_method_count":len(targets),
        "log_uploader_methods":summaries,
        "direct_network_invocation_sites_for_selected_classes":native_send[:100],
        "network_invocations_among_app_classes":len(network_sites),
        "network_invocation_sites_sample":network_sites[:120],
        "unresolved_invoke_count_sample":len(unexplained_invokes),
        "unresolved_invoke_examples":unexplained_invokes,
        "scope_warning":"Invokes only. No dynamic reflection, JNI, third-party Java, or Node transport evidence.",
        "NATIVE_AND_NODE_TOTAL_EGRESS_CLOSED":"NOT_VERIFIED",
        "P5_NATIVE_SEND_GATE_CONNECTED":"NO",
        "APK_BUILT":"NO",
        "APK_SIGNED":"NO",
        "ART_VERIFIED":"NO",
    }


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("v138_apk")
    parser.add_argument("--report",default="native-upload-callgraph.json")
    args=parser.parse_args()
    report=audit(args.v138_apk)
    pathlib.Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":report["status"],
        "app_methods_scanned":report["app_methods_scanned"],
        "direct_app_invocation_pairs":report["direct_app_invocation_pairs"],
        "uploader_methods":len(report["log_uploader_methods"]),
        "network_invocations":report["network_invocations_among_app_classes"],
        "uploader_callers":[
            {"method":r["method"],"callers":r["direct_callers"][:12],"total_callers":r["direct_caller_count"]}
            for r in report["log_uploader_methods"] if r["direct_caller_count"]
        ],
        "selected_native_network_invocations":report["direct_network_invocation_sites_for_selected_classes"][:30],
        "unresolved_invoke_count_sample":report["unresolved_invoke_count_sample"],
        "unresolved_invoke_examples":report["unresolved_invoke_examples"][:5],
        "report":args.report,
        "full_egress_closed":"NOT_VERIFIED",
    },indent=2))
