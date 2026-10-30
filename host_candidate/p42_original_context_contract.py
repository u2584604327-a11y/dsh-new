#!/usr/bin/env python3
"""P42 exact-v138 host-to-isolated-service integration preflight.

Only safe categorical metadata, SDK ranges, and Java API call names. Do not
print APK strings, environment values, file paths, app credentials, source,
or host-private payloads. READ ONLY. Not an engine integration/release.
"""
import argparse
import collections
import json
import pathlib
import re
import zipfile
from androguard.core.apk import APK
from androguard.core.dex import DEX
from p35_original_engine_spawn_contract import EXPECTED, sha, inspect as inspect_p35

ANDROID = "{http://schemas.android.com/apk/res/android}"
TARGET_CLASS = "Lcom/dsh/android/EngineManager$start$2;"
ENGINE_CLASS = "Lcom/dsh/android/EngineManager;"
API = re.compile(r"(L[^\s,;]+;)->([^\s(,]+)\(([^)]*)\)")
SENSITIVE_PATH = re.compile(r"(?:/data/|/storage/|/sdcard/|key|token|secret|password)", re.I)
START = ("Ljava/lang/ProcessBuilder;", "start")
INTERESTING = {
    ("Ljava/lang/ProcessBuilder;", "command"): "BUILDER_COMMAND",
    ("Ljava/lang/ProcessBuilder;", "environment"): "BUILDER_ENVIRONMENT",
    ("Ljava/lang/ProcessBuilder;", "directory"): "BUILDER_DIRECTORY",
    ("Ljava/lang/ProcessBuilder;", "redirectErrorStream"): "BUILDER_ERROR_MERGE",
    ("Ljava/lang/ProcessBuilder;", "redirectInput"): "BUILDER_STDIN_REDIRECT",
    ("Ljava/lang/ProcessBuilder;", "redirectOutput"): "BUILDER_STDOUT_REDIRECT",
    ("Ljava/lang/ProcessBuilder;", "redirectError"): "BUILDER_STDERR_REDIRECT",
    ("Ljava/lang/ProcessBuilder;", "start"): "BUILDER_START",
    ("Ljava/lang/Process;", "getInputStream"): "PROCESS_STDOUT",
    ("Ljava/lang/Process;", "getErrorStream"): "PROCESS_STDERR",
    ("Ljava/lang/Process;", "getOutputStream"): "PROCESS_STDIN",
    ("Ljava/lang/Process;", "destroy"): "PROCESS_STOP",
    ("Ljava/lang/Process;", "destroyForcibly"): "PROCESS_KILL",
    ("Ljava/lang/Process;", "waitFor"): "PROCESS_WAIT",
    ("Ljava/lang/Process;", "isAlive"): "PROCESS_ALIVE",
    ("Ljava/lang/Process;", "exitValue"): "PROCESS_EXITVALUE",
    ("Ljava/io/OutputStream;", "write"): "STREAM_STDIN_WRITE",
}
def require(ok, code):
    if not ok:
        raise RuntimeError("P42_BLOCKED_" + code)

def manifest_snapshot(path):
    manifest = APK(str(path))
    tree = manifest.get_android_manifest_xml()
    require(tree is not None, "MANIFEST_UNREADABLE")
    app = tree.find("application")
    require(app is not None, "APPLICATION_MISSING")
    services = list(app.findall("service"))
    providers = list(app.findall("provider"))
    receivers = list(app.findall("receiver"))
    application_name = app.get(ANDROID + "name", "")
    return {
        "target_sdk": int(manifest.get_target_sdk_version() or 0),
        "min_sdk": int(manifest.get_min_sdk_version() or 0),
        "application_has_custom_class": bool(application_name),
        "application_class_is_under_dsh_namespace": application_name.startswith((
            "com.dsh.android.", "."
        )),
        "services_count": len(services),
        "isolated_services_count": sum(s.get(ANDROID+"isolatedProcess") == "true"
                                       for s in services),
        "exported_services_count": sum(s.get(ANDROID+"exported") == "true"
                                       for s in services),
        "providers_count": len(providers),
        "receivers_count": len(receivers),
        "extract_native_libs": app.get(ANDROID+"extractNativeLibs", "unspecified"),
        "android_permission_internet": any(s == "android.permission.INTERNET"
                                          for s in manifest.get_permissions()),
        "uses_cleartext_traffic": app.get(ANDROID+"usesCleartextTraffic", "unspecified"),
        "original_manifest_unchanged": True,
    }

