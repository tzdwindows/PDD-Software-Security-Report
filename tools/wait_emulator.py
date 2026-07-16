# -*- coding: utf-8 -*-
"""Poll for emulator to be ready"""
import subprocess
import os
import time

ADB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "android-sdk", "platform-tools", "adb.exe")

print("Waiting for emulator to come online...")
max_wait = 300  # 5 minutes
interval = 5

for i in range(max_wait // interval):
    result = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    output = result.stdout
    
    if "emulator-5554\tdevice" in output:
        print(f"Emulator is ONLINE after {i * interval} seconds!")
        break
    elif "emulator-5554\toffline" in output:
        print(f"[{i * interval}s] Emulator offline, still booting...")
    else:
        print(f"[{i * interval}s] No emulator detected...")
    
    time.sleep(interval)
else:
    print("Timeout! Emulator did not come online in 5 minutes.")
    sys.exit(1)

# Now wait for boot complete
print("Waiting for boot to complete...")
subprocess.run([ADB, "wait-for-device"], capture_output=True)

# Check boot complete
for i in range(60):
    result = subprocess.run(
        [ADB, "shell", "getprop", "sys.boot_completed"],
        capture_output=True, text=True
    )
    if result.stdout.strip() == "1":
        print(f"Boot completed after {i * 2} seconds!")
        break
    time.sleep(2)
else:
    print("Warning: Boot may not have completed yet")

# Enable root
print("Attempting adb root...")
subprocess.run([ADB, "root"], capture_output=True)
time.sleep(3)

# Check if root works
result = subprocess.run([ADB, "shell", "id"], capture_output=True, text=True)
print(f"Root check: {result.stdout.strip()}")

print("Emulator ready for analysis!")