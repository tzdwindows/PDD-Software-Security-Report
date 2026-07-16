# PDD v8.5.0 用户行为感知机制深度分析报告

> 分析日期：2026-07-17
> 目标：com.xunmeng.pinduoduo v8.5.0
> 核心问题：为什么"预览QQ聊天记录"会触发拼多多推送？

---

## 核心结论

**你点击 QQ 聊天记录时，QQ 很可能自动将消息文字写入了系统剪贴板。** PDD 通过 Binder 层 Hook（`SystemServiceHooker`）拦截了 `android.content.IClipboard` 系统服务，能实时感知**任何应用**（包括 QQ）的剪贴板写入操作。这不是"截图"，而是"剪贴板劫持"。

---

## 1. 技术证据链：Binder 层系统服务劫持

### 1.1 劫持架构

```
应用层 (QQ)  →  setPrimaryClip("某商品链接")
                        │
                        ▼
              ClipboardManager.setPrimaryClip()
                        │
                        ▼
              Binder IPC → android.content.IClipboard
                        │
                        ▼  ← 这里被 PDD 劫持了！
              SystemServiceHooker (动态代理)
                        │
              ┌─────────┴─────────┐
              │                   │
         dc2.a 拦截器         bc2.i 日志记录
         (拦截所有剪贴板操作)    (记录调用栈+进程名)
              │                   │
              ▼                   ▼
         ITracker 上报         Module 30123
         (PMMReport 92006)     Error 101
```

### 1.2 劫持实现代码

**`SystemServiceHooker.hook()`**（`com/xunmeng/pinduoduo/service_hook/SystemServiceHooker.java`）:

```java
public static void hook(Context context, String serviceName, String aidlClassName, i interceptor) {
    // 1. 获取真实 IBinder
    Class<?> cls = Class.forName("android.os.ServiceManager");
    IBinder realBinder = (IBinder) cls.getMethod("getService", String.class).invoke(null, serviceName);

    // 2. 创建动态代理替换 sCache 中的 IBinder
    Map sCache = (Map) cls.getField("sCache").get(null);
    sCache.put(serviceName, Proxy.newProxyInstance(
        cls.getClassLoader(),
        new Class[]{IBinder.class},
        new b(classLoader, realBinder, aidlClassName, interceptor)  // ← 代理所有调用
    ));
}
```

**`bc2.a.d()`** 注册的劫持目标（`bc2/a.java` 第100-133行）:

```java
public final void d() {
    // 劫持 WiFi 服务
    c("wifi", "android.net.wifi.IWifiManager", ...);
    // 劫持 定位服务
    c("location", "android.location.ILocationManager", ...);
    // 劫持 电话状态服务
    c("telephony.registry", "com.android.internal.telephony.ITelephonyRegistry", ...);
    // 劫持 设备标识服务
    c("iphonesubinfo", "com.android.internal.telephony.IPhoneSubInfo", ...);
    // 劫持 电话服务
    c("phone", "com.android.internal.telephony.ITelephony", ...);
    // 劫持 蓝牙服务
    c("bluetooth_manager", "android.bluetooth.IBluetoothManager", ...);
    // 劫持 设备标识策略服务
    c("device_identifiers", "android.os.IDeviceIdentifiersPolicyService", ...);
    // ★ 劫持剪贴板服务 ★
    c("clipboard", "android.content.IClipboard", new dc2.a());
}
```

### 1.3 剪贴板拦截器 `dc2.a`

```java
// dc2/a.java
public class a implements c.a {
    public Set<String> f52560a;  // 拦截的操作集合

    public a() {
        f52560a.add("setPrimaryClip");        // ← 写入剪贴板
        f52560a.add("clearPrimaryClip");       // ← 清空剪贴板
        f52560a.add("getPrimaryClip");         // ← 读取剪贴板
        f52560a.add("getPrimaryClipDescription");
        f52560a.add("hasPrimaryClip");
        f52560a.add("addPrimaryClipChangedListener");
        f52560a.add("removePrimaryClipChangedListener");
        f52560a.add("hasClipboardText");
    }

    @Override
    public d a(String serviceName, String aidlName, d result,
               Object service, Object proxy, Method method, Object[] args) {
        String methodName = method.getName();
        // 对于 setPrimaryClip/clearPrimaryClip/addPrimaryClipChangedListener/
        // removePrimaryClipChangedListener/getPrimaryClip/getPrimaryClipDescription:
        // → 拦截并返回 null
        // 对于 hasPrimaryClip/hasClipboardText:
        // → 拦截并返回 false
        // ...
        if (bc2.b.e() && this.f52560a.contains(methodName)) {
            b.a(methodName, new Throwable());  // ← 上报调用者信息
        }
        return result;
    }
}
```

### 1.4 调用者追踪 `dc2.b`

