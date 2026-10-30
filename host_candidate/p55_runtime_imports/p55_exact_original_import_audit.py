#!/usr/bin/env python3
"""P55: bounded, read-only static startup/import audit of immutable DSH engine.

This NEVER executes original JS, loads native addons, emits module names or
source, writes extracted source, or grants private paths to a worker.
All reported imports are *literal/static hints*, not Node resolution proof.
"""
import argparse
import collections
import gzip
import hashlib
import io
import json
import pathlib
import posixpath
import re
import sys
import tarfile
import zipfile

# The P54 trusted scanner lives in its own sibling directory.
# Fixed local source import only; never network/module search from the archive.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "p54_engine_tree"))
from p54_immutable_tar_audit import exact_engine, safe_name

EXPECTED_TREE_SHA = "b2c7e52890351c4d1a3200c67ccb9be6154389a20da0b0b590d16676ce47b1e1"
ENGINE_ENTRY = "assets/engine.bin"
MAX_JS_BYTES = 2 * 1024 * 1024
MAX_JSON_BYTES = 512 * 1024
MAX_TOTAL_SCANNED = 384 * 1024 * 1024
MAX_LITERAL_IMPORTS = 350000
MAX_PACKAGE_METADATA = 12000
MAX_FIELD = 280
RE_LITERAL_IMPORT = re.compile(
    r'(?:\brequire\s*\(\s*|\bimport\s*\(\s*|\bfrom\s+|\bimport\s+)'
    r'(["\x27])([^"\x27\r\n]{1,256})\1'
)
RE_DYN_REQUIRE = re.compile(
    r"\brequire\s*\(\s*(?![\"'])"
)
RE_DYN_IMPORT = re.compile(
    r"\bimport\s*\(\s*(?![\"'])"
)
RE_NODE_STRING = re.compile(r"[\"'][^\"'\r\n]{0,240}\.node[\"']")
RE_PLATFORM = re.compile(r"\bprocess\s*\.\s*(?:platform|arch)\b")
RE_NATIVE_LOADER = re.compile(
    r"\b(?:node-gyp-build|bindings|prebuildify|node-pre-gyp|"
    r"@napi-rs|process\.dlopen)\b", re.I
)
RE_LITERAL_DYNAMIC_NATIVE = re.compile(r"require\s*\(\s*[^\"'\s][^)]*\.node", re.I)


def require(ok, reason):
    if not ok:
        raise ValueError("P55_BLOCKED_" + reason)


def normalize_import(caller, spec):
    """Only a *lexical* relative resolution hint, not actual Node resolver."""
    if not isinstance(spec, str) or not spec.startswith(("./", "../")):
        return None
    if len(spec) > MAX_FIELD or "\\" in spec or "\x00" in spec:
        return None
    normalized = posixpath.normpath(posixpath.join(posixpath.dirname(caller), spec))
    if normalized.startswith("../") or normalized in (".", ".."):
        return None
    # Do not trust the original specifier for file opening; safe-name check.
    try:
        return safe_name(normalized)
    except ValueError:
        return None


def normalize_entry(caller, raw):
    """Metadata main/module/bin path hint (not an executable command)."""
    if not isinstance(raw, str) or not 0 < len(raw) <= MAX_FIELD:
        return None
    if not re.fullmatch(r"[A-Za-z0-9._/+\-]+", raw):
        return None
    if raw.startswith("/") or raw.startswith("-") or ":" in raw:
        return None
    return normalize_import(caller, raw if raw.startswith(("./", "../"))
                            else "./" + raw)


