#!/usr/bin/env python3
"""P27: verify native ARM64 CI HOST and check for *actual* Android ARM64 guests.

This gate is intentionally incapable of declaring Android/Node PASS from
Linux uname -m, installed SDK tools, or /dev/kvm. No APK, phone, private
binaries, credentials, VM image or network traffic.
"""
import argparse
import json
import os
import pathlib
import platform
import shutil
import struct
import subprocess

KVM_GET_API_VERSION = 0xAE00
ELF_MACHINE_AARCH64 = 183


def kvm_info():
    path = pathlib.Path("/dev/kvm")
    if not path.exists():
        return {"device": "ABSENT", "api": "NOT_TESTED", "usable": False}
    import fcntl
    fd = None
    try:
        fd = os.open(str(path), os.O_RDWR | os.O_CLOEXEC)
        api = fcntl.ioctl(fd, KVM_GET_API_VERSION, 0)
        return {"device": "PRESENT", "api": api, "usable": api == 12}
    except OSError as exc:
        return {
            "device": "PRESENT",
            "api": "INACCESSIBLE",
            "usable": False,
            "errno": exc.errno,
        }
    finally:
        if fd is not None:
            os.close(fd)


def elf_info(path):
    try:
        with open(path, "rb") as f:
            h = f.read(24)
        if len(h) < 20 or h[:4] != b"\x7fELF":
            return "NOT_ELF"
        if h[5] != 1:
            return "NON_LITTLE_ENDIAN"
        return "AARCH64" if struct.unpack("<H", h[18:20])[0] == ELF_MACHINE_AARCH64 else "OTHER_ARCH"
    except OSError:
        return "NOT_READABLE"


def candidates():
    homes = [
        os.environ.get("ANDROID_HOME", ""),
        os.environ.get("ANDROID_SDK_ROOT", ""),
        "/usr/local/lib/android/sdk",
        os.environ.get("HOME", "") + "/Android/Sdk",
    ]
    found = {}
    emu = shutil.which("emulator")
    if emu:
        found["emulator_PATH"] = elf_info(emu)
    for idx, home in enumerate(homes):
        if not home:
            continue
        path = pathlib.Path(home) / "emulator" / "emulator"
        if path.exists():
            found["sdk_emulator_candidate_" + str(idx)] = elf_info(path)
    for app in ("qemu-system-aarch64", "adb", "sdkmanager"):
        location = shutil.which(app)
        found[app] = "PRESENT" if location else "ABSENT"
    return found


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--report", required=True)
    a = args.parse_args()
    uname = platform.machine().lower()
    native_arm = uname in ("aarch64", "arm64")
    kvm = kvm_info()
    apps = candidates()
    emulator = any("emulator" in name and value == "AARCH64"
                   for name, value in apps.items())
    # KVM (host) is not an Android guest, much less an Android isolate.
    report = {
        "task": "P27_ARM64_ANDROID_EXECUTOR_FEASIBILITY",
        "runner_native_arm64": native_arm,
        "host_kernel_arm64": uname,
        "arm64_linux_kvm": kvm,
        "tool_presence": apps,
        "official_google_linux_arm64_emulator_binary_observed": emulator,
        "android_arm64_guest_adb_connected": "NOT_CHECKED_NO_GUEST_BOOT",
        "android_arm64_guest_sdk_35": "NOT_TESTED",
        "android_arm64_isolated_service": "NOT_TESTED",
        "original_signed_v138_node_sha_verified_this_run": "NOT_READ_NO_PRIVATE_BINARY",
        "original_arm64_node_executed_in_android_isolated_uid": "NOT_TESTED",
        "original_node_private_file_and_network_denial": "NOT_TESTED",
        "dsh_v139_apk_ready": False,
        "v138_or_original_signer_changed": False,
        "release": "BLOCKED",
    }
    if not native_arm:
        raise SystemExit("P27_ARM64_HOST_RUNNER=FAIL_WRONG_MACHINE")
    out = pathlib.Path(a.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("P27_GITHUB_HOST_ARCH_AARCH64=PASS")
    print("P27_ARM64_HOST_KVM=" + ("USABLE" if kvm["usable"] else "UNAVAILABLE"))
    print("P27_HOST_NATIVE_ARM64_ANDROID_EMULATOR_BINARY=" +
          ("OBSERVED_UNTESTED" if emulator else "NOT_PRESENT"))
    print("P27_ANDROID_ARM64_GUEST_BOOT=NOT_TESTED")
    print("P27_ORIGINAL_V138_ARM64_NODE_ISOLATED_EXECVE=NOT_TESTED")
    print("P27_ORIGINAL_DSH_APP_RELEASE=BLOCKED")


if __name__ == "__main__":
    main()