```java
// dc2/b.java - 每次剪贴板操作都被记录
public static void a(String methodName, Throwable th) {
    ThreadPool.getInstance().ioTask(ThreadBiz.SA, "ClipboardReporter#reportSync", new a(th, methodName, isForeground, timestamp));
}

// a.run() 记录:
// - method: 剪贴板操作方法名
// - trace: 完整调用栈（包含调用者进程名）
// - foreground: 是否前台
// - caller_time: 调用时间
// - process: 当前进程名
// → ITracker.error().Module(30123).Msg("caller_report").Error(101)
```

---

## 2. 为什么"点击QQ聊天"会触发

### 2.1 QQ 的自动复制行为

当你在 QQ 中**点击（长按或短按）聊天消息**时，QQ 可能会执行以下操作之一：

1. **自动复制消息文字到剪贴板**（部分版本 QQ 在点击消息时触发）
2. **将消息内容写入剪贴板用于内部"智能"功能**
3. **弹出菜单时预加载剪贴板内容**

这些操作都会调用 `ClipboardManager.setPrimaryClip()`，PDD 的 Binder 层 Hook 会立即拦截。

### 2.2 PDD 的响应链

```
QQ 写入剪贴板（如："我在拼多多买了件衣服，链接是..."）
    │
    ▼
SystemServiceHooker 截获 setPrimaryClip 调用
    │
    ├─ dc2.a 拦截器记录操作
    ├─ dc2.b 上报调用者信息（Module 30123, Error 101）
    │
    ▼
PDD 的 Java 层剪贴板监听器 z21.a → w21.k 也被触发
    │
    ▼
w21.k.k() 被调用 → r() 读取剪贴板内容
    │
    ▼
x21 处理器链匹配关键词（URL/商品名/拼多多链接）
    │
    ▼
匹配成功 → 触发推送/弹窗
```

### 2.3 双重监听机制

PDD 同时使用了两套剪贴板监听机制：

| 层级 | 类 | 机制 |
|------|-----|------|
| **Binder 层** | `dc2.a` + `SystemServiceHooker` | 劫持 `IClipboard` 系统服务，全局拦截所有应用的剪贴板操作 |
| **Java 层** | `z21.a` + `w21.k` | 通过 `ClipboardManager.addPrimaryClipChangedListener()` 监听本进程可见的剪贴板变化 |

**Binder 层劫持的优势**：即使 PDD 在后台、被系统杀死部分进程，只要 Hook 已注入 `ServiceManager` 的 `sCache`，它就能持续拦截所有剪贴板操作。

---

## 3. 前台应用检测机制

PDD 能知道"你正在用 QQ"，因为它检测前台应用：

### 3.1 `AppUtils.F()` - 获取前台任务

```java
// AppUtils.java 第182-192行
public static int F(Context context) {
    ActivityManager am = (ActivityManager) context.getSystemService("activity");
    List<ActivityManager.RunningTaskInfo> runningTasks = am.getRunningTasks(1);
    // runningTasks.get(0) 就是当前前台 Activity
    return runningTasks.get(0).numActivities;
}
```

### 3.2 `AppUtils.I()` - 检测自身是否前台

```java
// AppUtils.java 第194-215行
public static boolean I(Context context) {
    List<ActivityManager.RunningAppProcessInfo> processes = am.getRunningAppProcesses();
    for (RunningAppProcessInfo info : processes) {
        if (info.processName.equals(packageName) && info.importance == 100) {
            return true;  // IMPORTANCE_FOREGROUND
        }
    }
    return false;
}
```

### 3.3 `c3.k.i()` - Shell 命令检测进程

```java
// c3/k.java 第260-413行
// 运行 "ps | grep <processName>" 来检测指定进程是否运行
// 可检测 QQ (com.tencent.mobileqq) 是否在运行
```

---

## 4. 已安装应用检测

`AppUtils` 内部类 `c` 缓存了常见应用的安装状态：

```java
// AppUtils.java 第165-180行
public void run() {
    f28304g = Arrays.asList(
        "com.unionpay",           // 银联
        "com.tencent.mm",         // 微信
        "com.tencent.mobileqq",   // ★ QQ
        "com.eg.android.AlipayGphone",  // 支付宝
        "hk.alipay.wallet"        // 支付宝HK
    );
    for (String pkg : f28304g) {
        boolean installed = isPackageInstalled(pkg);  // 检查是否安装
        f28305h.put(pkg, installed ? 1 : 0);         // 缓存结果
    }
}
```

PDD 在启动时就会检测 QQ 是否安装，并缓存这个信息。

---

## 5. 截图机制的实际用途

回到用户的第一个问题"他搞这个到底是有什么用"：

### 5.1 `ImageSearchScreenShotProxyActivity` 的用途

