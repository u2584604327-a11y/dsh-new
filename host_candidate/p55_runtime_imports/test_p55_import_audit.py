#!/usr/bin/env python3
"""P55 safety/integrity tests: synthetic files only, no user/original source."""
import io
import json
import pathlib
import sys
import tarfile
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from p55_exact_original_import_audit import (
    audit_tar, normalize_import, normalize_entry, parse_package, candidate_values, scan_original_apk_js_assets
)

test_count = 0

def verify(cond, why):
    global test_count
    test_count += 1
    if not cond:
        raise AssertionError("P55_FAIL_" + why)

def archive(files):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w") as tar:
        for name, blob in files:
            t = tarfile.TarInfo(name)
            t.size = len(blob)
            tar.addfile(t, io.BytesIO(blob))
    out.seek(0)
    return out

def scan(files):
    with tarfile.open(fileobj=archive(files), mode="r|") as tar:
        return audit_tar(tar)

files = [
    ("engine/package.json", json.dumps({
        "name": "synthetic", "main": "./main.js", "scripts": {"start": "node main.js"},
        "optionalDependencies": {"synthetic-addon": "1.0"}
    }).encode()),
    ("engine/main.js", (
        "import sub from './lib/sub.js';\n"
        "const binding = require('./addon.node');\n"
        "const maybe = process.platform === 'android';\n"
        "require(dynamicVariable);\n"
        "import(dynamicName);\n"
        "const b = 'binding.node';\n"
    ).encode()),
    ("engine/lib/sub.js", b"module.exports = 1;"),
    ("engine/addon.node", b"not-really-native-a-synthetic"),
]
r = scan(files)
verify(r["archive_members_seen"] == 4, "member_count")
verify(r["js_sources_scanned"] == 2, "source_count")
verify(r["non_dependency_js_members"] == 2, "non_dependency_js_scan")
verify(r["non_dependency_conventional_name_main"] == 1, "main_hint_count")
verify(r["node_modules_js_members"] == 0, "no_node_modules_in_fixture")
verify(r["package_json_members"] == 1, "package_count")
verify(r["root_start_command_present"] == 1, "start_metadata")
verify(r["root_metadata_entrypoint_hints"] == 1, "one_entry")
verify(r["root_metadata_entrypoint_literal_exists"] == 1, "entry_resolves")
verify(r["relative_literal_imports_detected"] == 2, "static_literals")
verify(r["relative_literal_present_path_hint"] == 2, "relative_modules")
verify(r["direct_static_native_addon_imports_present"] == 1, "native_addon_found")
verify(r["native_addon_string_hints"] >= 1, "literal_native_mention")
verify(r["conditional_platform_references"] == 1, "platform_guard")
verify(r["dynamic_require_unresolved_hints"] >= 1, "nonliteral_require")
verify(r["dynamic_import_unresolved_hints"] >= 1, "nonliteral_import")
verify(r["optional_dependency_metadata_keys"] == 1, "optional_dep_count")
verify(normalize_import("engine/main.js", "../outside.js") == "outside.js",
       "lexical_relative_path_not_emitted")
verify(normalize_import("engine/main.js", "../../../escape.js") is None,
       "escape_root_rejected")
try:
    parse_package(b'{"main":"x","main":"y"}')
except ValueError as error:
    verify("P55_DUPLICATE_PACKAGE_JSON_KEY" in str(error), "duplicate_keys")
else:
    raise AssertionError("duplicate package keys were accepted")
verify(parse_package(b'\xff\xfe') is None, "invalid_unicode_bounded")
verify(candidate_values({"main":"./main.js"}) == [("main","./main.js")],
       "literal_main_candidate")
try:
    scan([("engine/../escape.js", b"test")])
except ValueError as error:
    verify("P54_BLOCKED_" in str(error), "unsafe_tar_name")
else:
    raise AssertionError("unsafe path accepted")
try:
    scan([files[0], files[0]])
except ValueError as error:
    verify("P55_BLOCKED_" in str(error), "duplicate_tar_member")
else:
    raise AssertionError("duplicate archive member accepted")
verify(normalize_entry("deep/app/package.json", "lib/server.js") ==
       "deep/app/lib/server.js", "bare package main resolved inside package")
verify(normalize_entry("deep/app/package.json", "node --eval 'bad'") is None,
       "scripts are never interpreted as file path")
deep = scan([
    ("many/deep/levels/engine/package.json",
     b'{"main":"lib/server.js","scripts":{"start":"node lib/server.js"}}'),
    ("many/deep/levels/engine/lib/server.js", b"module.exports = 0;")
])
verify(deep["minimum_non_dependency_package_depth"] == 4,
       "deep root metadata relative depth")
verify(deep["root_metadata_entrypoint_literal_exists"] == 1,
       "deep start path exists")
asset_bytes = io.BytesIO()
with zipfile.ZipFile(asset_bytes, "w") as z:
    z.writestr("assets/boot.js",
      "const x = require('./side.js'); const y='engine.bin';"
      "const z='node_modules'; process.argv;"
      "createServer(()=>{});")
    z.writestr("assets/side.js", "module.exports=1;")
asset_bytes.seek(0)
with zipfile.ZipFile(asset_bytes) as z:
    asset_shape = scan_original_apk_js_assets(z)
verify(asset_shape["apk_js_source_examined"] == 2,
       "apk JS scan only permitted source")
verify(asset_shape["apk_js_import_targets_present_inside_apk"] == 1,
       "apk import relative from actual asset directory")
verify(asset_shape["apk_js_source_containing_node_modules"] == 1,
       "only aggregate Node modules string count")
verify(asset_shape["apk_js_source_containing_engine_bin"] == 1,
       "aggregate engine gzip string count")
verify(asset_shape["apk_js_source_containing_argv_access"] == 1,
       "bounded argv access count")
print("P55_STATIC_STARTUP_AND_NATIVE_IMPORT_SYNTHETIC_TESTS=PASS assertions="+str(test_count))
print("P55_ORIGINAL_JS_FILE_NAMES_AND_CONTENTS_LEAKED=NO")
