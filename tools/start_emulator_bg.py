import subprocess
import time
import os
import shutil

def force_kill_by_name(process_name):
    """强杀进程并捕获输出"""
    res = subprocess.run(f"taskkill /f /im {process_name}", shell=True, capture_output=True, text=True)
    stderr_clean = res.stderr.strip()
    stdout_clean = res.stdout.strip()
    
    if "not found" in stderr_clean.lower() or "找不到" in stderr_clean or "找不到" in stdout_clean:
        return
        
    if stdout_clean:
        print(f"[#] taskkill({process_name}): {stdout_clean}")
    if stderr_clean:
        print(f"[#] taskkill({process_name}) Error: {stderr_clean}")
        if "拒绝访问" in stderr_clean or "access is denied" in stderr_clean.lower():
            print("[-] [WARNING] 强杀进程被拒绝访问！请尝试以【管理员身份】运行此 Python 脚本。")

def wait_for_file_unlock(filepath, timeout=15):
    """检测并等待关键镜像文件解锁"""
    if not os.path.exists(filepath):
        return True
    
    print(f"[*] Checking if {os.path.basename(filepath)} is locked...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with open(filepath, 'r+b') as f:
                pass
            print(f"[+] {os.path.basename(filepath)} is unlocked and ready.")
            return True
        except IOError:
            time.sleep(1)
            
    print(f"[-] Timeout: {os.path.basename(filepath)} is still locked by another process!")
    return False

def clean_locks_and_remnants():
    """强力解锁并删除残留的锁文件"""
    print("[*] Cleaning up potential emulator locks and processes...")
    
    for name in ["emulator", "qemu-system-x86_64", "qemu-system-x86_64-headless", "adb"]:
        force_kill_by_name(name + ".exe")
        
    print("[*] Waiting 2 seconds for OS to release file handles...")
    time.sleep(2)
        
    user_home = os.path.expanduser("~")
    avd_dir = os.path.join(user_home, ".android", "avd", "pdd_analysis.avd")
    
    if os.path.exists(avd_dir):
        for root, dirs, files in os.walk(avd_dir):
            for d in dirs:
                if d.endswith(".lock"):
                    lock_path = os.path.join(root, d)
                    try:
                        shutil.rmtree(lock_path)
                    except Exception:
                        pass
            for f in files:
                if f.startswith("multiinstance.lock"):
                    lock_file = os.path.join(root, f)
                    try:
                        os.remove(lock_file)
                        print(f"[+] Successfully deleted lock file: {lock_file}")
                    except Exception as e:
                        print(f"[-] Still failed to delete {lock_file}: {e}")

        userdata_path = os.path.join(avd_dir, "userdata-qemu.img.qcow2")
        if not wait_for_file_unlock(userdata_path, timeout=15):
            print("[-] Cannot proceed because userdata file remains locked. Aborting.")
            return False
            
    return True

def start_emulator_background():
    if not clean_locks_and_remnants():
        return False
    
    emulator_path = r"F:\pdd逆向工程\tools\android-sdk\emulator\emulator.exe"
    avd_name = "pdd_analysis"
    
    log_file_path = os.path.join(os.path.dirname(__file__), "emulator.log")
    print(f"[*] Emulator logs will be redirected to: {log_file_path}")
    
    # 【核心改动 1】增加 -no-snapshot-load 强制冷启动，防止旧快照损坏引发无限卡死
    cmd = [
        emulator_path,
        "-avd", avd_name,
        "-gpu", "off",
        "-no-audio",
        "-no-window",
        "-netdelay", "none",
        "-netspeed", "full",
        "-memory", "2048",
        "-cores", "2",
        "-no-snapshot-load",  # 强制冷启动
        "-verbose"
    ]
    
    print(f"[*] Starting emulator: {' '.join(cmd)}")
    
    log_file = open(log_file_path, "w", encoding="utf-8", errors="ignore")
    
    proc = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )
    
    print(f"[*] Emulator Launcher PID: {proc.pid}")
    
    adb_path = r"F:\pdd逆向工程\tools\android-sdk\platform-tools\adb.exe"
    max_wait = 300
    waited = 0
    
    time.sleep(3)
    
    poll = proc.poll()
    if poll is not None and poll != 0:
        print(f"[-] Emulator launcher terminated abnormally with exit code {poll}!")
        log_file.close()
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                print(f"[-] Last 20 lines of log:\n{''.join(f.readlines()[-20:])}")
        except Exception:
            pass
        return False
    elif poll == 0:
        print("[*] Emulator launcher exited successfully (delegated to background QEMU process).")

    log_file.close()

    # 开始循环检测 ADB 连接
    while waited < max_wait:
        time.sleep(5)
        waited += 5
        
        try:
            # 1. 查询当前已连接的设备列表
            devices_check = subprocess.run(
                [adb_path, "devices"],
                capture_output=True, text=True, timeout=5
            )
            
            # 【核心改动 2】精细化解析模拟器的 ADB 状态
            device_state = None
            for line in devices_check.stdout.strip().split("\n"):
                if "emulator-" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        device_state = parts[1]  # 获取状态，例如 'offline', 'device', 'unauthorized'
                        break
            
            # 2. 根据不同的设备状态输出提示
            if device_state == "device":
                # 只有状态达到 'device' 时，查询 sys.boot_completed 才有实际意义
                result = subprocess.run(
                    [adb_path, "shell", "getprop", "sys.boot_completed"],
                    capture_output=True, text=True, timeout=5
                )
                boot_status = result.stdout.strip()
                if boot_status == "1":
                    print(f"[+] Emulator booted successfully! (waited {waited}s)")
                    return True
                else:
                    print(f"[*] Emulator ADB is active (status: device), waiting for system UI framework boot... ({waited}s) [boot_completed: '{boot_status}']")
            elif device_state == "offline":
                print(f"[*] Emulator kernel is booting (status: offline), waiting for ADB interface to wake up... ({waited}s)")
            elif device_state is not None:
                print(f"[*] Emulator detected with status: {device_state}, waiting... ({waited}s)")
            else:
                print(f"[*] Waiting for ADB server to detect virtual device... ({waited}s)")
                
        except subprocess.TimeoutExpired as te:
            print(f"[-] ADB query timed out (normal during boot phase): {te}")
        except Exception as e:
            print(f"[-] ADB query failed: {e}")
        
    print(f"[-] Emulator failed to boot within {max_wait}s.")
    for name in ["emulator", "qemu-system-x86_64", "qemu-system-x86_64-headless"]:
        force_kill_by_name(name + ".exe")
    return False

if __name__ == "__main__":
    start_emulator_background()