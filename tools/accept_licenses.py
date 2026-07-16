import subprocess
import sys
import os

sdk_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "android-sdk")
sdkmanager = os.path.join(sdk_root, "cmdline-tools", "latest", "bin", "sdkmanager.bat")

p = subprocess.Popen(
    [sdkmanager, f"--sdk_root={sdk_root}", "--licenses"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=False
)
out, _ = p.communicate(input=b"y\ny\ny\ny\ny\ny\ny\n", timeout=300)
print(out.decode("utf-8", errors="replace"))