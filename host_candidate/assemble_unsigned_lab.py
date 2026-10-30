#!/usr/bin/env python3
"""Bounded unsigned APK fusion LAB. Not an installable product, no signing/release."""
import argparse,copy,hashlib,io,json,pathlib,re,zipfile
from androguard.core.dex import DEX
from patch_deny import sha as hash_bytes,EXPECTED_APK
from patch_deny_art_safe import apply_art_safe as deny
import patch_browser,patch_privacy,patch_native_export_reply
from patch_native_export_failclosed import apply as patch_p9_export
from patch_remaining_bundle_calls import apply as patch_p10_builders
from patch_browser import apply_browser
from patch_privacy import apply_privacy
from verify_p6_asset_preimages import EXPECTED_P6,EXPECTED_PATHS,sha_file
from patch_logs_metadata_only import patch as patch_p11_logs
from patch_token_usage_p14 import patch as patch_p14_token
from patch_privileged_tools_p18 import patch_both as patch_p18_tools
from p13_manifest_inject import inject as inject_p13_manifest
P11_LOG_ZIP_SHA="29bcf54bb00ea989516b8bc7bdeb6bbd68f9a11a85082273399eb3597cdd76a0"
P14_BROWSER_TOOL_SHA="be8201f11c7a12478d0552efaf129becde6d104ef2da203c2433b3dfc397a69f"
P18_PRIVILEGED_TOOL_SHAS={"assets/shell-tool.zip":"51dac0e5c82a38e03318535b6d0d1ac9fe52d2b020ba508efc82af0947df1187","assets/root-tool.zip":"8f54d9871357a79df0acb997169becc03282eb64f3e191ff0cdba4bf7492b7f1"}
from patch_native_export_reply import apply as patch_p8_export
P1_SAFE_SHA="8565675b7da207e858f1c3dd69896ce5a68015a24605157a4a11b259218119b6"
P2_BROWSER_SAFE_SHA="e392e65bf7592ddd9531af81459e678d1462423abed526d5eeddac248ab158a4"
P8_DEX_SHA="086d0e431515d9f5072109e96a94cbbe7f37c578f1cc68722bcd787881d1acb3"
P9_DEX_SHA="db1d61fdae52f55b569cc92bc82afbc82c31f305295ef4a2fd3a431177038d29"
P10_DEX_SHA="cfe19482edcd4bea7c1b476bb90da5b956759c98a2bb101ee9dd459be4a15474"
P7_LOG_TOOL_PATH="assets/logs-tool.zip"

COMBINED_SHA="8682204473860802b17b18ab487fa72380eb076d37495d2de4abb76abad0df6b"
SIGNATURE_META=re.compile(r"META-INF/[^/]+\.(?:RSA|DSA|EC|SF)$",re.I)

def addon_classes(dex):
    return {c.get_name() for c in DEX(dex).get_classes()}

