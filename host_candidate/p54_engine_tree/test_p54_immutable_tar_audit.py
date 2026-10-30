#!/usr/bin/env python3
"""No actual original scripts in test data."""
import io
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p54_immutable_tar_audit import scan, safe_name, addon_metadata

checks = 0


def ok(v, code):
    global checks
    checks += 1
    if not v:
        raise AssertionError(code)


def tar(*entries):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as t:
        for name, content, member_type in entries:
            m = tarfile.TarInfo(name)
            m.type = member_type
            if member_type == tarfile.REGTYPE:
                m.size = len(content)
                t.addfile(m, io.BytesIO(content))
            else:
                t.addfile(m)
    buf.seek(0)
    return buf


def run(blob, check_addons=False):
    with tarfile.open(fileobj=blob, mode="r|") as t:
        return scan(t, check_addons=check_addons)


def reject(entries, why):
    global checks
    try:
        run(tar(*entries))
    except ValueError as e:
        checks += 1
        ok("P54_BLOCKED_" in str(e), why)
    else:
        raise AssertionError("wrongly allowed: " + why)


a = ("engine/main.js", b"console.log('fixture')", tarfile.REGTYPE)
b = ("engine/package.json", b'{"type":"module"}', tarfile.REGTYPE)
d = ("engine/assets", b"", tarfile.DIRTYPE)
first = run(tar(a, b, d))
second = run(tar(a, b, d))
ok(first["members"] == 3, "member count")
ok(first["regular_bytes"] == len(a[1]) + len(b[1]), "byte count")
ok(first["tree_sha256"] == second["tree_sha256"], "same tree fingerprint")
ok(first["counts"]["directories"] == 1, "directory")
ok(first["counts"]["js"] == 1 and first["counts"]["json"] == 1, "categories")
changed = run(tar((a[0], b"console.log('tampered')", tarfile.REGTYPE), b, d))
ok(first["tree_sha256"] != changed["tree_sha256"], "content hash tamper")
reordered = run(tar(b, a, d))
ok(first["tree_sha256"] != reordered["tree_sha256"], "tar order commits")
ok(safe_name("./engine/main.js") == "engine/main.js", "single root prefix")
for name in ("../backdoor.js", "/tmp/escape.js", "root/../other.js",
             "foo\\bar.js", "foo//bar.js", "foo/./bar.js", "",
             ".", "folder/\nsecret"):
    reject(((name, b"test", tarfile.REGTYPE),), "unsafe name " + repr(name))
try:
    safe_name("a/\x00b")
except ValueError as exc:
    ok("P54_BLOCKED_" in str(exc), "embedded NUL direct input")
else:
    raise AssertionError("embedded NUL accepted")
reject((a, a), "duplicate member")
reject((a, ("./engine/main.js", b"x", tarfile.REGTYPE)),
       "normalized duplicate")
reject((("shortcut", b"", tarfile.SYMTYPE),), "symlink")
reject((("shortcut", b"", tarfile.LNKTYPE),), "hardlink")
reject((("device", b"", tarfile.CHRTYPE),), "special node")
ok(addon_metadata(b"not an ELF")["nonelf"] == "small_ascii",
   "NON_ELF text placeholder is not executed")
ok(addon_metadata(b"")["nonelf"] == "empty",
   "zero-byte addon cannot become executable")
ok(addon_metadata(bytes([0,255]))["nonelf"] == "small_non_ascii",
   "small binary addon is not a proven ELF")
ok(addon_metadata(b"MZ" + bytes(512))["nonelf"] == "PE_MZ",
   "Windows PE native addon is not Android ELF")
ok(addon_metadata(bytes([0xcf,0xfa,0xed,0xfe]) + bytes(128))["nonelf"]
   == "MACHO_OR_FAT_MAGIC", "Mach-O addon not Android ELF")
print("P54_SAFE_TAR_HASH_NEGATIVE_TESTS=PASS assertions=" + str(checks))
print("P54_NO_REAL_JS_OR_EXTRACTED_ORIGINAL_PACKAGE_TEST=PASS")
