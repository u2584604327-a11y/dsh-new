#!/usr/bin/env python3
"""P51 side-by-side ARM64 test APK only, NEVER a production DSH update.

Converts the *already P43-injected original v138 decoded manifest* to a
separately installable, permissionless probe package. Original DSH classes,
assets and lib files remain in APK, but NO original DSH application,
Activity, providers, services, receivers or permissions are executable.
This deliberately does not prove original MainActivity/EngineManager parity.
"""
import argparse
import pathlib
import xml.etree.ElementTree as ET

A="{http://schemas.android.com/apk/res/android}"
ORIGINAL="com.dsh.android"
SIDECAR="com.dsh.p51.isolatedprobe"
SERVICE="com.dsh.android.p43.P43IsolatedWorker"
ACTIVITY="com.dsh.android.p43.P43ProbeActivity"
LABEL="P51 Isolated Node Test"
ET.register_namespace("android","http://schemas.android.com/apk/res/android")

def require(yes,code):
    if not yes:
        raise RuntimeError("P51_BLOCKED_"+code)

def transform(src):
    root=ET.fromstring(src)
    require(root.tag=="manifest" and root.get("package")==ORIGINAL,
            "INPUT_NOT_ORIGINAL_DSH_PACKAGE")
    app=root.find("application")
    require(app is not None,"APPLICATION_NOT_FOUND")
    services=[n for n in app.findall("service") if n.get(A+"name")==SERVICE]
    activities=[n for n in app.findall("activity") if n.get(A+"name")==ACTIVITY]
    require(len(services)==1 and len(activities)==1,
            "SOURCE_TEST_COMPONENTS_NOT_UNIQUE")
    service=services[0]
    activity=activities[0]
    require(service.get(A+"exported")=="false" and
            service.get(A+"isolatedProcess")=="true" and
            service.get(A+"process")==":p43_isolated",
            "SOURCE_SERVICE_NOT_ISOLATED")
    require(activity.get(A+"exported")=="true" and
            len(activity.findall("intent-filter"))==0,
            "SOURCE_PROBE_NOT_ADB_ONLY")
    # Stronger than merely renaming package: remove every original Android
    # executable component and all permissions from the sidecar manifest.
    for child in list(root):
        if child is not app:
            root.remove(child)
    for attribute in list(root.attrib):
        if attribute not in ("package",A+"versionCode",A+"versionName"):
            del root.attrib[attribute]
    root.set("package",SIDECAR)
    root.set(A+"versionCode","1")
    root.set(A+"versionName","p51-test-1")
    app.clear()
    app.set(A+"name","android.app.Application")
    app.set(A+"hasCode","true")
    app.set(A+"label",LABEL)
    app.set(A+"allowBackup","false")
    app.set(A+"debuggable","false")
    app.set(A+"usesCleartextTraffic","false")
    # The original arm64 .so files require the package manager to place
    # verified ELF at nativeLibraryDir for ProcessBuilder execve.
    app.set(A+"extractNativeLibs","true")
    service.attrib.clear()
    service.set(A+"name",SERVICE)
    service.set(A+"isolatedProcess","true")
    service.set(A+"exported","false")
    service.set(A+"enabled","true")
    service.set(A+"process",":p51_isolated")
    service.clear()
    service.set(A+"name",SERVICE)
    service.set(A+"isolatedProcess","true")
    service.set(A+"exported","false")
    service.set(A+"enabled","true")
    service.set(A+"process",":p51_isolated")
    activity.clear()
    activity.set(A+"name",ACTIVITY)
    activity.set(A+"exported","true")
    activity.set(A+"enabled","true")
    activity.set(A+"label",LABEL)
    intent=ET.SubElement(activity,"intent-filter")
    ET.SubElement(intent,"action",{A+"name":"android.intent.action.MAIN"})
    ET.SubElement(intent,"category",{A+"name":"android.intent.category.LAUNCHER"})
    app.append(service)
    app.append(activity)
    return ET.tostring(root,encoding="utf-8",xml_declaration=True)