def assemble(apkpath,p6path,p5path,outpath):
    if sha_file(apkpath)!=EXPECTED_APK:raise ValueError("APK_PREIMAGE_MISMATCH")
    if sha_file(p6path)!=EXPECTED_P6:raise ValueError("P6_PREIMAGE_MISMATCH")
    addon=pathlib.Path(p5path).read_bytes()
    if len(addon)>5_000_000:raise ValueError("P5_DEX_TOO_LARGE")
    newclasses=addon_classes(addon)
    if len(newclasses)<64 or not all(
        n.startswith("Lcom/dsh/p1/") or n.startswith("Lcom/dsh/p12/")
        for n in newclasses
    ):
        raise ValueError("P5_P12_CLASS_SCOPE_MISMATCH")
    if "Lcom/dsh/p12/P12LogViewerReviewEntry;" not in newclasses or \
       "Lcom/dsh/p12/P13NativeReviewInitializer;" not in newclasses:
        raise ValueError("P13_AUTO_STARTUP_OR_P12_ADAPTER_CLASS_MISSING")
    if "Landroidx/startup/Initializer;" in newclasses:
        raise ValueError("FORBIDDEN_DUPLICATE_ANDROIDX_STARTUP_STUB")
    with zipfile.ZipFile(p6path) as bundle:
        if bundle.testzip():raise ValueError("P6_CRC_FAIL")
        inner=bundle.read("output/DSH_V139_P6_ASSET_OVERLAY_NOT_APK.zip")
    with zipfile.ZipFile(io.BytesIO(inner)) as patch:
        if patch.testzip():raise ValueError("P6_OVERLAY_CRC_FAIL")
        man=json.loads(patch.read("ASSET_DELTA_MANIFEST.json"))
        if set(man["changes"])!=EXPECTED_PATHS:raise ValueError("P6_UNEXPECTED_PATHS")
        if set(patch.namelist())!=EXPECTED_PATHS|{"ASSET_DELTA_MANIFEST.json"}:raise ValueError("P6_EXTRA_FILES")
        overlays={n:patch.read(n) for n in EXPECTED_PATHS}
        p14_browser,p14_js=patch_p14_token(overlays["assets/browser-tool.zip"])
        if hash_bytes(p14_browser)!=P14_BROWSER_TOOL_SHA:raise ValueError("P14_BROWSER_TOKEN_OUTPUT_NOT_PINNED")
        if "本轮用量（未提供）" not in p14_js:raise ValueError("P14_UNKNOWN_USAGE_STATUS_ABSENT")
    with zipfile.ZipFile(apkpath) as original:
        if original.testzip():raise ValueError("BASELINE_APK_CRC_FAIL")
        names=original.namelist()
        if len(names)!=len(set(names)):raise ValueError("DUPLICATE_BASELINE_NAMES")
        dexnames=sorted(x for x in names if re.fullmatch(r"classes(?:[2-9][0-9]*)?\.dex",x))
        if dexnames!=["classes.dex","classes2.dex"]:raise ValueError("UNEXPECTED_ORIGINAL_DEX_LAYOUT")
        if not (EXPECTED_PATHS|{P7_LOG_TOOL_PATH}).issubset(set(names)):
            raise ValueError("MISSING_ORIGINAL_ASSETS_OR_LOG_PLUGIN")
        new_manifest,p13_report=inject_p13_manifest(original.read("AndroidManifest.xml"))
        if hash_bytes(new_manifest)!="39a825e40aff02cef83944ef40de61e310a4c6912d3a352169637ee72a9a0b5f":
            raise ValueError("P13_MANIFEST_HASH_NOT_PINNED")
        patched_log_plugin,patched_log_js=patch_p11_logs(original.read(P7_LOG_TOOL_PATH))
        if hash_bytes(patched_log_plugin)!=P11_LOG_ZIP_SHA:raise ValueError("P11_LOG_PLUGIN_IDENTITY_MISMATCH")
        if "enum: ['summary']" not in patched_log_js:raise ValueError("P11_SUMMARY_ONLY_SCHEMA_MISSING")
        if b"bundlePath: { type: 'string' }" in patched_log_js.encode("utf-8"):
            raise ValueError("P7_AI_VISIBLE_PATH_SCHEMA_STILL_PRESENT")
        overlays[P7_LOG_TOOL_PATH]=patched_log_plugin
        p18=patch_p18_tools({name:original.read(name) for name in P18_PRIVILEGED_TOOL_SHAS})
        if {n:hash_bytes(pair[0]) for n,pair in p18.items()}!=P18_PRIVILEGED_TOOL_SHAS:
            raise ValueError("P18_UNTRUSTED_SHELL_ROOT_POLICY_OUTPUT_NOT_PINNED")
        p1,p1_report=deny(original.read("classes.dex"))
        if hash_bytes(p1)!=P1_SAFE_SHA or p1_report["TRY_START_END_AND_HANDLER_ALIGNMENT"]!="PASS_STATIC":
            raise ValueError("P1_ART_SAFE_PREIMAGE_OR_TRY_BOUNDARY_FAIL")
        patch_browser.EXPECTED_P1=P1_SAFE_SHA
        p2,_=patch_browser.apply_browser(p1)
        if hash_bytes(p2)!=P2_BROWSER_SAFE_SHA:raise ValueError("ART_SAFE_BROWSER_CHAIN_MISMATCH")
        patch_privacy.EXPECTED=P2_BROWSER_SAFE_SHA
        modified,_=patch_privacy.apply_privacy(p2)
        if hash_bytes(modified)!=COMBINED_SHA:raise ValueError("ART_SAFE_PRIVACY_CHAIN_MISMATCH")
        patch_native_export_reply.EXPECTED_P2=COMBINED_SHA
        modified,p8_report=patch_native_export_reply.apply(modified)
        if hash_bytes(modified)!=P8_DEX_SHA:raise ValueError("P8_BOUND_NATIVE_DEX_IDENTITY_FAIL")
        modified,p9_report=patch_p9_export(modified)
        if hash_bytes(modified)!=P9_DEX_SHA:raise ValueError("P9_FAIL_CLOSED_NATIVE_EXPORT_IDENTITY_FAIL")
        modified,p10_report=patch_p10_builders(modified)
        if hash_bytes(modified)!=P10_DEX_SHA:raise ValueError("P10_ALL_NATIVE_ZIP_BUILDER_CALLS_NOT_DENIED")
        for name in dexnames:
            if addon_classes(original.read(name))&newclasses:raise ValueError("DUPLICATE_CLASS_IN_FUSED_DEX")
        resultpath=pathlib.Path(outpath)
        resultpath.parent.mkdir(parents=True,exist_ok=True)
        unchanged=0
        with zipfile.ZipFile(resultpath,"w",allowZip64=True) as output:
            output.comment=b"UNSIGNED_DSH_FUSION_LAB_ONLY_NOT_FOR_INSTALLATION"
            for member in original.infolist():
                name=member.filename
                if name=="META-INF/MANIFEST.MF" or SIGNATURE_META.fullmatch(name):continue
                data=original.read(name)
                if name in overlays and name!=P7_LOG_TOOL_PATH:
                    spec=man["changes"][name]
                    if hash_bytes(data)!=spec["original_sha256"] or len(data)!=spec["original_size"]:
                        raise ValueError("P6_OVERLAY_PREIMAGE_FAIL_"+name)
                    candidate=overlays[name]
                    if hash_bytes(candidate)!=spec["new_sha256"] or len(candidate)!=spec["new_size"]:
                        raise ValueError("P6_OVERLAY_OUTPUT_FAIL_"+name)
                    data=p14_browser if name=="assets/browser-tool.zip" else candidate
                elif name==P7_LOG_TOOL_PATH:
                    data=patched_log_plugin
                elif name in p18:
                    data=p18[name][0]
                elif name=="AndroidManifest.xml":data=new_manifest
                elif name=="classes.dex":data=modified
                elif not member.is_dir():unchanged+=1
                meta=copy.copy(member)
                meta.extra=b""
                output.writestr(meta,data)
            output.writestr("classes3.dex",addon,compress_type=zipfile.ZIP_DEFLATED)
        with zipfile.ZipFile(resultpath) as merged:
            if merged.testzip():raise AssertionError("FUSED_APK_CRC_FAIL")
            if len(merged.namelist())!=len(set(merged.namelist())):raise AssertionError("DUPLICATE_OUTPUT_NAMES")
            for name in names:
                if name in overlays or name in p18 or name in ("classes.dex","AndroidManifest.xml","META-INF/MANIFEST.MF") or SIGNATURE_META.fullmatch(name):continue
                if merged.read(name)!=original.read(name):raise AssertionError("UNMODIFIED_APK_ENTRY_CHANGED_"+name)
            if hash_bytes(merged.read("classes.dex"))!=P10_DEX_SHA:raise AssertionError("PATCHED_DEX_CHANGED")
            if merged.read("AndroidManifest.xml")!=new_manifest:raise AssertionError("P13_MANIFEST_CHANGED")
            for name, (blob,js) in p18.items():
                if merged.read(name)!=blob:raise AssertionError("P18_PRIVILEGED_TOOL_OUTPUT_CHANGED_"+name)
            if merged.read("classes3.dex")!=addon:raise AssertionError("P5_DEX_CHANGED")
            for name in EXPECTED_PATHS|{P7_LOG_TOOL_PATH}:
                expected=p14_browser if name=="assets/browser-tool.zip" else overlays[name]
                if merged.read(name)!=expected:raise AssertionError("OVERLAY_CHANGED_"+name)
            if any(n=="META-INF/MANIFEST.MF" or SIGNATURE_META.fullmatch(n) for n in merged.namelist()):
                raise AssertionError("LEGACY_SIGNATURE_FILES_REMAIN")
    return {
      "ASSEMBLY":"UNSIGNED_TEMP_LAB_STRUCTURE_PASS",
      "ORIGINAL_APK_SHA256":EXPECTED_APK,"PATCHED_MAIN_DEX_SHA256":P10_DEX_SHA,
      "P9_NATIVE_RAW_ZIP_DENY_SHA256":P9_DEX_SHA,
      "P10_EXTERNAL_DIRECT_LEGACY_ZIP_BUILD_CALLS":
          p10_report["ALL_DIRECT_EXTERNAL_DIAGNOSTIC_BUILD_DEFAULT_CALLS"],
      "P8_NATIVE_PATH_REDACTED_SHA256":P8_DEX_SHA,
      "P9_NATIVE_RAW_ZIP_CREATION":"FAIL_CLOSED",
      "P9_FAIL_CLOSED_EVIDENCE":p9_report["NATIVE_LOG_EXPORT_BUNDLE_BUILDER_DISABLED"],
      "P2_BROWSER_PRIVACY_DENY_SAFE_SHA256":COMBINED_SHA,
      "OLD_P2_ARRAY_PAYLOAD_ART":"KNOWN_FAIL",
      "ART_SAFE_DENY_TRY_BOUNDARIES":p1_report["TRY_START_END_AND_HANDLER_ALIGNMENT"],
      "P8_NATIVE_EXPORT_BUNDLEPATH_REMOVED":p8_report["NATIVE_EXPORT_REPLY_BUNDLE_PATH_REMOVED"],
      "P5_ADDON_DEX_SHA256":hash_bytes(addon),"P5_CLASS_COUNT":len(newclasses),
      "P13_NATIVE_AUTOSTART_MANIFEST_SHA256":hash_bytes(new_manifest),
      "P13_STARTUP_META_COUNT":p13_report["P13_ANDROIDX_META_DATA_COUNT"],
      "P13_AUTOWIRE_REAL_ACTIVITY_RUNTIME":"PENDING_ANDROID_INSTRUMENTATION",
      "ADDED_DEX_ENTRY":"classes3.dex","P6_OVERLAY_FILES":sorted(EXPECTED_PATHS),
      "P11_SUMMARY_ONLY_LOG_TOOL_SHA256":hash_bytes(patched_log_plugin),
      "P14_LAN_TOKEN_USAGE_BROWSER_ASSET_SHA256":hash_bytes(p14_browser),
      "P14_TOKEN_USAGE":"PROVIDER_OR_ESTIMATE_OR_UNAVAILABLE",
      "P18_LEGACY_ADB_SHELL_ROOT_TOOLS":"UNREGISTERED_FAIL_CLOSED",
      "P18_PRIVILEGED_TOOL_SHA256":{n:hash_bytes(p18[n][0]) for n in sorted(p18)},
      "P18_GENERIC_BASH_NODE_SAME_UID":"NOT_ISOLATED",
      "P7_AI_VISIBLE_DIAGNOSTIC_PATH":"REDACTED",
      "P11_MODEL_RAW_LOG_CRASH_EXPORT":"DENIED_BEFORE_MAILBOX",
      "P7_NATIVE_MAILBOX_FILE_PATH":"UNVERIFIED_PRIVACY",
      "UNCHANGED_ENTRIES_CHECKED":unchanged,
      "UNSIGNED_LAB_FILE_SHA256":sha_file(resultpath),
      "UNSIGNED_LAB_FILE_BYTES":resultpath.stat().st_size,
      "PACKAGE_VERSION_CODE":"138_UNCHANGED",
      "P5_HOST_WIRED":"P13_STARTUP_CANDIDATE_UNVERIFIED","DIAGNOSTIC_EGRESS_TOTAL_GATE":"NOT_VERIFIED",
      "SIGNED_WITH_ORIGINAL_CERT":"NO","ART_VERIFIED":"NO",
      "INSTALLATION_ALLOWED":"NO","APK_EXPORT_ALLOWED":"NO"}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("v138");p.add_argument("p6");p.add_argument("p5_dex")
    p.add_argument("--output",required=True);p.add_argument("--report",required=True)
    args=p.parse_args()
    result=assemble(args.v138,args.p6,args.p5_dex,args.output)
    pathlib.Path(args.report).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
