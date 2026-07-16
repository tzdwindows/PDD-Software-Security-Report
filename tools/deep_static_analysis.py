# -*- coding: utf-8 -*-
"""Deep static analysis of PDD decompiled source code"""
import os
import re

JADX_SOURCES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jadx_output", "sources")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static_analysis_findings.txt")

patterns = {
    "SYSTEM_ALERT_WINDOW": [r'Settings\.canDrawOverlays', r'SYSTEM_ALERT_WINDOW', r'WindowManager\.LayoutParams\.TYPE_APPLICATION_OVERLAY'],
    "DYNAMIC_LOADING": [r'DexClassLoader', r'PathClassLoader', r'ClassLoader', r'loadClass'],
    "NATIVE_LOADING": [r'System\.loadLibrary', r'System\.load\b'],
    "BINDER_MANIPULATION": [r'readStrongBinder', r'transact\b', r'Parcel\.obtain'],
    "COMMAND_EXECUTION": [r'Runtime\.exec', r'ProcessBuilder'],
    "PACKAGE_INSTALL": [r'pm install', r'pm uninstall', r'PackageInstaller', r'INSTALL_PACKAGES', r'REQUEST_INSTALL_PACKAGES'],
    "REFLECTION": [r'Method\.invoke', r'Field\.set', r'Class\.forName', r'getDeclaredMethod', r'getDeclaredField'],
    "HIDDEN_APP": [r'PackageManager\.setComponentEnabledSetting', r'COMPONENT_ENABLED_STATE_DISABLED', r'getLaunchIntentForPackage'],
    "ACCESSIBILITY": [r'AccessibilityService', r'AccessibilityEvent', r'AccessibilityNodeInfo'],
    "CLIPBOARD": [r'ClipboardManager', r'ClipData', r'getPrimaryClip'],
    "AUDIO_VIDEO": [r'AudioRecord', r'MediaRecorder', r'MediaProjection', r'createScreenCaptureIntent'],
    "DEVICE_ID": [r'getDeviceId', r'IMEI', r'getSubscriberId', r'TelephonyManager', r'getString.*android_id'],
    "LOCATION": [r'LocationManager', r'getLastKnownLocation', r'requestLocationUpdates'],
    "NOTIFICATION_LISTENER": [r'NotificationListenerService'],
    "ALARM_KEEPALIVE": [r'AlarmManager', r'setExactAndAllowWhileIdle', r'setAlarmClock', r'JobScheduler', r'schedule'],
    "WEBSOCKET_LONG_CONN": [r'WebSocket', r'OkHttpClient', r'pingInterval', r'keepAlive'],
    "CRYPTO": [r'Cipher\.getInstance', r'SecretKeySpec', r'IvParameterSpec', r'MessageDigest', r'AES', r'DES'],
    "WEBVIEW_BRIDGE": [r'addJavascriptInterface', r'WebView', r'evaluateJavascript'],
    "SCREENSHOT": [r'ScreenShot', r'screenshot', r'takeScreenshot', r'MediaProjection'],
    "SELF_UPDATE": [r'AppUpdate', r'update', r'apk.*download', r'download.*apk'],
    "CONTENT_PROVIDER_LEAK": [r'ContentProvider', r'query\b', r'content://'],
    "PUSH_PULL_ALIVE": [r'pull_alive', r'push_alive', r'keep.*alive', r'heartbeat'],
    "DESKTOP_SHORTCUT": [r'desk_shortcut', r'installShortcut', r'createShortcut'],
    "FLOATING_WINDOW": [r'msg_floating', r'float.*window', r'FloatWindow'],
    "SENSOR": [r'SensorManager', r'SensorEventListener', r'TYPE_ACCELEROMETER', r'TYPE_GYROSCOPE'],
}

findings = []

def search_file(filepath):
    """Search a single file for patterns"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return []
    
    results = []
    for category, regex_list in patterns.items():
        for regex in regex_list:
            matches = list(re.finditer(regex, content, re.IGNORECASE))
            for m in matches:
                # Get context
                start = max(0, m.start() - 100)
                end = min(len(content), m.end() + 200)
                context = content[start:end].replace('\n', ' ').strip()
                if len(context) > 300:
                    context = context[:300] + "..."
                results.append({
                    'category': category,
                    'match': m.group(),
                    'file': filepath,
                    'context': context
                })
    return results

# Walk through all java files
total_files = 0
found_count = 0

print("Scanning decompiled source files...")
for root, dirs, files in os.walk(JADX_SOURCES):
    for fname in files:
        if fname.endswith('.java'):
            total_files += 1
            filepath = os.path.join(root, fname)
            results = search_file(filepath)
            if results:
                found_count += 1
                findings.extend(results)
                if found_count % 100 == 0:
                    print(f"  Scanned {total_files} files, found {found_count} with matches, {len(findings)} total matches")

print(f"\nTotal files scanned: {total_files}")
print(f"Files with matches: {found_count}")
print(f"Total matches: {len(findings)}")

# Write findings
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("PDD (拼多多) v8.5.0 - Static Analysis Findings\n")
    f.write("=" * 80 + "\n\n")
    
    f.write(f"Total files scanned: {total_files}\n")
    f.write(f"Files with matches: {found_count}\n")
    f.write(f"Total matches: {len(findings)}\n\n")
    
    # Group by category
    from collections import defaultdict
    by_category = defaultdict(list)
    for finding in findings:
        by_category[finding['category']].append(finding)
    
    for category, items in sorted(by_category.items()):
        f.write(f"\n{'='*60}\n")
        f.write(f"CATEGORY: {category}\n")
        f.write(f"Matches: {len(items)}\n")
        f.write(f"{'='*60}\n\n")
        
        # Show first 10 unique files per category
        unique_files = set()
        count = 0
        for item in items:
            if item['file'] not in unique_files:
                unique_files.add(item['file'])
                rel_path = item['file'].replace(JADX_SOURCES + os.sep, '')
                f.write(f"  File: {rel_path}\n")
                f.write(f"  Match: {item['match']}\n")
                f.write(f"  Context: {item['context'][:200]}\n\n")
                count += 1
                if count >= 10:
                    if len(items) > 10:
                        f.write(f"  ... (and {len(items)-10} more matches)\n\n")
                    break

print(f"Results written to: {OUTPUT_FILE}")