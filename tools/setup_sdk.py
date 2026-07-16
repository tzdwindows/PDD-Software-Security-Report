import subprocess
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

# Write output to file instead of console
result_path = os.path.join(os.path.dirname(__file__), "license_result.txt")
with open(result_path, "wb") as f:
    f.write(out)
print("License acceptance completed. Check license_result.txt")

# Verify by checking if licenses were accepted
# Now try to install packages
packages = [
    "platform-tools",
    "build-tools;34.0.0",
    "platforms;android-30",
    "system-images;android-30;google_apis;x86_64",
    "emulator"
]

print("Installing SDK packages...")
p2 = subprocess.Popen(
    [sdkmanager, f"--sdk_root={sdk_root}"] + packages,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=False
)
out2, _ = p2.communicate(input=b"y\n", timeout=600)  # Accept any additional prompts

install_path = os.path.join(os.path.dirname(__file__), "install_result.txt")
with open(install_path, "wb") as f:
    f.write(out2)
print("SDK installation completed. Check install_result.txt")