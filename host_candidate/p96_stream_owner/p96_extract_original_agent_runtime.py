#!/usr/bin/env python3
"""Temporary original agent-loop+ToolRuntime package graph for import-only
contract inspection. No production app, user data, browser, tool calls.
Uses same exact APK SHA and file restrictions as proven pi-ai fixture.
"""
import argparse
import pathlib
import p96_extract_pi_ai_fixture as ext

ext.BASE_PACKAGES=(
    "@earendil-works/pi-ai",
    "@deepseek-ai/dsh-agent-loop",
    "@deepseek-ai/dsh-tools",
    "@deepseek-ai/dsh-api-session-controller",
)
ext.MAX_PACKAGE_GRAPH=400
ext.INCLUDE_PRESENT_PEERS=True
ext.MAX_FILES=20000
ext.MAX_BYTES=350*1024*1024
ext.MAX_MEMBER=12*1024*1024

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--original",required=True)
    a.add_argument("--out",required=True)
    args=a.parse_args()
    ext.audit_extract(pathlib.Path(args.original),pathlib.Path(args.out))
    out=pathlib.Path(args.out)
    for pkg in ext.BASE_PACKAGES:
        assert (out/"node_modules"/pkg/"package.json").is_file(), pkg
    print("P96_EXACT_ORIGINAL_AGENT_DISPATCH_CLOSURE=PASS")