def verify_manifest_bytes(raw):
    root=ET.fromstring(raw)
    require(root.tag=="manifest" and root.get("package")==SIDECAR,
            "NOT_DISTINCT_PACKAGE")
    app=root.find("application")
    require(app is not None and app.get(A+"name")=="android.app.Application" and
            app.get(A+"debuggable")=="false" and
            app.get(A+"allowBackup")=="false" and
            app.get(A+"usesCleartextTraffic")=="false" and
            app.get(A+"extractNativeLibs")=="true","UNSAFE_APP_ATTRIBUTES")
    children=list(app)
    require(len(children)==2 and
            sorted(n.tag for n in children)==["activity","service"],
            "UNEXPECTED_APPLICATION_COMPONENTS")
    # aapt may add a platform uses-sdk node from explicit min/target flags.
    children=[n.tag for n in root]
    require(children.count("application")==1 and
            children.count("uses-sdk")<=1 and
            set(children).issubset({"application","uses-sdk"}),
            "UNEXPECTED_MANIFEST_TOP_LEVEL")
    service=app.find("service")
    require(service is not None and service.get(A+"name")==SERVICE and
            service.get(A+"exported")=="false" and
            service.get(A+"isolatedProcess")=="true" and
            service.get(A+"process")==":p51_isolated" and
            service.get(A+"enabled")=="true","ISOLATED_SERVICE_DRIFT")
    activity=app.find("activity")
    require(activity is not None and activity.get(A+"name")==ACTIVITY and
            activity.get(A+"exported")=="true" and
            activity.get(A+"enabled")=="true","PROBE_ACTIVITY_DRIFT")
    actions=activity.findall("intent-filter/action")
    categories=activity.findall("intent-filter/category")
    require(len(actions)==1 and len(categories)==1 and
            actions[0].get(A+"name")=="android.intent.action.MAIN" and
            categories[0].get(A+"name")=="android.intent.category.LAUNCHER",
            "EXTRA_INTENT_FILTERS")
    require(not any(c.tag in ("uses-permission","uses-permission-sdk-23",
                "permission","permission-group","queries","uses-library")
                for c in root),"PERMISSION_OR_QUERY_DRIFT")
    require(root.get(A+"sharedUserId") is None,"SHARED_USER_ID_FOUND")

def rewrite(path):
    path=pathlib.Path(path)
    require(path.is_file() and not path.is_symlink(),"INPUT_FILE_MISSING")
    before=path.read_bytes()
    after=transform(before)
    verify_manifest_bytes(after)
    path.write_bytes(after)
    print("P51_DISTINCT_PACKAGE_IDENTITY_AND_NO_ORIGINAL_APP_COMPONENTS=PASS_STATIC")
    print("P51_PERMISSIONLESS_NONEXPORTED_ISOLATED_SERVICE=PASS_STATIC")
    print("P51_ORIGINAL_DSH_SIGNER_OR_PACKAGE_WILL_NOT_BE_OVERWRITTEN=YES")
    print("P51_ORIGINAL_MAINACTIVITY_AND_APPLICATION_RUNTIME=NOT_TESTED")

def verify_apk(path):
    from androguard.core.apk import APK
    apk=APK(str(path))
    require(apk.get_package()==SIDECAR,"SIGNED_PACKAGE_NOT_SIDECAR")
    root=apk.get_android_manifest_xml()
    from lxml import etree as LET
    verify_manifest_bytes(LET.tostring(root,encoding="utf-8"))
    require(not apk.get_permissions(),"SIGNED_APP_HAS_PERMISSIONS")
    require(int(apk.get_min_sdk_version() or 0)==26 and
            int(apk.get_target_sdk_version() or 0)==28,
            "SIDECAR_SDK_DRIFT")
    print("P51_SIGNED_APK_SEPARATE_PACKAGE_NO_PERMISSIONS=PASS")
    print("P51_ORIGINAL_DSH_APPLICATION_NOT_RUNNING=YES")
    print("P51_NOT_PRODUCTION_V139=YES")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("inject","verify"))
    p.add_argument("target")
    a=p.parse_args()
    rewrite(a.target) if a.mode=="inject" else verify_apk(a.target)
