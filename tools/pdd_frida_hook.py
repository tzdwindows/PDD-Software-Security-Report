# -*- coding: utf-8 -*-
"""
Frida Dynamic Hook Script for PDD (拼多多) v8.5.0
Package: com.xunmeng.pinduoduo
Usage: frida -U -f com.xunmeng.pinduoduo -l pdd_hook.js --no-pause
"""
import frida
import sys

JS_CODE = """
// ============================================================
// PDD Dynamic Analysis Hook Script
// Target: com.xunmeng.pinduoduo v8.5.0
// ============================================================

// 1. SSL Unpinning - bypass certificate validation
Java.perform(function() {
    console.log("[*] PDD Hook: Starting SSL Unpinning...");
    
    // Hook OkHttp CertificatePinner
    try {
        var CertificatePinner = Java.use("okhttp3.CertificatePinner");
        CertificatePinner.check.overload('java.lang.String', 'java.util.List').implementation = function(hostname, peerCertificates) {
            console.log("[SSL] CertificatePinner.check bypassed for: " + hostname);
            return;
        };
    } catch(e) { console.log("[!] OkHttp CertificatePinner hook failed: " + e); }
    
    // Hook TrustManager
    try {
        var TrustManagerImpl = Java.use("com.android.org.conscrypt.TrustManagerImpl");
        TrustManagerImpl.verifyChain.implementation = function(untrustedChain, trustAnchorChain, host, clientAuth, endpoint, session) {
            console.log("[SSL] TrustManager verifyChain bypassed for: " + host);
            return untrustedChain;
        };
    } catch(e) { console.log("[!] TrustManager hook failed: " + e); }
});

// 2. Network Request Interception
Java.perform(function() {
    console.log("[*] PDD Hook: Starting Network Monitoring...");
    
    // Hook OkHttp RealCall.execute
    try {
        var RealCall = Java.use("okhttp3.RealCall");
        RealCall.execute.implementation = function() {
            var request = this.request();
            var url = request.url().toString();
            var method = request.method();
            console.log("[HTTP] " + method + " " + url);
            
            // Log POST body
            if (method == "POST" || method == "PUT") {
                var body = request.body();
                if (body != null) {
                    console.log("[HTTP BODY] " + body.toString());
                }
            }
            
            var response = this.execute();
            var code = response.code();
            console.log("[HTTP RESP] " + url + " -> " + code);
            return response;
        };
    } catch(e) { console.log("[!] RealCall hook failed: " + e); }
    
    // Hook OkHttp enqueue (async)
    try {
        var RealCall = Java.use("okhttp3.RealCall");
        RealCall.enqueue.implementation = function(callback) {
            var request = this.request();
            var url = request.url().toString();
            var method = request.method();
            console.log("[HTTP ASYNC] " + method + " " + url);
            
            var Callback = Java.use("okhttp3.Callback");
            var originalCallback = callback;
            var hookedCallback = Java.registerClass({
                name: "com.hook.ProxyCallback",
                implements: [Callback],
                methods: {
                    onResponse: function(call, response) {
                        console.log("[HTTP ASYNC RESP] " + url + " -> " + response.code());
                        originalCallback.onResponse(call, response);
                    },
                    onFailure: function(call, e) {
                        console.log("[HTTP ASYNC FAIL] " + url + " -> " + e.toString());
                        originalCallback.onFailure(call, e);
                    }
                }
            });
            this.enqueue(hookedCallback.$new());
        };
    } catch(e) { console.log("[!] RealCall.enqueue hook failed: " + e); }
});

// 3. Binder Communication Monitoring
Java.perform(function() {
    console.log("[*] PDD Hook: Starting Binder Monitoring...");
    
    try {
        var Binder = Java.use("android.os.Binder");
        Binder.transact.implementation = function(code, data, reply, flags) {
            var result = this.transact(code, data, reply, flags);
            console.log("[BINDER] transact code=" + code + " flags=" + flags);
            return result;
        };
    } catch(e) { console.log("[!] Binder.transact hook failed: " + e); }
    
    try {
        var Parcel = Java.use("android.os.Parcel");
        Parcel.obtain.implementation = function() {
            var parcel = this.obtain();
            console.log("[PARCEL] Parcel.obtain() called from: " + Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()));
            return parcel;
        };
    } catch(e) { console.log("[!] Parcel.obtain hook failed: " + e); }
});

// 4. Sensitive API Monitoring
Java.perform(function() {
    console.log("[*] PDD Hook: Starting Sensitive API Monitoring...");
    
    // Hook System.loadLibrary
    try {
        var System = Java.use("java.lang.System");
        System.loadLibrary.implementation = function(libname) {
            console.log("[NATIVE] System.loadLibrary: " + libname);
            console.log(Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()));
            return this.loadLibrary(libname);
        };
    } catch(e) { console.log("[!] System.loadLibrary hook failed: " + e); }
    
    // Hook DexClassLoader
    try {
        var DexClassLoader = Java.use("dalvik.system.DexClassLoader");
        DexClassLoader.$init.overload('java.lang.String', 'java.lang.String', 'java.lang.String', 'java.lang.ClassLoader').implementation = function(dexPath, optimizedDir, libPath, parent) {
            console.log("[DEX] DexClassLoader loading: " + dexPath);
            console.log("[DEX] Optimized dir: " + optimizedDir);
            return this.$init(dexPath, optimizedDir, libPath, parent);
        };
    } catch(e) { console.log("[!] DexClassLoader hook failed: " + e); }
    
    // Hook Runtime.exec
    try {
        var Runtime = Java.use("java.lang.Runtime");
        Runtime.exec.overload('[Ljava.lang.String;').implementation = function(cmd) {
            console.log("[EXEC] Runtime.exec: " + cmd);
            console.log(Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()));
            return this.exec(cmd);
        };
    } catch(e) { console.log("[!] Runtime.exec hook failed: " + e); }
    
    // Hook ProcessBuilder
    try {
        var ProcessBuilder = Java.use("java.lang.ProcessBuilder");
        ProcessBuilder.start.implementation = function() {
            var cmd = this.command();
            console.log("[EXEC] ProcessBuilder.start: " + cmd);
            console.log(Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()));
            return this.start();
        };
    } catch(e) { console.log("[!] ProcessBuilder hook failed: " + e); }
    
    // Hook ClipboardManager
    try {
        var ClipboardManager = Java.use("android.content.ClipboardManager");
        ClipboardManager.setPrimaryClip.implementation = function(clip) {
            if (clip != null && clip.getItemCount() > 0) {
                var text = clip.getItemAt(0).getText();
                console.log("[CLIPBOARD] setPrimaryClip: " + text);
            }
            return this.setPrimaryClip(clip);
        };
        ClipboardManager.getPrimaryClip.implementation = function() {
            var clip = this.getPrimaryClip();
            if (clip != null && clip.getItemCount() > 0) {
                var text = clip.getItemAt(0).getText();
                console.log("[CLIPBOARD] getPrimaryClip read: " + text);
            }
            return clip;
        };
    } catch(e) { console.log("[!] ClipboardManager hook failed: " + e); }
    
    // Hook AudioRecord
    try {
        var AudioRecord = Java.use("android.media.AudioRecord");
        AudioRecord.startRecording.implementation = function() {
            console.log("[AUDIO] AudioRecord.startRecording() called!");
            console.log(Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()));
            return this.startRecording();
        };
    } catch(e) { console.log("[!] AudioRecord hook failed: " + e); }
    
    // Hook MediaProjection
    try {
        var MediaProjectionManager = Java.use("android.media.projection.MediaProjectionManager");
        MediaProjectionManager.createScreenCaptureIntent.implementation = function() {
            console.log("[SCREEN] createScreenCaptureIntent called!");
            console.log(Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()));
            return this.createScreenCaptureIntent();
        };
    } catch(e) { console.log("[!] MediaProjection hook failed: " + e); }
    
    // Hook AccessibilityService
    try {
        var AccessibilityService = Java.use("android.accessibilityservice.AccessibilityService");
        AccessibilityService.onAccessibilityEvent.implementation = function(event) {
            console.log("[A11Y] AccessibilityEvent: " + event.toString());
            return this.onAccessibilityEvent(event);
        };
    } catch(e) { console.log("[!] AccessibilityService hook failed: " + e); }
    
    // Hook LocationManager
    try {
        var LocationManager = Java.use("android.location.LocationManager");
        LocationManager.requestLocationUpdates.implementation = function(provider, minTime, minDistance, listener) {
            console.log("[LOCATION] requestLocationUpdates: provider=" + provider + " minTime=" + minTime);
            console.log(Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()));
            return this.requestLocationUpdates(provider, minTime, minDistance, listener);
        };
    } catch(e) { console.log("[!] LocationManager hook failed: " + e); }
    
    // Hook TelephonyManager - device ID access
    try {
        var TelephonyManager = Java.use("android.telephony.TelephonyManager");
        TelephonyManager.getDeviceId.implementation = function() {
            console.log("[DEVICE] getDeviceId() called!");
            console.log(Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()));
            return this.getDeviceId();
        };
        TelephonyManager.getImei.implementation = function() {
            console.log("[DEVICE] getImei() called!");
            console.log(Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()));
            return this.getImei();
        };
    } catch(e) { console.log("[!] TelephonyManager hook failed: " + e); }
    
    // Hook PackageManager.setComponentEnabledSetting (hide app icon)
    try {
        var PackageManager = Java.use("android.content.pm.PackageManager");
        PackageManager.setComponentEnabledSetting.implementation = function(componentName, newState, flags) {
            console.log("[HIDE] setComponentEnabledSetting: " + componentName + " state=" + newState);
            console.log(Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()));
            return this.setComponentEnabledSetting(componentName, newState, flags);
        };
    } catch(e) { console.log("[!] PackageManager hook failed: " + e); }
    
    // Hook Settings.canDrawOverlays
    try {
        var Settings = Java.use("android.provider.Settings");
        Settings.canDrawOverlays.implementation = function(context) {
            var result = this.canDrawOverlays(context);
            console.log("[OVERLAY] canDrawOverlays: " + result);
            return result;
        };
    } catch(e) { console.log("[!] Settings.canDrawOverlays hook failed: " + e); }
    
    // Hook WebView.addJavascriptInterface
    try {
        var WebView = Java.use("android.webkit.WebView");
        WebView.addJavascriptInterface.implementation = function(obj, name) {
            console.log("[WEBVIEW] addJavascriptInterface: name=" + name + " obj=" + obj.getClass().getName());
            console.log(Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()));
            return this.addJavascriptInterface(obj, name);
        };
    } catch(e) { console.log("[!] WebView.addJavascriptInterface hook failed: " + e); }
    
    // Hook AlarmManager (keepalive)
    try {
        var AlarmManager = Java.use("android.app.AlarmManager");
        AlarmManager.setExactAndAllowWhileIdle.implementation = function(type, triggerAtMillis, operation) {
            console.log("[ALARM] setExactAndAllowWhileIdle: type=" + type + " triggerAt=" + triggerAtMillis);
            console.log(Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()));
            return this.setExactAndAllowWhileIdle(type, triggerAtMillis, operation);
        };
    } catch(e) { console.log("[!] AlarmManager hook failed: " + e); }
    
    // Hook ContentProvider.query
    try {
        var ContentProvider = Java.use("android.content.ContentProvider");
        ContentProvider.query.implementation = function(uri, projection, selection, selectionArgs, sortOrder) {
            console.log("[CP] ContentProvider.query: " + uri.toString());
            return this.query(uri, projection, selection, selectionArgs, sortOrder);
        };
    } catch(e) { console.log("[!] ContentProvider.query hook failed: " + e); }
    
    console.log("[*] PDD Hook: All hooks installed successfully!");
});

// 5. Anti-detection bypass
Java.perform(function() {
    // Hook Build fields to fake device info
    try {
        var Build = Java.use("android.os.Build");
        // Override isEmulator check
        var BuildClass = Java.use("android.os.Build").class;
    } catch(e) {}
    
    // Hook PackageManager to hide frida
    try {
        var PM = Java.use("android.app.ApplicationPackageManager");
        PM.getInstalledApplications.implementation = function(flags) {
            var apps = this.getInstalledApplications(flags);
            console.log("[PM] getInstalledApplications called, returning " + apps.size() + " apps");
            return apps;
        };
    } catch(e) {}
});

console.log("[*] === PDD Analysis Hook Ready ===");
"""

def on_message(message, data):
    if message['type'] == 'send':
        print(f"[FRIDA] {message['payload']}")
    elif message['type'] == 'error':
        print(f"[FRIDA ERROR] {message.get('description', message)}")

def main():
    package_name = "com.xunmeng.pinduoduo"
    
    try:
        device = frida.get_usb_device()
        print(f"[*] Connected to device: {device}")
        
        pid = device.spawn([package_name])
        print(f"[*] Spawned {package_name} with PID: {pid}")
        
        session = device.attach(pid)
        script = session.create_script(JS_CODE)
        script.on('message', on_message)
        script.load()
        
        device.resume(pid)
        print("[*] Resumed! Monitoring...")
        sys.stdin.read()
        
    except frida.ServerNotStartedError:
        print("[!] Frida server not running! Start frida-server on device first.")
        print("[!] Run: adb shell su -c '/data/local/tmp/frida-server-17.15.5-android-x86_64 &'")
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    main()