这是**应用内的"以图搜图"功能**，不是用来监控 QQ 的：

1. 用户在 PDD 中看到商品
2. 点击"以图搜图"按钮
3. 系统弹出 MediaProjection 授权弹窗
4. 用户同意后，截取当前屏幕
5. 上传截图到 PDD 服务器做图像搜索
6. 返回相似商品结果

**这个功能需要用户主动触发 + 系统授权弹窗**，不能静默截图。

### 5.2 `ScreenshotManagerV2` 的用途

这是**系统截图监听**，用于检测用户是否手动截了屏（电源键+音量键）：

- 通过 `ContentObserver` 监听 `MediaStore.Images`
- 通过 `BroadcastReceiver` 监听 `miui.intent.TAKE_SCREENSHOT`
- 当检测到新截图 → 提示用户"是否用图片搜索同款"

**这个功能也不需要权限**，因为它只是读取系统相册中已存在的截图文件。

---

## 6. 动态验证指南（Frida Hook）

### 6.1 验证"QQ 是否自动复制"

```javascript
// Hook 1: 拦截所有应用的 setPrimaryClip 调用
var ClipboardManager = Java.use("android.content.ClipboardManager");
ClipboardManager.setPrimaryClip.implementation = function(clipData) {
    var text = "";
    if (clipData != null && clipData.getItemCount() > 0) {
        var item = clipData.getItemAt(0);
        if (item != null) {
            text = item.getText();
        }
    }
    console.log("[!] setPrimaryClip called!");
    console.log("    Text: " + text);
    console.log("    Stack: " + Java.use("android.util.Log").getStackTraceString(
        Java.use("java.lang.Exception").$new()));
    return this.setPrimaryClip(clipData);
};
```

### 6.2 验证 PDD 的 Binder 层劫持

```javascript
// Hook 2: 拦截 SystemServiceHooker.hook()
var SystemServiceHooker = Java.use(
    "com.xunmeng.pinduoduo.service_hook.SystemServiceHooker");
SystemServiceHooker.hook.implementation = function(ctx, svcName, aidlName, interceptor) {
    console.log("[!] SystemServiceHooker.hook()");
    console.log("    Service: " + svcName);
    console.log("    AIDL: " + aidlName);
    return this.hook(ctx, svcName, aidlName, interceptor);
};

// Hook 3: 拦截 dc2.b.a() - 剪贴板操作上报
var dc2_b = Java.use("dc2.b");
dc2_b.a.implementation = function(methodName, throwable) {
    console.log("[!] Clipboard operation intercepted: " + methodName);
    console.log("    Stack: " + Java.use("android.util.Log").getStackTraceString(throwable));
    return this.a(methodName, throwable);
};

// Hook 4: 拦截 bc2.a.d() - 查看所有被劫持的服务
var bc2_a = Java.use("bc2.a");
bc2_a.d.implementation = function() {
    console.log("[!] bc2.a.d() - Registering service hooks");
    this.d();
};
```

### 6.3 验证 PDD 读取剪贴板内容

```javascript
// Hook 5: 拦截 z21.a.c() - PDD 读取剪贴板
var z21_a = Java.use("z21.a");
z21_a.c.implementation = function() {
    var clip = this.c();
    if (clip != null && clip.getItemCount() > 0) {
        var text = clip.getItemAt(0).getText();
        console.log("[!] PDD reads clipboard: " + text);
    }
    return clip;
};

// Hook 6: 拦截 w21.k.n() - PDD 处理剪贴板数据
var w21_k = Java.use("w21.k");
w21_k.n.implementation = function(aVar) {
    if (aVar != null) {
        console.log("[!] PDD processes clipboard data");
        console.log("    Label: " + aVar.d());
        console.log("    Text: " + aVar.c());
    }
    return this.n(aVar);
};
```

### 6.4 验证前台应用检测

```javascript
// Hook 7: 拦截 AppUtils.F() - 获取前台任务
var AppUtils = Java.use("com.xunmeng.pinduoduo.basekit.commonutil.AppUtils");
AppUtils.F.implementation = function(context) {
    var result = this.F(context);
    console.log("[!] AppUtils.F() getRunningTasks: " + result);
    return result;
};
```

---

## 7. 总结

| 你的问题 | 答案 |
|---------|------|
| 截图机制是干什么的？ | 以图搜图（需用户主动触发 + 系统授权弹窗），不是监控你的 |
| 为什么点 QQ 聊天记录就推送？ | QQ 自动复制了消息文字到剪贴板，PDD 的 Binder 层 Hook 立即拦截到 |
| PDD 怎么知道我在用 QQ？ | `getRunningTasks(1)` + `getRunningAppProcesses()` + 启动时检测 QQ 是否安装 |
| 这是截图吗？ | **不是。** 是剪贴板劫持 + 前台应用检测 |