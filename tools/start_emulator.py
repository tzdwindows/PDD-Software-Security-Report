# -*- coding: utf-8 -*-
import subprocess
import os
import sys

SDK_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "android-sdk")
EMULATOR = os.path.join(SDK_ROOT, "emulator", "emulator.exe")

log_path = os.path.join(os.path.dirname(__file__), "emulator_log.txt")

cmd = [
    EMULATOR,
    "-avd", "pdd_analysis",
    "-writable-system",
    "-no-snapshot",
    "-no-audio",
    "-no-boot-anim",
    "-gpu", "swiftshader_indirect",
    "-memory", "2048"
]

print("Starting emulator in background...")
with open(log_path, "w") as log:
    proc = subprocess.Popen(
        cmd,
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    )
print(f"Emulator PID: {proc.pid}")
print("Background process started. Check emulator_log.txt for output.")