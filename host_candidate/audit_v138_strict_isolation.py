"""P15 original v138 UID/virtualization/fingerprint isolation audit.
Read-only exact-APK structural proof. No accounts, diagnostics or token values.
A WebView device-mode preset must NEVER count as OS-level VM isolation.
"""
import argparse,hashlib,io,json,os,pathlib,sys,zipfile
from p13_manifest_inject import strings_from_pool,chunk,attrs,u32,BASELINE_SHA
EXPECTED_APK="3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5"
COMPONENTS={"service","provider","activity","activity-alias"}
def audit(path):
    data=pathlib.Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=EXPECTED_APK:raise ValueError("NOT_EXACT_SIGNED_V138")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if z.testzip():raise ValueError("APK_CRC_FAIL")
        manifest=z.read("AndroidManifest.xml")
        if hashlib.sha256(manifest).hexdigest()!=BASELINE_SHA:raise ValueError("MANIFEST_IDENTITY_FAIL")
        ss=strings_from_pool(manifest);stack=[];components=[]
        pos=8
        while pos<len(manifest):
            t,h,size=chunk(manifest,pos)
            if t==0x102:
                tag=ss[u32(manifest,pos+20)]
                a=attrs(manifest,pos,ss)
                info={k:v[0] for k,v in a.items() if k in
                     ("name","process","isolatedProcess","exported","permission")}
                if tag in COMPONENTS:
                    components.append({"kind":tag,**info})
                stack.append(tag)
            elif t==0x103:
                if not stack:raise ValueError("MANIFEST_UNBALANCED")
                stack.pop()
            pos+=size
        if stack:raise ValueError("MANIFEST_UNBALANCED")
        children=[x for x in components if x["kind"]=="service"]
        isolated=[x for x in children if x.get("isolatedProcess") in (True,1,"true")]
        process_names=sorted(set(str(x.get("process") or "default") for x in children))
        # Concrete assets, not heuristic OS isolation claims.
        present=sorted(n for n in (
          "assets/node-runtime.bin","assets/boosandbox.bin",
          "assets/boo-sandbox-run.bin","assets/dsh-android-shell.mjs",
          "assets/shell-tool.zip","assets/root-tool.zip",
          "assets/browser-tool.zip") if n in z.namelist())
        js=z.read("assets/browser-tool.zip")
        with zipfile.ZipFile(io.BytesIO(js)) as browser:
            t=browser.read("lib/index.js").decode("utf-8")
            has_modes="const DEVICE_PROFILES = {" in t
            disclaimer=("engine remains Android WebView/Chromium" in t or
                        "engine remains Android WebView" in t or
                        "The engine remains Android WebView/Chromium" in t)
        return {
          "BASELINE_V138_APK_SHA256":EXPECTED_APK,
          "MANIFEST_COMPONENTS":components,
          "SERVICE_COUNT":len(children),
          "SERVICES_MARKED_ISOLATED_PROCESS":isolated,
          "SERVICE_PROCESS_NAMES":process_names,
          "NODE_AND_EXECUTION_CAPABLE_ASSETS":present,
          "BROWSER_HAS_DEVICE_MODE_PRESETS":has_modes,
          "BROWSER_DISCLOSES_UNDERLYING_WEBVIEW":disclaimer,
          "ANDROID_OS_UID_ISOLATION_DEMONSTRATED":False,
          "ISOLATED_RUNTIME_BROKER_TESTED":False,
          "WEBVIEW_SEPARATE_DATA_DIRECTORY_TESTED":False,
          "WEBVIEW_PER_SITE_STORAGE_BOUNDARY_TESTED":False,
          "GENERIC_NODE_SHELL_FS_EGRESS_GATE_CLOSED":False,
          "TARGET_SITE_SEES_EMULATED_HARDWARE":False,
          "USER_AGENT_AND_VIEWPORT_SIMULATION":"SOURCE_EXISTS_RUNTIME_ONLY",
          "VIRTUAL_MACHINE_OR_STRICT_SEPARATION":"NOT_VERIFIED_FAIL_CLOSED",
          "REAL_PHONE":"NOT_TOUCHED"}
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("apk");a.add_argument("--output",required=True)
    b=a.parse_args();result=audit(b.apk)
    pathlib.Path(b.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    # Summary intentionally omits any user-private configuration/credentials.
    print(json.dumps({
        "SERVICE_COUNT":result["SERVICE_COUNT"],
        "ISOLATED_PROCESS_SERVICE_COUNT":len(result["SERVICES_MARKED_ISOLATED_PROCESS"]),
        "SERVICE_PROCESS_NAMES":result["SERVICE_PROCESS_NAMES"],
        "NODE_EXECUTION_ASSETS":result["NODE_AND_EXECUTION_CAPABLE_ASSETS"],
        "DEVICE_PRESET_CODE":result["BROWSER_HAS_DEVICE_MODE_PRESETS"],
        "STRICT_ISOLATION":"NOT_VERIFIED_FAIL_CLOSED",
        "UID_BOUNDARY":"NOT_VERIFIED",
        "REAL_VIRTUAL_MACHINE":"NO_PROOF"
    },indent=2))