def parse_package(raw):
    """Safe JSON only; duplicate keys invalidate a root package definition."""
    def no_duplicates(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError("P55_DUPLICATE_PACKAGE_JSON_KEY")
            result[k] = v
        return result
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
    except (UnicodeError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def candidate_values(meta):
    """Bounded literal hints. Never interpret shell scripts as Node command."""
    vals = []
    for key in ("main", "module", "browser"):
        value = meta.get(key)
        if isinstance(value, str) and 0 < len(value) <= MAX_FIELD:
            vals.append((key, value))
    exports = meta.get("exports")
    if isinstance(exports, str) and 0 < len(exports) <= MAX_FIELD:
        vals.append(("exports", exports))
    elif isinstance(exports, dict):
        for key in (".", "default", "node", "import", "require"):
            v = exports.get(key)
            if isinstance(v, str) and 0 < len(v) <= MAX_FIELD:
                vals.append(("exports", v))
    bin_value = meta.get("bin")
    if isinstance(bin_value, str) and 0 < len(bin_value) <= MAX_FIELD:
        vals.append(("bin", bin_value))
    elif isinstance(bin_value, dict):
        for v in list(bin_value.values())[:10]:
            if isinstance(v, str) and 0 < len(v) <= MAX_FIELD:
                vals.append(("bin", v))
    return vals[:24]


def audit_tar(stream):
    present = set()
    addon_members = set()
    imports = []
    hinted_entries = []
    package_count = 0
    root_package_count = 0
    start_command_count = 0
    native_optional_dependency_count = 0
    potential_root_packages = []
    counts = collections.Counter()
    total = 0
    non_dependency_min_js_depth = None
    for entry in stream:
        name = safe_name(entry.name)
        require(name not in present, "DUPLICATE_MEMBER")
        present.add(name)
        if entry.isdir():
            continue
        require(entry.isfile(), "NON_FILE")
        if name.endswith(".node"):
            addon_members.add(name)
        is_js = name.endswith((".js", ".mjs", ".cjs"))
        is_pkg = name.endswith("/package.json") or name == "package.json"
        if is_js and "node_modules" not in name.split("/"):
            counts["non_dependency_js_members"] += 1
            depth = name.count("/")
            if non_dependency_min_js_depth is None or depth < non_dependency_min_js_depth:
                non_dependency_min_js_depth = depth
            # Only fixed conventional basename categories; never emit a name.
            basename = posixpath.basename(name).lower()
            if basename in ("index.js","main.js","server.js","app.js",
                            "bootstrap.js","boot.js","start.js","cli.js"):
                counts["non_dependency_conventional_name_" + basename[:-3]] += 1
        if is_js and "node_modules" in name.split("/"):
            counts["node_modules_js_members"] += 1
        if not (is_js or is_pkg):
            continue
        if is_pkg:
            package_count += 1
            require(package_count <= MAX_PACKAGE_METADATA, "PACKAGE_COUNT")
        limit = MAX_JS_BYTES if is_js else MAX_JSON_BYTES
        if entry.size > limit:
            counts["source_or_json_over_limit"] += 1
            continue
        total += entry.size
        require(total <= MAX_TOTAL_SCANNED, "SCAN_BYTES_LIMIT")
        inp = stream.extractfile(entry)
        require(inp is not None, "SOURCE_MEMBER_NOT_READABLE")
        # Small bounded buffer transiently in private CI; never print bytes.
        body = inp.read(limit + 1)
        require(len(body) == entry.size, "SHORT_SOURCE_READ")
        if is_pkg:
            meta = parse_package(body)
            if meta is None:
                counts["invalid_package_json"] += 1
                continue
            # Identify closest-to-root Node packages even with a deep
            # original TAR prefix; NEVER expose original package paths.
            if "node_modules" not in name.split("/"):
                entrypoints = []
                for kind, value in candidate_values(meta):
                    resolved = normalize_entry(name, value)
                    if resolved:
                        entrypoints.append((kind, resolved))
                start = meta.get("scripts")
                has_start = (isinstance(start, dict) and
                             isinstance(start.get("start"), str))
                potential_root_packages.append((
                    name.count("/"), entrypoints, has_start,
                    meta.get("type") == "module"))
            opt = meta.get("optionalDependencies")
            if isinstance(opt, dict):
                native_optional_dependency_count += len(opt)
            continue
        try:
            text = body.decode("utf-8")
        except UnicodeError:
            counts["non_utf8_js"] += 1
            continue
        counts["js_sources_scanned"] += 1
        counts["conditional_platform_references"] += len(RE_PLATFORM.findall(text))
        counts["native_loader_pattern_hints"] += len(RE_NATIVE_LOADER.findall(text))
        counts["dynamic_require_unresolved_hints"] += len(RE_DYN_REQUIRE.findall(text))
        counts["dynamic_import_unresolved_hints"] += len(RE_DYN_IMPORT.findall(text))
        counts["native_addon_string_hints"] += len(RE_NODE_STRING.findall(text))
        counts["nonliteral_native_import_hints"] += len(RE_LITERAL_DYNAMIC_NATIVE.findall(text))
        for match in RE_LITERAL_IMPORT.finditer(text):
            spec = match.group(2)
            counts["literal_import_syntax_occurrences"] += 1
            require(counts["literal_import_syntax_occurrences"] <= MAX_LITERAL_IMPORTS,
                    "LITERAL_IMPORT_COUNT_CAP")
            if spec.startswith(("node:",)):
                counts["builtin_node_specifier_hints"] += 1
            elif spec.startswith(("./", "../")):
                relative = normalize_import(name, spec)
                if relative is None:
                    counts["unresolvable_or_unsafe_relative_literal"] += 1
                else:
                    imports.append((relative, spec.endswith(".node")))
            else:
                counts["package_or_builtin_import_hints"] += 1
    counts["minimum_non_dependency_js_depth"] = (
        non_dependency_min_js_depth if non_dependency_min_js_depth is not None else -1)
    counts["non_dependency_package_metadata"] = len(potential_root_packages)
    counts["node_modules_package_metadata"] = (
        package_count - len(potential_root_packages))
    if potential_root_packages:
        mindepth = min(p[0] for p in potential_root_packages)
        counts["minimum_non_dependency_package_depth"] = mindepth
        # Shallowest two levels are candidates, NOT proven startup argv.
        for depth, entrypoints, has_start, module_type in potential_root_packages:
            if depth <= mindepth + 2:
                root_package_count += 1
                hinted_entries.extend(entrypoints)
                if has_start:
                    start_command_count += 1
                if module_type:
                    counts["root_type_module"] += 1
    else:
        counts["minimum_non_dependency_package_depth"] = -1
    direct_native = 0
    direct_native_miss = 0
    relative_present = 0
    relative_missing = 0
    for target, is_node in imports:
        guesses = (target, target + ".js", target + ".mjs", target + ".cjs",
                   target + ".json", target + "/index.js",
                   target + "/index.mjs", target + "/index.cjs")
        if any(g in present for g in guesses):
            relative_present += 1
        else:
            relative_missing += 1
        if is_node:
            if target in addon_members: direct_native += 1
            else: direct_native_miss += 1
    entry_exists = 0
    for kind, target in hinted_entries:
        guesses = (target, target + ".js", target + ".mjs",
                   target + ".cjs", target + "/index.js")
        if any(g in present for g in guesses):
            entry_exists += 1
    counts.update({
        "archive_members_seen": len(present),
        "native_addon_members": len(addon_members),
        "package_json_members": package_count,
        "rootish_package_metadata": root_package_count,
        "root_start_command_present": start_command_count,
        "optional_dependency_metadata_keys": native_optional_dependency_count,
        "relative_literal_imports_detected": len(imports),
        "relative_literal_present_path_hint": relative_present,
        "relative_literal_missing_path_hint": relative_missing,
        "direct_static_native_addon_imports_present": direct_native,
        "direct_static_native_addon_imports_missing": direct_native_miss,
        "root_metadata_entrypoint_hints": len(hinted_entries),
        "root_metadata_entrypoint_literal_exists": entry_exists,
        "candidate_source_bytes_examined": total,
    })
    return counts


def scan_original_apk_js_assets(z):
    """Aggregate-only shapes from APK JS assets, not proof of engine entry."""
    c = collections.Counter()
    members = [x for x in z.infolist()
               if x.filename.startswith("assets/")
               and x.filename.lower().endswith((".js", ".mjs", ".cjs"))
               and not x.is_dir()]
    require(len(members) <= 32, "TOO_MANY_APK_JS_ASSETS")
    known = set(z.namelist())
    for item in members:
        if item.file_size > MAX_JS_BYTES:
            c["apk_js_oversize"] += 1
            continue
        body = z.read(item)
        require(len(body) == item.file_size, "APK_JS_SHORT_READ")
        try:
            source = body.decode("utf-8")
        except UnicodeError:
            c["apk_js_not_utf8"] += 1
            continue
        c["apk_js_source_examined"] += 1
        c["apk_js_source_bytes_examined"] += len(body)
        c["apk_js_source_containing_node_modules"] += int(
            "node_modules" in source)
        c["apk_js_source_containing_engine_bin"] += int(
            "engine.bin" in source)
        c["apk_js_source_containing_runtime_bootstrap"] += int(
            "bootstrap" in source.lower())
        c["apk_js_source_containing_spawn_api"] += int(bool(re.search(
            r"\b(?:spawn|execFile|fork|ProcessBuilder)\s*\(", source)))
        c["apk_js_source_containing_http_server_api"] += int(bool(re.search(
            r"\b(?:createServer|\.listen|WebSocketServer)\s*\(", source)))
        c["apk_js_source_containing_argv_access"] += int(
            "process.argv" in source)
        c["apk_js_platform_condition_hints"] += len(RE_PLATFORM.findall(source))
        c["apk_js_native_loader_hints"] += len(RE_NATIVE_LOADER.findall(source))
        c["apk_js_native_addon_strings"] += len(RE_NODE_STRING.findall(source))
        for match in RE_LITERAL_IMPORT.finditer(source):
            c["apk_js_literal_imports"] += 1
            spec = match.group(2)
            if spec.startswith(("./", "../")):
                guess = normalize_import(item.filename, spec)
                if guess is not None and guess in known:
                    c["apk_js_import_targets_present_inside_apk"] += 1
                else:
                    c["apk_js_relative_imports_unresolved"] += 1
    return c


def run_exact_original(apk):
    # P54 full SHA/TAR audit is an independent prerequisite, not a shortcut.
    immutable = exact_engine(apk)
    require(immutable["tree_sha256"] == EXPECTED_TREE_SHA, "IMMUTABLE_TREE_DRIFT")
    require(immutable["members"] == 30411, "ARCHIVE_COUNT_DRIFT")
    with zipfile.ZipFile(apk) as z:
        all_assets = [i for i in z.infolist()
                      if i.filename.startswith("assets/") and not i.is_dir()
                      and i.filename != ENGINE_ENTRY]
        asset_counts = collections.Counter()
        for item in all_assets:
            name = item.filename.lower()
            if name.endswith((".js",".mjs",".cjs")):
                asset_counts["apk_asset_js_members"] += 1
            elif name.endswith(".json"):
                asset_counts["apk_asset_json_members"] += 1
            elif name.endswith(".sh"):
                asset_counts["apk_asset_shell_members"] += 1
            elif name.endswith(".zip"):
                asset_counts["apk_asset_zip_members"] += 1
        apk_asset_js_shapes = scan_original_apk_js_assets(z)
        encoded = z.read(ENGINE_ENTRY)
    with gzip.GzipFile(fileobj=io.BytesIO(encoded), mode="rb") as g:
        with tarfile.open(fileobj=g, mode="r|") as t:
            summary = audit_tar(t)
    require(summary["archive_members_seen"] == 30411,
            "SECOND_PASS_MEMBER_COUNT_CHANGED")
    require(summary["native_addon_members"] == 9, "ADDON_MEMBER_COUNT_CHANGED")
    summary.update(asset_counts)
    summary.update(apk_asset_js_shapes)
    return summary


def print_report(c):
    print("P55_EXACT_ORIGINAL_IMMUTABLE_TREE_ROOT=PASS")
    print("P55_STATIC_JS_IMPORT_SCAN=PASS_BOUNDED_HEURISTIC")
    keys = (
        "archive_members_seen", "js_sources_scanned",
        "non_dependency_js_members", "node_modules_js_members",
        "minimum_non_dependency_js_depth",
        "non_dependency_conventional_name_index",
        "non_dependency_conventional_name_main",
        "non_dependency_conventional_name_server",
        "non_dependency_conventional_name_app",
        "non_dependency_conventional_name_bootstrap",
        "non_dependency_conventional_name_boot",
        "non_dependency_conventional_name_start",
        "non_dependency_conventional_name_cli",
        "apk_asset_js_members", "apk_asset_json_members",
        "apk_asset_shell_members", "apk_asset_zip_members",
        "apk_js_source_examined", "apk_js_source_bytes_examined",
        "apk_js_oversize", "apk_js_not_utf8",
        "apk_js_source_containing_node_modules",
        "apk_js_source_containing_engine_bin",
        "apk_js_source_containing_runtime_bootstrap",
        "apk_js_source_containing_spawn_api",
        "apk_js_source_containing_http_server_api",
        "apk_js_source_containing_argv_access",
        "apk_js_platform_condition_hints",
        "apk_js_native_loader_hints",
        "apk_js_native_addon_strings", "apk_js_literal_imports",
        "apk_js_import_targets_present_inside_apk",
        "apk_js_relative_imports_unresolved",
        "source_or_json_over_limit", "candidate_source_bytes_examined",
        "package_json_members", "rootish_package_metadata",
        "non_dependency_package_metadata", "node_modules_package_metadata",
        "minimum_non_dependency_package_depth",
        "root_metadata_entrypoint_hints",
        "root_metadata_entrypoint_literal_exists",
        "root_start_command_present", "root_type_module",
        "optional_dependency_metadata_keys",
        "literal_import_syntax_occurrences",
        "relative_literal_imports_detected",
        "relative_literal_present_path_hint",
        "relative_literal_missing_path_hint",
        "package_or_builtin_import_hints", "builtin_node_specifier_hints",
        "conditional_platform_references",
        "native_loader_pattern_hints",
        "native_addon_string_hints", "nonliteral_native_import_hints",
        "dynamic_require_unresolved_hints",
        "dynamic_import_unresolved_hints",
        "direct_static_native_addon_imports_present",
        "direct_static_native_addon_imports_missing",
    )
    for k in keys:
        print("P55_" + k.upper() + "=" + str(c[k]))
    print("P55_LITERAL_IMPORTS_ARE_ONLY_LOWER_BOUND=YES")
    print("P55_DESKTOP_NATIVE_ADDONS_OPTIONAL_FOR_ANDROID=NOT_PROVEN")
    print("P55_PRODUCTION_ENTRYPOINT_RESOLVED=NO")
    print("P55_PRODUCTION_MODULE_GRAPH_CLOSED=NO")
    print("P55_PRODUCTION_NODE_RUNTIME_OR_SCRIPTS_EXECUTED=NO")
    print("P55_SOURCE_PATHS_OR_JS_CONTENT_EMITTED=NO")
    print("P55_DSH_ENGINEMANAGER_HANDOFF=NOT_IMPLEMENTED")
    print("P55_SIGNED_V139_APK=BLOCKED")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("signed_original_v138_apk")
    args = p.parse_args()
    print_report(run_exact_original(pathlib.Path(args.signed_original_v138_apk)))
