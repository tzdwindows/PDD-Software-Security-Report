import subprocess
import os
import sys
import time

# Paths
SDK_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "android-sdk")
AVD_NAME = "pdd_analysis"
AVD_HOME = os.path.join(os.path.expanduser("~"), ".android", "avd")
AVD_INI = os.path.join(os.path.expanduser("~"), ".android", "avd", f"{AVD_NAME}.ini")

# Create AVD directory
os.makedirs(AVD_HOME, exist_ok=True)

# Write AVD config
config_ini_content = f"""avd.ini.encoding=UTF-8
path={AVD_HOME}\\{AVD_NAME}.avd
path.rel=avd\\{AVD_NAME}.avd
target=android-30
"""

with open(AVD_INI, "w") as f:
    f.write(config_ini_content)

# Create AVD directory
avd_dir = os.path.join(AVD_HOME, f"{AVD_NAME}.avd")
os.makedirs(avd_dir, exist_ok=True)

# Write config.ini for the AVD
avd_config = f"""AvdId={AVD_NAME}
PlayStore.enabled=false
abi.type=x86_64
avd.ini.displayname=PDD Analysis AVD
avd.ini.encoding=UTF-8
disk.dataPartition.size=4096M
fastboot.chosenSnapshotFile=
fastboot.forceChosenSnapshotBoot=no
fastboot.forceColdBoot=no
fastboot.forceFastBoot=yes
hw.accelerometer=yes
hw.audioInput=yes
hw.battery=yes
hw.camera.back=emulated
hw.camera.front=emulated
hw.cpu.arch=x86_64
hw.cpu.ncore=4
hw.dPad=no
hw.device.hash2=MD5:55acbc83517f5454c3a8ca7fe1f45b49
hw.device.manufacturer=Google
hw.device.name=pixel_4
hw.gps=yes
hw.gpu.enabled=yes
hw.gpu.mode=auto
hw.initialOrientation=portrait
hw.keyboard=yes
hw.lcd.density=420
hw.lcd.height=1920
hw.lcd.width=1080
hw.mainKeys=no
hw.ramSize=2048
hw.sdCard=yes
hw.sensors.proximity=yes
hw.trackBall=no
image.sysdir.1=system-images\\android-30\\google_apis\\x86_64\\
runtime.network.latency=none
runtime.network.speed=full
sdcard.size=512M
showDeviceFrame=no
skin.dynamic=yes
skin.name=pixel_4
skin.path={SDK_ROOT}\\skins\\pixel_4
tag.display=Google APIs
tag.id=google_apis
vm.heapSize=256
"""

with open(os.path.join(avd_dir, "config.ini"), "w") as f:
    f.write(avd_config)

# Also write hardware-qemu.ini
hw_qemu = """hw.cpu.arch = x86_64
hw.cpu.ncore = 4
hw.ramSize = 2048
hw.screen = multi-touch
hw.mainKeys = false
hw.trackBall = false
hw.keyboard = true
hw.keyboard.lid = false
hw.keyboard.charmap = qwerty2
hw.dPad = false
hw.gsmModem = true
hw.gps = true
hw.battery = true
hw.accelerometer = true
hw.audioInput = true
hw.audioOutput = true
hw.sdCard = true
hw.sdCard.path = 
disk.cachePartition = true
disk.cachePartition.path = 
disk.cachePartition.size = 66M
hw.lcd.width = 1080
hw.lcd.height = 1920
hw.lcd.depth = 16
hw.lcd.density = 420
hw.lcd.backlight = true
hw.gpu.enabled = true
hw.gpu.mode = host
hw.initialOrientation = portrait
hw.camera.back = emulated
hw.camera.front = emulated
vm.heapSize = 256
hw.sensors.proximity = true
hw.sensors.magnetic_field = true
hw.sensors.orientation = true
hw.sensors.temperature = true
hw.useext4 = true
kernel.path = 
kernel.parameters = androidboot.hardware=ranchu
disk.ramdisk.path = 
disk.systemPartition.initPath = 
disk.systemPartition.size = 
disk.vendorPartition.initPath = 
disk.vendorPartition.size = 
disk.dataPartition.path = 
disk.dataPartition.size = 4096M
disk.encryptionKeyPartition.path = 
avd.name = {AVD_NAME}
fastboot.forceColdBoot = false
hw.cpu.model = qemu64
"""

with open(os.path.join(avd_dir, "hardware-qemu.ini"), "w") as f:
    f.write(hw_qemu)

print(f"AVD '{AVD_NAME}' created successfully!")
print(f"AVD directory: {avd_dir}")

# Now start the emulator
emulator_exe = os.path.join(SDK_ROOT, "emulator", "emulator.exe")
print(f"Starting emulator: {emulator_exe}")

# Start emulator in background
cmd = [
    emulator_exe,
    "-avd", AVD_NAME,
    "-writable-system",
    "-no-snapshot",
    "-netdelay", "none",
    "-netspeed", "full",
    "-memory", "2048",
    "-gpu", "swiftshader_indirect",
    "-no-audio",
    "-no-boot-anim"
]

print(f"Command: {' '.join(cmd)}")

# Start in background and write PID
process = subprocess.Popen(
    cmd,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    stdin=subprocess.DEVNULL
)

# Write PID to file
with open(os.path.join(os.path.dirname(__file__), "emulator_pid.txt"), "w") as f:
    f.write(str(process.pid))

print(f"Emulator started with PID: {process.pid}")
print("Waiting for emulator to boot...")
print("Run 'adb wait-for-device' to check when ready.")