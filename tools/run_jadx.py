# -*- coding: utf-8 -*-
"""Start JADX decompilation in background"""
import subprocess
import os
import sys

JADX_BAT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "jadx", "bin", "jadx.bat")
APK_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "base.apk")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jadx_output")
LOG_PATH = os.path.join(os.path.dirname(__file__), "jadx_log.txt")

# Add JVM memory limit
cmd = [
    JADX_BAT,
    "-d", OUTPUT_DIR,
    "--no-res",  # Skip resource decompilation for speed
    "--threads-count", "4",
    APK_PATH
]

print(f"Starting JADX...")
print(f"Cmd: {' '.join(cmd)}")
print(f"APK: {APK_PATH}")
print(f"Output: {OUTPUT_DIR}")

# Set JAVA_TOOL_OPTIONS to increase memory
env = os.environ.copy()
env["JAVA_TOOL_OPTIONS"] = "-Xmx4g"

with open(LOG_PATH, "w") as log:
    proc = subprocess.Popen(
        cmd,
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

print(f"JADX PID: {proc.pid}")
print("Decompilation started in background. Check jadx_log.txt for progress.")