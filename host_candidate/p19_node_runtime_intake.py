#!/usr/bin/env python3
"""P19 exact v138 runtime intake. Static readelf only: NEVER execute APK binaries.

This does not prove Node isolation, VM authenticity, linker success, SELinux
acceptance, or native host migration. Only bounded binary metadata is emitted.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import zipfile

EXPECTED_APK_SHA = "3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
EXPECTED_NODE_ASSET_SHA = "ba16f7f4d0cc0b0272700effe06dc0d3682206afe1b54af75ca530a3e5c0d3bf"
EXPECTED_NODE_BIN_SHA = "a0d21a1589312919114b24a5cc520c30ab7f26f9985b3f0c643c153172ebd1e6"
EXPECTED_BOOTSTRAP_SHA = "b3739c14a2eb7421243b908e2fe2b9e54cbdf8477d210d09e8ac4452d864cad9"
ANDROID_PLATFORM_LIBS = frozenset({
    "libc.so", "libm.so", "libdl.so", "liblog.so", "libandroid.so"
})
MAX_ARCHIVE_MEMBER = 128 * 1024 * 1024
MAX_NODE_ZIP = 100 * 1024 * 1024

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def audited_members(data):
    if len(data) > MAX_NODE_ZIP:
        raise ValueError("NODE_ZIP_TOO_LARGE")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if len(names) > 64 or len(names) != len(set(names)):
            raise ValueError("UNEXPECTED_NODE_MEMBER_COUNT")
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts or item.file_size > MAX_ARCHIVE_MEMBER:
                raise ValueError("UNSAFE_NODE_MEMBER")
            if item.filename not in {"LINKS.txt", "bin/node"} and not item.filename.startswith("lib/"):
                raise ValueError("UNEXPECTED_NODE_MEMBER")
        if archive.testzip() is not None:
            raise ValueError("NODE_ZIP_CRC_FAIL")
        if "bin/node" not in names or "LINKS.txt" not in names:
            raise ValueError("NODE_OR_LINKS_MISSING")
        links = {}
        for line in archive.read("LINKS.txt").decode("ascii").splitlines():
            parts = line.split()
            if len(parts) != 2:
                raise ValueError("BAD_RUNTIME_LINKS")
            link, target = parts
            if not link.startswith("lib/") or "/" in target or target.startswith("."):
                raise ValueError("BAD_RUNTIME_LINK")
            if link in links:
                raise ValueError("DUPLICATE_RUNTIME_LINK")
            links[link] = "lib/" + target
        return names, links, archive.read("bin/node")

def readelf_metadata(binary):
    if binary[:4] != b"\x7fELF" or binary[4] != 2 or binary[5] != 1:
        raise ValueError("NOT_ELF64_LITTLE_ENDIAN")
    if int.from_bytes(binary[18:20], "little") != 183:
        raise ValueError("NODE_NOT_ARM64")
    with tempfile.TemporaryDirectory(prefix="p19-node-readelf-") as tmp:
        path = Path(tmp) / "opaque-runtime-elf"
        with path.open("wb") as out:
            out.write(binary)
        # Read-only parser, not execve, chmod, dlopen or runtime startup.
        result = subprocess.run(["readelf", "-l", "-d", str(path)],
                                capture_output=True, text=True,
                                timeout=30, check=True)
    output = result.stdout
    interp = re.search(r"Requesting program interpreter:\s*([^\]]+)\]", output)
    needed = sorted(set(re.findall(r"Shared library:\s*\[([^\]]+)\]", output)))
    runpaths = re.findall(r"Library (?:runpath|rpath):\s*\[([^\]]+)\]", output)
    if not interp or not needed:
        raise ValueError("MISSING_INTERPRETER_OR_DEPENDENCIES")
    return {
        "elf_machine": "AArch64",
        "elf_bits": 64,
        "interpreter": interp.group(1),
        "needed_libraries": needed,
        "runpaths": runpaths
    }

def analyze(apk_path):
    data = Path(apk_path).read_bytes()
    if digest(data) != EXPECTED_APK_SHA:
        raise ValueError("NOT_PINNED_V138")
    with zipfile.ZipFile(io.BytesIO(data)) as apk:
        node_asset = apk.read("assets/node-runtime.bin")
        bootstrap_asset = apk.read("assets/bootstrap-aarch64.zip")
        if digest(node_asset) != EXPECTED_NODE_ASSET_SHA:
            raise ValueError("NODE_ASSET_PREIMAGE_CHANGED")
        if digest(bootstrap_asset) != EXPECTED_BOOTSTRAP_SHA:
            raise ValueError("BOOTSTRAP_PREIMAGE_CHANGED")
    with zipfile.ZipFile(io.BytesIO(bootstrap_asset)) as bootstrap:
        if len(bootstrap.namelist()) > 5000 or bootstrap.testzip() is not None:
            raise ValueError("BOOTSTRAP_ARCHIVE_INVALID")
        bootstrap_names = set(bootstrap.namelist())
    names, links, node_binary = audited_members(node_asset)
    if digest(node_binary) != EXPECTED_NODE_BIN_SHA:
        raise ValueError("NODE_BINARY_PREIMAGE_CHANGED")
    elf = readelf_metadata(node_binary)
    available = set(names)
    combined = available | bootstrap_names
    link_targets_missing = sorted(link for link, dest in links.items() if dest not in available)
    link_targets_missing_combined = sorted(
        link for link, dest in links.items() if dest not in combined
    )
    def missing_needed(available_names):
        return sorted(name for name in elf["needed_libraries"]
            if name not in ANDROID_PLATFORM_LIBS
            and ("lib/" + name) not in available_names
            and ("lib/" + name not in links or links["lib/" + name] not in available_names))
    missing_node_zip = missing_needed(available)
    missing_combined = missing_needed(combined)
    termux_runpath = any("/data/data/com.termux/files/usr/lib" in rp for rp in elf["runpaths"])
    # Do not make a dynamic linker claim merely from a static dependency list.
    return {
        "p19_input_apk_sha256": EXPECTED_APK_SHA,
        "node_zip_sha256": EXPECTED_NODE_ASSET_SHA,
        "node_executable_sha256": EXPECTED_NODE_BIN_SHA,
        "bootstrap_zip_sha256": EXPECTED_BOOTSTRAP_SHA,
        "node_zip_entry_count": len(names),
        "node_zip_is_direct_elf": False,
        "node_binary": elf,
        "node_zip_unresolved_needed": missing_node_zip,
        "declared_link_targets_absent": link_targets_missing,
        "combined_bootstrap_node_unresolved_needed": missing_combined,
        "combined_declared_link_targets_absent": link_targets_missing_combined,
        "cross_asset_library_presence_proven": not missing_combined,
        "termux_absolute_runpath_present": termux_runpath,
        "isolated_uid_node_spawn_proven": False,
        "android_35_native_linker_success_proven": False,
        "original_dsh_node_host_migrated": False,
        "original_dsh_signer_used": False,
        "release_state": "BLOCKED_REAL_RUNTIME_MIGRATION_NOT_PROVEN"
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("apk")
    parser.add_argument("--output", required=True)
    parser.add_argument("--verify-known-baseline-blockers", action="store_true")
    args = parser.parse_args()
    report = analyze(args.apk)
    if args.verify_known_baseline_blockers:
        if not report["node_zip_unresolved_needed"] or not report["termux_absolute_runpath_present"]:
            raise ValueError("P19_BASELINE_CHANGED_OR_OBSERVED_BLOCKERS_MISSING")
        if report["combined_bootstrap_node_unresolved_needed"] or not report["cross_asset_library_presence_proven"]:
            raise ValueError("P19_CROSS_ASSET_DEPENDENCY_EXPECTATION_CHANGED")
        if report["isolated_uid_node_spawn_proven"]:
            raise ValueError("P19_FALSE_MIGRATION_PASS")
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    # Only fixed, non-private technical metadata; never print bundle contents.
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
