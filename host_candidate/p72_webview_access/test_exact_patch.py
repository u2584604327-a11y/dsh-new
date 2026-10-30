#!/usr/bin/env python3
import sys,pathlib,tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from patch_exact_webview_accessor import patch
before=""".class public Lcom/dsh/android/browser/AiBrowserView;
.method private final currentWebView()Landroid/webkit/WebView;
  .registers 2
  const/4 v0, 0x0
  return-object v0
.end method
.method public otherMethod()V
  .registers 1
  return-void
.end method
"""
with tempfile.TemporaryDirectory() as d:
 f=pathlib.Path(d)/"smali/com/dsh/android/browser/AiBrowserView.smali"
 f.parent.mkdir(parents=True);f.write_text(before)
 patch(d)
 after=f.read_text()
 assert after==before.replace(".method private final currentWebView()",
                             ".method public final currentWebView()")
 try:patch(d)
 except RuntimeError:pass
 else:raise AssertionError("repeat not blocked")
print("P72_EXACT_ONLY_ACCESS_VISIBILITY_SYNTHETIC=PASS")