def engine_surface(path):
    engine_methods = []
    methods = collections.Counter()
    builder_related = collections.Counter()
    stderr_merge_seen = 0
    with zipfile.ZipFile(path) as z:
        for name in sorted(n for n in z.namelist()
                           if re.fullmatch(r"classes(?:[2-9]\d*)?\.dex", n)):
            d = DEX(z.read(name))
            for cls in d.get_classes():
                if cls.get_name() not in (TARGET_CLASS, ENGINE_CLASS) and not (
                    cls.get_name().startswith("Lcom/dsh/android/EngineManager$")
                ):
                    continue
                for m in cls.get_methods():
                    if not m.get_code():
                        continue
                    method_name = m.get_name()
                    is_primary = (cls.get_name() == TARGET_CLASS and
                                  method_name == "invokeSuspend")
                    for pc, inst in m.get_instructions_idx():
                        if not inst.get_name().startswith("invoke-"):
                            continue
                        match = API.search(inst.get_output())
                        if match is None:
                            continue
                        key = (match.group(1), match.group(2))
                        kind = INTERESTING.get(key)
                        if kind:
                            methods[kind] += 1
                            if is_primary:
                                builder_related[kind] += 1
                            if kind == "BUILDER_ERROR_MERGE" and is_primary:
                                stderr_merge_seen += 1
                    engine_methods.append((cls.get_name(), method_name))
    assert engine_methods
    require(builder_related["BUILDER_START"] == 1, "PRIMARY_START_ANCHOR_MISSING")
    require(methods["BUILDER_START"] == 3, "OTHER_START_SITES_DRIFT")
    return {
        "original_engine_family_method_count": len(engine_methods),
        "original_engine_family_direct_api_counts": dict(sorted(methods.items())),
        "primary_launch_direct_api_counts": dict(sorted(builder_related.items())),
        "primary_stderr_redirection_config_invokes": stderr_merge_seen,
        "real_command_arguments_evaluated": False,
        "real_environment_values_evaluated": False,
        "android_process_context_acquisition": "NOT_IMPLEMENTED",
        "runtime_js_require_import_and_native_addons": "NOT_RESOLVED",
        "engine_stdin_indirect_and_dynamic_invocations": "NOT_PROVEN",
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("exact_signed_v138")
    p.add_argument("--report", required=True)
    args = p.parse_args()
    original = pathlib.Path(args.exact_signed_v138)
    require(sha(original) == EXPECTED, "EXACT_V138_SHA_MISMATCH")
    require(original.stat().st_size == 147341486, "EXACT_V138_SIZE_MISMATCH")
    p35 = inspect_p35(original)
    require(p35["primary_start_pc"] == 3912 and len(
        p35["post_spawn_required_lifecycle_api_edges"]) == 6,
        "P35_LIFECYCLE_ANCHORS_DRIFT")
    result = {
        "gate": "P42_EXACT_ORIGINAL_HOST_CONTEXT_AND_NODE_ENVELOPE",
        "exact_original_apk_sha256": EXPECTED,
        "manifest": manifest_snapshot(original),
        "engine": engine_surface(original),
        "original_engine_process_intercepted": False,
        "isolated_process_worker_in_original_apk": False,
        "original_app_binder_supervisor": False,
        "original_app_full_runtime_parity": "NOT_TESTED",
        "production_fixed_signing": "NOT_ATTEMPTED",
        "v139_release": "BLOCKED",
    }
    report = pathlib.Path(args.report)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    # Safe categorical subset only: report is ephemeral and never uploaded.
    print("P42_EXACT_ORIGINAL_SHA=PASS")
    print("P42_MANIFEST_CATEGORIES=" + json.dumps(result["manifest"],sort_keys=True))
    print("P42_PRIMARY_PROCESSBUILDER_API_COUNTS=" + json.dumps(
        result["engine"]["primary_launch_direct_api_counts"],sort_keys=True))
    print("P42_ENGINE_FAMILY_PROCESS_API_COUNTS=" + json.dumps(
        result["engine"]["original_engine_family_direct_api_counts"],sort_keys=True))
    print("P42_ORIGINAL_ENGINE_ISOLATION=NOT_IMPLEMENTED")
    print("P42_SIGNED_V139_RELEASE=BLOCKED")

if __name__ == "__main__":
    main()
