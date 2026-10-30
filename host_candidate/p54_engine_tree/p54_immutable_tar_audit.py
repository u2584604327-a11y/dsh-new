#!/usr/bin/env python3
"""P54 read-only content-hash inventory of the exact original DSH engine.tar.gz.

Never execute an ELF or JS, unpack a script to disk, expose member names or
source contents, or write a deployable manifest. Only opaque root digest and
aggregate metadata are emitted. An exact signed-v138 APK hash is required.
"""
import argparse
import collections
import gzip
import hashlib
import io
import os
import pathlib
import posixpath
import re
import subprocess
import tarfile
import zipfile

SOURCE_SHA = "3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
SOURCE_BYTES = 147341486
ENGINE_ENTRY = "assets/engine.bin"
EXPECTED_TAR_ENTRIES = 30411
EXPECTED_ADDONS = 9
MAX_COMPRESSED = 128 * 1024 * 1024
MAX_FILES = 100000
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_DECLARED_BYTES = 4 * 1024 * 1024 * 1024
MAX_ADDON_BYTES = 32 * 1024 * 1024
SAFE_SONAME = re.compile(r"[A-Za-z0-9_.+-]{1,96}\Z")
SHA = hashlib.sha256


def require(ok, code):
    if not ok:
        raise ValueError("P54_BLOCKED_" + code)


def file_sha(path):
    hasher = SHA()
    with open(path, "rb") as inp:
        for piece in iter(lambda: inp.read(1 << 20), b""):
            hasher.update(piece)
    return hasher.hexdigest()


def safe_name(name):
    require(isinstance(name, str) and 0 < len(name) <= 1024,
            "MISSING_OR_OVERSIZE_NAME")
    require(not name.startswith("/") and "\\" not in name and "\x00" not in name,
            "ABSOLUTE_OR_UNSAFE_SEPARATOR")
    require(not any(ord(c) < 32 or ord(c) == 127 for c in name),
            "CONTROL_CHARACTER_NAME")
    # A single leading './' is a common archive convention, not a grant to
    # resolve paths. All other traversal and alias spellings fail.
    if name.startswith("./"):
        name = name[2:]
    name = name.rstrip("/")
    require(bool(name), "ROOT_MEMBER_NOT_ALLOWED")
    parts = name.split("/")
    require(all(p not in ("", ".", "..") for p in parts),
            "UNCANONICAL_OR_TRAVERSAL")
    require(posixpath.normpath(name) == name, "NONCANONICAL_PATH")
    return name


def kind_of(name):
    lower = name.lower()
    if lower.endswith(".js"): return "js"
    if lower.endswith(".mjs"): return "mjs"
    if lower.endswith(".cjs"): return "cjs"
    if lower.endswith(".json"): return "json"
    if lower.endswith(".node"): return "native_addon"
    return "other_file"


def addon_metadata(blob):
    """Read-only dynamic-symbol metadata, via Linux anonymous memfd."""
    if not blob.startswith(b"\x7fELF") or len(blob) < 64:
        # Inspect only header magic; do not parse/execute PE or Mach-O.
        if len(blob) >= 2 and blob[:2] == b"MZ":
            subtype = "PE_MZ"
        elif len(blob) >= 4 and blob[:4] in (
                bytes([0xfe,0xed,0xfa,0xce]),
                bytes([0xce,0xfa,0xed,0xfe]),
                bytes([0xfe,0xed,0xfa,0xcf]),
                bytes([0xcf,0xfa,0xed,0xfe]),
                bytes([0xca,0xfe,0xba,0xbe]),
                bytes([0xbe,0xba,0xfe,0xca]),
                bytes([0xca,0xfe,0xba,0xbf]),
                bytes([0xbf,0xba,0xfe,0xca])):
            subtype = "MACHO_OR_FAT_MAGIC"
        elif len(blob) == 0: subtype = "empty"
        elif len(blob) <= 2048 and all(
                b in (9, 10, 13) or 32 <= b <= 126 for b in blob):
            subtype = "small_ascii"
        elif len(blob) <= 2048: subtype = "small_non_ascii"
        else: subtype = "unknown_binary_or_large"
        return {"kind": "NON_ELF", "needed": (),
                "machine": "unknown", "nonelf": subtype}
    require(blob[4] in (1, 2) and blob[5] == 1, "ADDON_ELF_CLASS_OR_ENDIAN")
    machine = int.from_bytes(blob[18:20], "little")
    machine_name = {183: "aarch64", 62: "x86_64", 40: "arm32",
                    3: "x86_32"}.get(machine, "other")
    require(len(blob) <= MAX_ADDON_BYTES, "ADDON_TOO_LARGE_FOR_MEMFD")
    require(hasattr(os, "memfd_create"), "MEMFD_UNAVAILABLE")
    fd = os.memfd_create("p54-transient-anonymous-addon")
    try:
        with os.fdopen(os.dup(fd), "wb") as f:
            f.write(blob)
        cmd = ["readelf", "-d", "/proc/self/fd/" + str(fd)]
        p = subprocess.run(cmd, pass_fds=(fd,), capture_output=True,
                           text=True, timeout=10, check=False)
        require(p.returncode == 0, "ADDON_READELF_FAILED")
        libraries = []
        for soname in re.findall(r"\(NEEDED\).*Shared library:\s*\[([^\]]+)\]",
                                 p.stdout):
            require(bool(SAFE_SONAME.fullmatch(soname)),
                    "ADDON_UNSAFE_NEEDED_SONAME")
            libraries.append(soname)
        return {"kind": "ELF", "needed": tuple(sorted(set(libraries))),
                "machine": machine_name}
    finally:
        os.close(fd)


