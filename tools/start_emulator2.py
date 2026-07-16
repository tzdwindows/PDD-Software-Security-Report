# -*- coding: utf-8 -*-
import subprocess
import os

SDK_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "android-sdk")
EMULATOR = os.path.join(SDK_ROOT, "emulator", "emulator.exe")
log_path = os.path.join(os.path.dirname(__file__), "emulator_log2.txt")

# Try with different GPU options to avoid Vulkan errors
cmd = [
    EMULATOR,
    "-avd", "pdd_analysis",
    "-writable-system",
    "-no-snapshot",
    "-no-audio",
    "-no-boot-anim",
    "-gpu", "guest",        # Use guest-side rendering instead of host Vulkan
    "-memory", "2048",
    "-verbose"
]

print("Starting emulator (attempt 2) with -gpu guest...")
print(" ".join(cmd))

with open(log_path, "w") as log:
    proc = subprocess.Popen(
        cmd,
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

print(f"Emulator PID: {proc.pid}")