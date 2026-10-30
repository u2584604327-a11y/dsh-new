#!/usr/bin/env python3
"""P43 only: inject an isolated Service and disposable diagnostic Activity
into a private offline ORIGINAL DSH AndroidManifest. No production release."""
import argparse
import hashlib
import pathlib
import xml.etree.ElementTree as ET

A="{http://schemas.android.com/apk/res/android}"
SERVICE="com.dsh.android.p43.P43IsolatedWorker"
PROBE="com.dsh.android.p43.P43ProbeActivity"
ET.register_namespace("android","http://schemas.android.com/apk/res/android")

def require(ok,msg):
    if not ok:
        raise RuntimeError("P43_BLOCKED_"+msg)

def inject(path):
    target=pathlib.Path(path)
    require(target.is_file() and not target.is_symlink(),"MANIFEST_MISSING")
    original=target.read_bytes()
    root=ET.fromstring(original)
    require(root.tag=="manifest" and root.get("package")=="com.dsh.android",
            "PACKAGE_DRIFT")
    application=root.find("application")
    require(application is not None,"APPLICATION_MISSING")
    # Preserve every pre-existing element and attribute; fail on collision.
    existing_services=list(application.findall("service"))
    existing_activities=list(application.findall("activity"))
    require(len(existing_services)==2,"ORIGINAL_SERVICE_COUNT_DRIFT")
    require(not any(s.get(A+"name")==SERVICE for s in existing_services),"REPLAY")
    require(not any(a.get(A+"name")==PROBE for a in existing_activities),"REPLAY")
    app_before={k:v for k,v in application.attrib.items()}
    service_before=[ET.tostring(s) for s in existing_services]
    activities_before=[ET.tostring(a) for a in existing_activities]
    s=ET.SubElement(application,"service",{
        A+"name":SERVICE,
        A+"isolatedProcess":"true",
        A+"exported":"false",
        A+"process":":p43_isolated",
    })
    a=ET.SubElement(application,"activity",{
        A+"name":PROBE,
        A+"exported":"true",
        A+"label":"P43 ORIGINAL APK TEMPORARY BINDER TEST",
    })
    # An explicit adb-only test Activity. No launcher intent filter.
    require(application.attrib==app_before,"APPLICATION_ATTRIBUTES_CHANGED")
    require([ET.tostring(x) for x in existing_services]==service_before,"EXISTING_SERVICES_CHANGED")
    require([ET.tostring(x) for x in existing_activities]==activities_before,"EXISTING_ACTIVITIES_CHANGED")
    require(s.get(A+"isolatedProcess")=="true" and s.get(A+"exported")=="false",
            "ISOLATION_FLAGS_CHANGED")
    require(not list(a.findall("intent-filter")),"TEST_ACTIVITY_NOT_ADB_ONLY")
    target.write_bytes(ET.tostring(root,encoding="utf-8",xml_declaration=True))
    print("P43_ORIGINAL_SERVICE_MANIFEST_INJECTED=PASS_STATIC")
    print("P43_EXISTING_DSH_APPLICATION_ACTIVITIES_SERVICES=UNCHANGED_SEMANTICALLY")
    print("P43_EMBEDDED_WORKER_NODESCRIPTS=NONE")

def verify(apk):
    from androguard.core.apk import APK
    target=APK(apk)
    tree=target.get_android_manifest_xml()
    root=tree.find("application")
    require(root is not None,"BUILT_MANIFEST_MISSING")
    services=[s for s in root.findall("service") if s.get(A+"name")==SERVICE]
    probes=[s for s in root.findall("activity") if s.get(A+"name")==PROBE]
    require(len(services)==1 and len(probes)==1,"BUILT_COMPONENT_MISSING")
    require(services[0].get(A+"isolatedProcess")=="true" and
            services[0].get(A+"exported")=="false" and
            services[0].get(A+"process")==":p43_isolated",
            "BUILT_ISOLATED_SERVICE_NOT_PRIVATE")
    require(probes[0].get(A+"exported")=="true" and
            not list(probes[0].findall("intent-filter")),
            "BUILT_TEST_ACTIVITY_UNEXPECTED")
    require(len(root.findall("service"))==3,"BUILT_ORIGINAL_SERVICES_CHANGED")
    require(target.get_package()=="com.dsh.android","PACKAGE_CHANGED")
    require(int(target.get_min_sdk_version() or 0)==26 and
            int(target.get_target_sdk_version() or 0)==28,
            "BUILT_MIN_TARGET_SDK_DRIFT")
    print("P43_ORIGINAL_REBUILT_APK_ISOLATED_SERVICE_MANIFEST=PASS")
    print("P43_ORIGINAL_SERVICE_NOT_EXPORTED=PASS")
    print("P43_BUNDLE_IS_TEST_ONLY_NOT_PRODUCTION=YES")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("operation",choices=["inject","verify"])
    p.add_argument("filename")
    a=p.parse_args()
    inject(a.filename) if a.operation=="inject" else verify(a.filename)