def scan(tar_file, check_addons=True):
    """Stream all regular-file bytes; never store scripts, paths or content."""
    counts = collections.Counter()
    seen = set()
    root = SHA(b"P54_IMMUTABLE_ENGINE_TREE_V1\x00")
    items = 0
    total = 0
    addon_machines = collections.Counter()
    needed = collections.Counter()
    addon_platform_hints = collections.Counter()
    needed_by_machine = collections.defaultdict(set)
    for item in tar_file:
        items += 1
        require(items <= MAX_FILES, "TAR_COUNT_LIMIT")
        name = safe_name(item.name)
        require(name not in seen, "DUPLICATE_CANONICAL_MEMBER")
        seen.add(name)
        require(item.isfile() or item.isdir(),
                "UNSUPPORTED_LINK_OR_SPECIAL_ENTRY")
        require(0 <= item.size <= MAX_MEMBER_BYTES,
                "TAR_MEMBER_SIZE_LIMIT")
        if item.isdir():
            require(item.size == 0, "DIRECTORY_WITH_PAYLOAD")
            category = "directories"
            digest = SHA(b"").digest()
        else:
            category = kind_of(name)
            total += item.size
            require(total <= MAX_DECLARED_BYTES, "TOTAL_DECLARED_BOMB")
            reader = tar_file.extractfile(item)
            require(reader is not None, "MISSING_REGULAR_MEMBER_READER")
            h = SHA()
            consumed = 0
            addon = bytearray() if category == "native_addon" and check_addons else None
            while True:
                chunk = reader.read(1024 * 1024)
                if not chunk:
                    break
                consumed += len(chunk)
                require(consumed <= item.size, "MEMBER_OVERREAD")
                h.update(chunk)
                if addon is not None:
                    require(consumed <= MAX_ADDON_BYTES,
                            "ADDON_SIZE_BUDGET_EXCEEDED")
                    addon.extend(chunk)
            require(consumed == item.size, "MEMBER_SHORT_READ")
            digest = h.digest()
            if addon is not None:
                meta = addon_metadata(bytes(addon))
                identity = meta["kind"] + ":" + meta["machine"]
                if meta["kind"] == "NON_ELF":
                    identity += ":" + meta["nonelf"]
                addon_machines[identity] += 1
                needed.update(meta["needed"])
                needed_by_machine[meta["machine"]].update(meta["needed"])
                # Original member paths are NEVER printed. These are only
                # weak filename hints, NOT proven Android loader targets.
                labels = set(re.split(r"[^a-z0-9]+", name.lower()))
                for hint in ("android", "linux", "darwin", "windows",
                             "win32", "musl", "glibc", "gnu",
                             "aarch64", "arm64", "x64", "x86"):
                    if hint in labels:
                        addon_platform_hints[hint] += 1
        counts[category] += 1
        # Stable root digest includes full names and ALL file contents, but
        # outputs only one opaque overall digest, never a list of paths/hashes.
        name_bytes = name.encode("utf-8")
        root.update(len(name_bytes).to_bytes(4, "big"))
        root.update(name_bytes)
        root.update(b"\x01" if item.isdir() else b"\x00")
        root.update(item.size.to_bytes(8, "big"))
        root.update(digest)
    return {"members": items, "regular_bytes": total, "counts": counts,
            "tree_sha256": root.hexdigest(),
            "native_machines": addon_machines, "needed": needed,
            "addon_platform_hints": addon_platform_hints,
            "needed_by_machine": needed_by_machine}


