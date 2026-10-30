#!/usr/bin/env python3
import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from audit_original_webview_access import access_category
assert access_category(1)=="PUBLIC"
assert access_category(2)=="PRIVATE"
assert access_category(4)=="PROTECTED"
assert access_category(0)=="PACKAGE_PRIVATE"
print("P72_SYNTHETIC_ACCESS_FLAG_CLASSIFIER=PASS")
