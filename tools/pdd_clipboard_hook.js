// ============================================================
// PDD 动态安全测试 Hook 脚本 v2.0
// 目标：验证 PDD 通过 Binder 层劫持实时读取 QQ 聊天内容
// 日期：2026-07-17
// 用法：frida -U -f com.xunmeng.pinduoduo -l pdd_clipboard_hook.js --no-pause
// ============================================================

Java.perform(function() {
    console.log("╔══════════════════════════════════════════════════════╗");
    console.log("║   PDD Dynamic Security Test Hook v2.0                ║");
    console.log("║   Target: com.xunmeng.pinduoduo v8.5.0               ║");
    console.log("╚══════════════════════════════════════════════════════╝\n");

    // ============================================================
    // 1. 拦截 SystemServiceHooker.hook() —— 记录所有被劫持的服务
    // ============================================================
    try {
        var SystemServiceHooker = Java.use(
            "com.xunmeng.pinduoduo.service_hook.SystemServiceHooker");
        SystemServiceHooker.hook.implementation = function(ctx, svcName, aidlName, interceptor) {
            console.log("[HOOK-1] SystemServiceHooker.hook()");
            console.log("    Service: " + svcName);
            console.log("    AIDL: " + aidlName);
            console.log("    Interceptor: " + interceptor.getClass().getName());
            return this.hook(ctx, svcName, aidlName, interceptor);
        };
        console.log("[+] Hook 1 installed: SystemServiceHooker.hook()");
    } catch(e) {
        console.log("[-] Hook 1 failed: " + e);
    }

    // ============================================================
    // 2. 拦截 bc2.a.d() —— 记录所有注册的劫持目标
    // ============================================================
    try {
        var bc2_a = Java.use("bc2.a");
        bc2_a.d.implementation = function() {
            console.log("[HOOK-2] bc2.a.d() - Registering service hooks");
            this.d();
        };
        console.log("[+] Hook 2 installed: bc2.a.d()");
    } catch(e) {
        console.log("[-] Hook 2 failed: " + e);
    }

    // ============================================================
    // 3. 拦截 dc2.a —— 剪贴板操作拦截器（核心）
    // ============================================================
    try {
        var dc2_a = Java.use("dc2.a");
        var original_a = dc2_a.a;

        dc2_a.a.implementation = function(svcName, aidlName, dVar, obj, proxy, method, args) {
            var methodName = method.getName();
            if (methodName === "setPrimaryClip") {
                console.log("\n╔══════════════════════════════════════════╗");
                console.log("║  [!] CLIPBOARD WRITE INTERCEPTED!        ║");
                console.log("╚══════════════════════════════════════════╝");
                console.log("    Method: " + methodName);

                if (args && args.length >= 1) {
                    var clipData = args[0];
                    if (clipData != null) {
                        try {
                            var itemCount = clipData.getItemCount();
                            console.log("    ItemCount: " + itemCount);
                            for (var i = 0; i < itemCount; i++) {
                                var item = clipData.getItemAt(i);
                                if (item != null) {
                                    var text = item.getText();
                                    if (text != null) {
                                        console.log("    Text: " + text.toString());
                                    }
                                    var uri = item.getUri();
                                    if (uri != null) {
                                        console.log("    URI: " + uri.toString());
                                    }
                                }
                            }
                        } catch(e2) {
                            console.log("    [Error: " + e2 + "]");
                        }
                    }
                }

                var Exception = Java.use("java.lang.Exception");
                var Log = Java.use("android.util.Log");
                var stackTrace = Log.getStackTraceString(Exception.$new());
                console.log("    Stack:\n" + stackTrace);
                console.log("╚══════════════════════════════════════════╝\n");
            }
            return original_a.call(this, svcName, aidlName, dVar, obj, proxy, method, args);
        };
        console.log("[+] Hook 3 installed: dc2.a.a()");
    } catch(e) {
        console.log("[-] Hook 3 failed: " + e);
    }

    // ============================================================
    // 4. 拦截 dc2.b.a() —— 剪贴板操作上报
    // ============================================================
    try {
        var dc2_b = Java.use("dc2.b");
        dc2_b.a.implementation = function(methodName, throwable) {
            console.log("[HOOK-4] Clipboard operation reported!");
            console.log("    Method: " + methodName);
            var Log = Java.use("android.util.Log");
            console.log("    Stack: " + Log.getStackTraceString(throwable));
            return this.a(methodName, throwable);
        };
        console.log("[+] Hook 4 installed: dc2.b.a()");
    } catch(e) {
        console.log("[-] Hook 4 failed: " + e);
    }

    // ============================================================
    // 5. 拦截 PDD Java 层剪贴板监听
    // ============================================================
    try {
        var z21_a = Java.use("z21.a");
        z21_a.c.implementation = function() {
            var clip = this.c();
            if (clip != null && clip.getItemCount() > 0) {
                var text = clip.getItemAt(0).getText();
                console.log("[HOOK-5] PDD reads clipboard (Java): " + text);
            }
            return clip;
        };
        console.log("[+] Hook 5 installed: z21.a.c()");
    } catch(e) {
        console.log("[-] Hook 5 failed: " + e);
    }

    try {
        var w21_k = Java.use("w21.k");
        w21_k.n.implementation = function(aVar) {
            if (aVar != null) {
                console.log("[HOOK-5b] PDD processes clipboard: " + aVar.c());
            }
            return this.n(aVar);
        };
        console.log("[+] Hook 5b installed: w21.k.n()");
    } catch(e) {
        console.log("[-] Hook 5b failed: " + e);
    }

    // ============================================================
    // 6. 拦截前台应用检测
    // ============================================================
    try {
        var AppUtils = Java.use("com.xunmeng.pinduoduo.basekit.commonutil.AppUtils");
        AppUtils.F.implementation = function(context) {
            var result = this.F(context);
            console.log("[HOOK-6] getRunningTasks(1) → " + result);
            return result;
        };
        console.log("[+] Hook 6 installed: AppUtils.F()");
    } catch(e) {
        console.log("[-] Hook 6 failed: " + e);
    }

    try {
        var AppUtils = Java.use("com.xunmeng.pinduoduo.basekit.commonutil.AppUtils");
        AppUtils.I.implementation = function(context) {
            var result = this.I(context);
            console.log("[HOOK-6b] getRunningAppProcesses() → isForeground: " + result);
            return result;
        };
        console.log("[+] Hook 6b installed: AppUtils.I()");
    } catch(e) {
        console.log("[-] Hook 6b failed: " + e);
    }

    // ============================================================
    // 7. 拦截 QQ 安装状态检测
    // ============================================================
    try {
        var AppUtils = Java.use("com.xunmeng.pinduoduo.basekit.commonutil.AppUtils");
        AppUtils.l.implementation = function(context, packageName) {
            var result = this.l(context, packageName);
            console.log("[HOOK-7] isPackageInstalled: " + packageName + " → " + result);
            return result;
        };
        console.log("[+] Hook 7 installed: AppUtils.l()");
    } catch(e) {
        console.log("[-] Hook 7 failed: " + e);
    }

    // ============================================================
    // 8. 全局系统剪贴板监控（对比层）
    // ============================================================
    try {
        var ClipboardManager = Java.use("android.content.ClipboardManager");
        ClipboardManager.setPrimaryClip.implementation = function(clipData) {
            var text = "";
            if (clipData != null && clipData.getItemCount() > 0) {
                var item = clipData.getItemAt(0);
                if (item != null) {
                    var t = item.getText();
                    text = t != null ? t.toString() : "";
                }
            }
            console.log("[HOOK-8] ★ System Clipboard.setPrimaryClip ★");
            console.log("    Text: " + text.substring(0, Math.min(200, text.length)));

            var Exception = Java.use("java.lang.Exception");
            var Log = Java.use("android.util.Log");
            var stack = Log.getStackTraceString(Exception.$new());
            if (stack.indexOf("com.tencent.mobileqq") !== -1) {
                console.log("    ⚠️  CALLER: QQ (com.tencent.mobileqq) ⚠️");
            }
            return this.setPrimaryClip(clipData);
        };
        console.log("[+] Hook 8 installed: ClipboardManager.setPrimaryClip");
    } catch(e) {
        console.log("[-] Hook 8 failed: " + e);
    }

    console.log("\n╔══════════════════════════════════════════════════════╗");
    console.log("║   All hooks installed. Ready to capture.            ║");
    console.log("║   To test: Open QQ → tap a message → watch output   ║");
    console.log("╚══════════════════════════════════════════════════════╝\n");
});