def exact_engine(path):
    p = pathlib.Path(path)
    require(p.is_file() and p.stat().st_size == SOURCE_BYTES,
            "ORIGINAL_APK_LENGTH")
    require(file_sha(p) == SOURCE_SHA, "ORIGINAL_APK_SHA")
    with zipfile.ZipFile(p) as z:
        require(z.namelist().count(ENGINE_ENTRY) == 1,
                "ORIGINAL_ENGINE_DUPLICATED_OR_MISSING")
        entry = z.getinfo(ENGINE_ENTRY)
        require(0 < entry.file_size <= MAX_COMPRESSED, "ENGINE_SIZE_LIMIT")
        payload = z.read(ENGINE_ENTRY)
    require(payload.startswith(b"\x1f\x8b"), "EXPECTED_GZIP")
    with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as gz:
        with tarfile.open(fileobj=gz, mode="r|") as tar:
            result = scan(tar, check_addons=True)
    require(result["members"] == EXPECTED_TAR_ENTRIES,
            "BASELINE_TAR_COUNT_CHANGED")
    require(result["counts"]["native_addon"] == EXPECTED_ADDONS,
            "BASELINE_ADDON_COUNT_CHANGED")
    return result


def render(r):
    print("P54_EXACT_ORIGINAL_V138_ENGINE_CONTENT_HASH_AUDIT=PASS")
    print("P54_ARCHIVE_CANONICAL_NAMES_AND_NO_SYMLINKS=PASS")
    print("P54_EACH_REGULAR_TAR_MEMBER_FULLY_SHA256_STREAMED=PASS")
    print("P54_ARCHIVE_MEMBER_COUNT=" + str(r["members"]))
    print("P54_ARCHIVE_REGULAR_PAYLOAD_BYTES=" + str(r["regular_bytes"]))
    print("P54_OPAQUE_TREE_SHA256=" + r["tree_sha256"])
    for key in ("js", "mjs", "cjs", "json", "native_addon",
                "other_file", "directories"):
        print("P54_CATEGORY_" + key.upper() + "=" + str(r["counts"][key]))
    print("P54_ADDON_ELF_MACHINE_COUNTS=" +
          ",".join(f"{k}:{v}" for k, v in sorted(r["native_machines"].items())))
    print("P54_ADDON_NEEDED_SONAMES=" +
          ",".join(k for k in sorted(r["needed"])))
    print("P54_ADDON_NEEDED_BY_ELF_ARCH=" + ";".join(
          machine + ":" + ",".join(sorted(deps))
          for machine, deps in sorted(r["needed_by_machine"].items())))
    print("P54_ADDON_FILENAME_PLATFORM_HINT_COUNTS=" + ",".join(
          f"{k}:{v}" for k,v in sorted(r["addon_platform_hints"].items())))
    print("P54_ADDON_PATH_HINTS_ARE_NOT_PROOF_OF_RUNTIME_LOAD=YES")
    print("P54_PRODUCTION_ANDROID_ADDON_COMPATIBILITY=BLOCKED_UNVERIFIED")
    print("P54_ADDON_ANDROID_ABI_AND_DYNAMIC_LOADER=NOT_PROVEN")
    print("P54_DEVELOPMENT_SCRIPT_PATH_AND_ENTRYPOINT=NOT_DISCLOSED_OR_PROVEN")
    print("P54_PRODUCTION_JS_MODULE_RESOLUTION=NOT_IMPLEMENTED")
    print("P54_ORIGINAL_PRODUCTION_ENGINE_MANAGER_WIRED=NO")
    print("P54_SCRIPT_SOURCE_AND_NATIVE_ADDONS_EXPORTED=NO")
    print("P54_FIXED_SIGNED_V139_RELEASE=BLOCKED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("exact_original_v138_apk")
    a = parser.parse_args()
    render(exact_engine(a.exact_original_v138_apk))


if __name__ == "__main__":
    main()
