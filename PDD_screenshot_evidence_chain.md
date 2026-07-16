# PDD v8.5.0 截图/相册监控证据链深度分析报告

> 分析日期：2026-07-17
> 目标：com.xunmeng.pinduoduo v8.5.0 (base.apk)
> 反编译工具：JADX 1.5.6 | 总文件：24,827 | 命中：31,246

---

## 1. 截图触发与授权规避（Initiation & Authorization Bypass）

### 1.1 核心组件拓扑

```
ImageSearchScreenShotProxyActivity (taskAffinity=".ImageSearchProxy")
    │
    ├─ onCreate() → MediaProjectionManager → d()
    │
    ├─ d() ─── 三条路径 ───┐
    │                      │
    │  ┌─ API<34 且单例已有授权 ─→ p() → ScreenShotAdapterService.startForeground()
    │  │                           └→ h() → u1(intent, resultCode=-1, ...) → 直接截图
    │  │
    │  ├─ API<34 无授权 ─→ j1(createScreenCaptureIntent(), 1000)
    │  │                  └→ startActivityForResult → 系统弹窗
    │  │
    │  └─ API≥34 ─→ j1(createScreenCaptureIntent(config), 1000)
    │              └→ startActivityForResult → 系统弹窗
    │
    ├─ onActivityResult(1000, RESULT_OK, intent)
    │   └→ a.f().a(intent, -1)  // 存入单例
    │   └→ p()  // 启动前台服务
    │   └→ postDelayed(300ms) → u1(intent, -1, ...) → s1(mediaProjection, ...)
    │
    └─ s1() → VirtualDisplay("pdd-screen") + ImageReader → OnImageAvailableListener
```

### 1.2 授权规避机制深度分析

**关键发现一：`ScreenShotAdapterService` 是 MediaProjection 的生命周期锚点**

```java
// AndroidManifest.xml
<service
    android:name="com.xunmeng.pinduoduo.image_search.floating.ScreenShotAdapterService"
    android:foregroundServiceType="mediaProjection"   // ← 关键！
    android:exported="false"/>
```

该服务声明了 `foregroundServiceType="mediaProjection"`，这是 Android 10+ 引入的前台服务类型。**它使得 MediaProjection 的生命周期可以绑定到 Service 而非 Activity**，从而：
- 绕过 Activity 被销毁后 MediaProjection 自动失效的限制
- 在后台持续持有截图权限

**关键发现二：单例状态管理器 `a.java` 跨组件传递授权状态**

```java
// floating/a.java (单例)
public class a {
    public Intent f36122a;     // 存储 MediaProjection Intent
    public int f36123b;        // 存储 resultCode (RESULT_OK = -1)
    CopyOnWriteArrayList<InterfaceC0463a> f36124c;  // 监听者列表

    public boolean d() {
        return this.f36122a != null && this.f36123b == -1;  // 已有授权
    }
}
```

**攻击链**：用户首次授权后，`Intent` + `resultCode=-1` 被持久化到单例中。后续调用 `d()` 时检测到已有授权，**直接跳过系统弹窗**，走 `p()` → `h()` → `u1()` 路径进行静默截图。

**关键发现三：`taskAffinity=".ImageSearchProxy"` 的隐蔽性设计**

```xml
<activity
    android:name="com.xunmeng.pinduoduo.image_search.floating.ImageSearchScreenShotProxyActivity"
    android:taskAffinity=".ImageSearchProxy"    // ← 独立任务栈
    android:exported="false"/>
```

独立 `taskAffinity` 意味着该 Activity 在独立任务栈中运行，**不会出现在主任务栈的最近任务列表中**，降低被用户察觉的概率。

**关键发现四：Android 14+ 适配的 `MediaProjectionConfig`**

```java
// d() 方法中 Android 14+ 路径
if (this.J0) {  // AB 测试配置: ab_image_search_screen_shot_config_78800
    j1(k.b(this.f36101x0,
        MediaProjectionConfig.createConfigForDefaultDisplay(),  // Android 14+ 新API
        "com.xunmeng.pinduoduo.image_search.floating.ImageSearchScreenShotProxyActivity"), 1000);
}
```

Android 14 要求必须使用 `MediaProjectionConfig.createConfigForDefaultDisplay()`（而非旧的 `createScreenCaptureIntent()`），PDD 已通过 AB 测试配置 `J0` 布尔值进行动态适配。

### 1.3 高价值特征关键字

| 特征字符串 | 位置 | 含义 |
|-----------|------|------|
| `"capture_screen"` | `qa2/k.java`, `bb2/a.java` | 敏感 API 追踪标签 |
| `"fw_h"` ~ `"fw_i"` | `gm1/b.java`, `ImageSearchScreenShotProxyActivity` | 截图操作步骤埋点(共9步) |
| `"pdd-screen"` | `ImageSearchScreenShotProxyActivity.o1()` | VirtualDisplay 名称 |
| `"camera_icon_album"` | `ImageSearchScreenShotProxyActivity.l1()` | 截图搜索来源标记 |
| `"10667"` | `ImageSearchScreenShotProxyActivity.l1()` | 浮动窗口截图 source ID |
| `"ab_image_search_screen_shot_config_78800"` | `ImageSearchScreenShotProxyActivity.c()` | AB 测试配置键 |
| `"screen_shot_adapter_service"` | `ScreenShotAdapterService.a()` | 前台通知渠道 ID |
| `"com.xunmeng.pinduoduo.image_search.action.GET_PROJECTION"` | `ScreenShotAdapterService`, `ImageSearchScreenShotProxyActivity` | 服务间通信 Action |
| `"com.xunmeng.pinduoduo.image_search.action.START_FOREGROUND"` | `ScreenShotAdapterService`, `ImageSearchScreenShotProxyActivity` | 启动前台服务 Action |

---

## 2. 图像数据的提取与加工（Data Extraction & Processing）

### 2.1 数据流向全链路

```
【捕获层】VirtualDisplay("pdd-screen")
    │  Surface → ImageReader (format=RGBA_8888, maxImages=3)
    │
    ▼
【回调层】ImageReader.OnImageAvailableListener (内部类 g)
    │  → m1(boolean z14, boolean z15, ImageReader imageReader)
    │
    ├─ imageReader.acquireLatestImage()
    ├─ image.getPlanes()[0] → Plane.getBuffer() → ByteBuffer (原始像素)
    ├─ 黑帧检测: buffer.getInt(buffer.capacity()/2) == 0 → 丢弃
    ├─ Bitmap.createBitmap(width, height, ARGB_8888)
    ├─ bitmap.copyPixelsFromBuffer(buffer)
    └─ l1(bitmap, z15)
         │
         ▼
【转换层】l1(Bitmap bitmap, boolean z14)
    │  → ByteBuffer.allocate(bitmap.getByteCount())
    │  → bitmap.copyPixelsToBuffer(byteBuffer)
    │  → JumpProps:
    │      .setImageDimension(width, height)
    │      .setSearchMet("camera_icon_album")
    │      .setSource("10667")
    │
    ▼
【路由层】ml1.d.d(context, byteBuffer, source)
    │  → ISearchImageUploadService.uploadImage(uuid, byteBuffer, jumpProps, runnable)
    │  → Router.build("ImageSearchUploadService").getModuleService(...)
    │
    ▼
【结果层】sjs_search_img.html (WebView)
    │  → 展示以图搜图结果
    │  → 图片数据已上传至服务端
```

### 2.2 图像处理细节

**黑帧过滤机制**（`m1()` 方法）：
```java
// 检查图像中间像素是否为纯黑（全0），用于过滤无效/全黑帧
if (buffer.getInt(buffer.capacity() / 2) == 0) {
    image.close();
    return;  // 丢弃黑帧
}
```

**配置参数**（来自 AB 测试 `ab_image_search_screen_shot_config_78800`）：
```java
// 格式: "max_frames,timeout_ms,use_config_api"
// 默认: H0=10 (最大帧数), I0=30000 (超时30s), J0=false
String[] split = stringValue.split(",");
this.H0 = Integer.parseInt(split[0]);  // 最大截图次数
this.I0 = Long.parseLong(split[1]);    // 超时时间
this.J0 = Boolean.parseBoolean(split[2]);  // 是否使用 MediaProjectionConfig
```

### 2.3 Native 层图像搜索引擎

| 类 | SO 库 | 功能 |
|----|-------|------|
| `ImageSearchSessionJni` | `libimage_search_mobile.so` | 通用图片搜索（静态图） |
| `ImageSearchSimpleSessionJni` | `libimage_search_mobile.so` | 简化图片搜索 |
| `ImageSearchVideoSessionJni` | `libimage_search_mobile.so` | 视频帧搜索（含 `frames_url` + `frames_jpeg` 数据读取器） |

三者均继承 `AlmightyCommonSessionJni`，属于拼多多自研的 **Almighty AI 框架**。`ImageSearchVideoSessionJni` 的构造函数中注册了 `VectorPnnDataReader` 用于读取视频帧 URL 和 JPEG 数据，**表明存在视频帧级别的图像搜索能力**。

`ImageSearchAlmightServiceImpl.preload()` 调用 `am1.f.l()` 预加载 native 模型，实现快速启动。

### 2.4 相册监听机制（ScreenshotManagerV2）

**ContentObserver 监听**（`ScreenshotManagerV2` 内部类 `e`）：
```java
// 注册监听 MediaStore.Images.Media.EXTERNAL_CONTENT_URI
ContentObserver observer = new e(
    qa2.c.l("com.xunmeng.pinduoduo.common.screenshot.ScreenshotManagerV2"), // → MediaStore.Images.Media.EXTERNAL_CONTENT_URI
    handler
);
contentResolver.registerContentObserver(uri, notifyForDescendants, observer);
```

**BroadcastReceiver 监听**（`ScreenReceiver`）：
```java
// 监听 MIUI 等厂商的截图广播
this.f31442k = Collections.singletonList("miui.intent.TAKE_SCREENSHOT");
```

**文件名过滤规则**（`f31432a` 列表）：
```
"screenshot", "screen_shot", "screen-shot", "screen shot",
"screencapture", "screen_capture", "screen-capture", "screen capture",
"screencap", "screen_cap", "screen-cap", "screen cap", "截屏"
```

**查询字段**：`_data`, `datetaken`, `width`, `height`

**触发流程**：
1. `ContentObserver.onChange()` → `q(uri)` → `postDelayed(f, 300ms)` → `d(uri)`
2. `d(uri)` 查询 `MediaStore` 获取最新截图元数据
3. 对文件名做关键词匹配（`a()` 方法返回 0 表示匹配成功）
4. 匹配成功 → 通知已注册的 `g51.e` 回调（`h()` 方法）
5. 回调中携带截图路径 `_data` 和元数据 Map

### 2.5 高价值特征关键字

| 特征字符串 | 位置 | 含义 |
|-----------|------|------|
| `"pdd-screen"` | `ImageSearchScreenShotProxyActivity.o1()` | VirtualDisplay 标识 |
| `"image_search_mobile"` | `ImageSearchSessionJni`, `ImageSearchSimpleSessionJni`, `ImageSearchVideoSessionJni` | Native SO 名称 |
| `"frames_url"`, `"frames_jpeg"` | `ImageSearchVideoSessionJni` | 视频帧数据读取器 |
| `"VectorPnnDataReader"` | `ImageSearchVideoSessionJni` | 向量数据读取器 |
| `"sjs_search_img.html"` | `ml1/d.java` | 图片搜索结果页 |
| `"ImageSearchUploadService"` | `ml1/d.java` | Router 服务名 |
| `"ab_image_search_auto_scan_switch_72400"` | `ml1/d.java` | 自动扫描开关 |
| `"ab_image_search_auto_scan_switch_79300"` | `ImageSearchAlmightServiceImpl` | 本地焦点自动扫描 |
| `"miui.intent.TAKE_SCREENSHOT"` | `ScreenshotManagerV2` | MIUI 截图广播 |
| `"base.screenshot_path"` | `ScreenshotManagerV2` | 配置键：截图路径过滤词 |
| `"base.screenshot_send_interval"` | `ScreenshotManagerV2` | 配置键：发送间隔(默认300ms) |
| `"ScreenshotManagerV2#postScreenShotTask"` | `ScreenshotManagerV2.q()` | 延时任务标识 |

---

## 3. 隐蔽的数据传输（Covert Exfiltration）

### 3.1 传输协议分析

**上传入口**：`ISearchImageUploadService`（Router 动态加载）
```java
public interface ISearchImageUploadService extends ModuleService {
    void uploadImage(String uuid, ByteBuffer byteBuffer, JumpProps jumpProps, Runnable callback);
    void uploadImage(String uuid, JumpProps jumpProps);
}
```

**上传数据包结构**（`ml1.d.d()` 构建）：
```json
{
    "pic_cache_id": "<36位UUID>",
    "file_path": "<本地缓存路径>",
    "search_met": "camera_icon_album",
    "page_source": "10667",
    "image_upload_id": "<36位UUID>",
    "goods_id": "<商品ID>",       // 可选
    "activity_style_": 2
}
```

**关键发现**：
- `search_met` 字段区分了多种截图来源：`"camera_icon_album"`（浮动窗口）、`"goods_dtl_screenshot"`（商品详情截图）、`"goods_dtl_pic_storage"`（商品详情相册）
- `source` 字段标记了不同的入口：`"10667"`（浮动窗口）、`"10057"`（商品详情页）
- 图片数据以 `ByteBuffer` 形式直接传入，**不经文件系统落盘**（除非 `byteBuffer == null` 时走文件路径上传）

### 3.2 埋点追踪体系

所有截图操作通过 `gm1.b` 类上报至 PMMReport（事件 ID: **92006**）：

| 埋点标记 | 触发位置 | 含义 |
|---------|---------|------|
| `fw_h` | `onCreate()` | 截图流程开始 |
| `fw_f1` | `g()` | 截图未授权 |
| `fw_f2` | `u1()` | getMediaProjection 失败 |
| `fw_f3` | `b.a()` | s1() 失败 |
| `fw_f4` | `g.onImageAvailable()` | 超过最大帧数 |
| `fw_f5` | `a.run()` | 截图超时(30s) |
| `fw_f6` | `n()` | 截图失败通用 |
| `fw_f7` | `onBackPressed()` | 用户返回 |
| `fw_g` | `l1()` | 截图成功，bitmap 已发送 |
| `fw_i` | `onDestroy()` | 截图流程结束 |

### 3.3 敏感 API 追踪

`bb2.a` 类对所有 `MediaProjection` 相关 API 调用进行埋点追踪：
```java
bb2.a.g("capture_screen", "createScreenCaptureIntent", callerClassName);
bb2.a.g("capture_screen", "createScreenCaptureIntent(config)", callerClassName);
bb2.a.g("capture_screen", "getMediaProjection", callerClassName);
```

### 3.4 Meco 引擎关联分析

Meco 容器（`libmeco_cookie.so`）在本截图链中**未直接参与**。但：
- `ml1.d.d()` 最终跳转到 `sjs_search_img.html`（WebView 页面）
- PDD 使用 Meco 作为 WebView 容器（`cc1/g.java`, `cc1/h.java`）
- 图片搜索结果通过 Meco WebView 渲染，上传请求可能走 Meco 的 `OkHttpClient`（`bf1/d.java`）

**结论**：Meco 在此充当的是"结果展示容器"而非"数据上报白名单通道"，但上传请求和 WebView 渲染均通过 Meco 的 HTTP 栈。

### 3.5 高价值特征关键字

| 特征字符串 | 位置 | 含义 |
|-----------|------|------|
| `"ImageSearchUploadService"` | `ml1/d.java` | Router 服务名 |
| `"sjs_search_img.html"` | `ml1/d.java` | 搜索结果页 |
| `"search_image_capture.html"` | `ml1/d.java` | 拍照搜索页 |
| `"camera_icon_album"` | `ImageSearchScreenShotProxyActivity.l1()` | 浮动窗口截图标记 |
| `"goods_dtl_screenshot"` | `ak1/q2.java` | 商品详情截图标记 |
| `"10057"`, `"10667"` | 多处 | 页面来源 ID |
| `92006` | `gm1/b.java` | PMMReport 事件 ID |
| `"capture_screen"` | `bb2/a.java`, `qa2/k.java` | 敏感 API 追踪标签 |

---

## 4. 动态取证指南：Frida Hook 目标清单

### 4.1 MediaProjection 授权拦截

```javascript
// Hook 1: 拦截 createScreenCaptureIntent（捕获截图意图触发）
var MediaProjectionManager = Java.use("android.media.projection.MediaProjectionManager");
MediaProjectionManager.createScreenCaptureIntent.overload().implementation = function() {
    console.log("[!] MediaProjectionManager.createScreenCaptureIntent()");
    console.log("    Stack: " + Java.use("android.util.Log").getStackTraceString(
        Java.use("java.lang.Exception").$new()));
    return this.createScreenCaptureIntent();
};

// Hook 2: 拦截 qa2.k.c() —— PDD 的 createScreenCaptureIntent 包装器
var k = Java.use("qa2.k");
k.c.implementation = function(manager, callerName) {
    console.log("[!] qa2.k.c() createScreenCaptureIntent");
    console.log("    Caller: " + callerName);
    var result = this.c(manager, callerName);
    console.log("    Intent: " + result);
    return result;
};

// Hook 3: 拦截 qa2.k.d() —— getMediaProjection 包装器
k.d.implementation = function(manager, resultCode, intent, callerName) {
    console.log("[!] qa2.k.d() getMediaProjection");
    console.log("    resultCode: " + resultCode);
    console.log("    Caller: " + callerName);
    return this.d(manager, resultCode, intent, callerName);
};

// Hook 4: 拦截 ScreenShotAdapterService —— 获取 MediaProjection 的前台服务
var ScreenShotAdapterService = Java.use(
    "com.xunmeng.pinduoduo.image_search.floating.ScreenShotAdapterService");
ScreenShotAdapterService.onStartCommand.implementation = function(intent, flags, startId) {
    console.log("[!] ScreenShotAdapterService.onStartCommand()");
    console.log("    Action: " + (intent ? intent.getAction() : "null"));
    return this.onStartCommand(intent, flags, startId);
};

// Hook 5: 拦截 ImageSearchScreenShotProxyActivity.s1() —— VirtualDisplay 创建
var ProxyActivity = Java.use(
    "com.xunmeng.pinduoduo.image_search.floating.ImageSearchScreenShotProxyActivity");
ProxyActivity.s1.implementation = function(mediaProjection, z14, z15) {
    console.log("[!] ImageSearchScreenShotProxyActivity.s1()");
    console.log("    mediaProjection: " + mediaProjection);
    console.log("    z14: " + z14 + ", z15: " + z15);
    return this.s1(mediaProjection, z14, z15);
};

// Hook 6: 拦截单例 a.f().d() —— 检查是否已有授权
var FloatingA = Java.use("com.xunmeng.pinduoduo.image_search.floating.a");
FloatingA.d.implementation = function() {
    var result = this.d();
    console.log("[!] floating.a.d() hasAuth: " + result);
    console.log("    intent: " + this.f36122a.value);
    console.log("    resultCode: " + this.f36123b.value);
    return result;
};
```

### 4.2 ImageReader 图像回调拦截（保存截图到本地）

```javascript
// Hook 7: 拦截 ImageReader.OnImageAvailableListener
var ProxyActivity = Java.use(
    "com.xunmeng.pinduoduo.image_search.floating.ImageSearchScreenShotProxyActivity");

// Hook m1() —— 图像数据提取
ProxyActivity.m1.implementation = function(z14, z15, imageReader) {
    console.log("[!] ImageSearchScreenShotProxyActivity.m1()");
    console.log("    z14: " + z14 + ", z15: " + z15);

    var image = imageReader.acquireLatestImage();
    if (image !== null) {
        try {
            var planes = image.getPlanes();
            var plane = planes[0];
            var buffer = plane.getBuffer();
            var width = image.getWidth();
            var height = image.getHeight();
            var pixelStride = plane.getPixelStride();
            var rowStride = plane.getRowStride();

            console.log("    width: " + width + ", height: " + height);
            console.log("    pixelStride: " + pixelStride + ", rowStride: " + rowStride);

            // 保存原始 Buffer 到本地文件
            var bytes = Java.array('byte', new Array(buffer.remaining()));
            buffer.get(bytes);
            var fos = Java.use("java.io.FileOutputStream").$new(
                "/data/local/tmp/screenshot_" + Date.now() + ".raw");
            fos.write(bytes);
            fos.close();
            console.log("    [+] Saved raw buffer to /data/local/tmp/");

            // 重建 Bitmap 并保存为 PNG
            var Bitmap = Java.use("android.graphics.Bitmap");
            var bitmap = Bitmap.createBitmap(
                ((rowStride - (pixelStride * width)) / pixelStride) + width,
                height, Bitmap.Config.ARGB_8888.value);
            buffer.position(0);
            bitmap.copyPixelsFromBuffer(buffer);

            var realBitmap = Bitmap.createBitmap(bitmap, 0, 0, width, height);
            var fos2 = Java.use("java.io.FileOutputStream").$new(
                "/data/local/tmp/screenshot_" + Date.now() + ".png");
            realBitmap.compress(Bitmap.CompressFormat.PNG.value, 100, fos2);
            fos2.close();
            console.log("    [+] Saved PNG to /data/local/tmp/");

            if (realBitmap !== bitmap && !bitmap.isRecycled()) {
                bitmap.recycle();
            }
        } catch (e) {
            console.log("    [-] Error: " + e);
        } finally {
            image.close();
        }
    }
    return this.m1(z14, z15, imageReader);
};

// Hook 8: 拦截 l1() —— 图片上传前的最后处理
ProxyActivity.l1.implementation = function(bitmap, z14) {
    console.log("[!] ImageSearchScreenShotProxyActivity.l1()");
    console.log("    bitmap: " + bitmap + " (w=" + bitmap.getWidth() +
                ", h=" + bitmap.getHeight() + ")");
    console.log("    z14: " + z14);
    return this.l1(bitmap, z14);
};

// Hook 9: 拦截 o1() —— VirtualDisplay 创建
ProxyActivity.o1.implementation = function(width, height, density, z14, z15) {
    console.log("[!] ImageSearchScreenShotProxyActivity.o1()");
    console.log("    width: " + width + ", height: " + height + ", density: " + density);
    return this.o1(width, height, density, z14, z15);
};
```

### 4.3 ContentObserver 相册监听拦截

```javascript
// Hook 10: 拦截 ContentResolver.registerContentObserver
var ContentResolver = Java.use("android.content.ContentResolver");
ContentResolver.registerContentObserver.overload(
    'android.net.Uri', 'boolean', 'android.database.ContentObserver'
).implementation = function(uri, notifyForDescendants, observer) {
    var uriStr = uri.toString();
    if (uriStr.indexOf("external/images/media") !== -1 ||
        uriStr.indexOf("MediaStore") !== -1) {
        console.log("[!] ContentResolver.registerContentObserver()");
        console.log("    URI: " + uriStr);
        console.log("    notifyForDescendants: " + notifyForDescendants);
        console.log("    Observer: " + observer.getClass().getName());
        Java.use("android.util.Log").getStackTraceString(
            Java.use("java.lang.Exception").$new());
    }
    return this.registerContentObserver(uri, notifyForDescendants, observer);
};

// Hook 11: 拦截 ScreenshotManagerV2 的 ContentObserver (内部类 e)
var ScreenshotManagerV2 = Java.use(
    "com.xunmeng.pinduoduo.common.screenshot.ScreenshotManagerV2");
// 注意：内部类 e 的完整路径
var ContentObserverE = Java.use(
    "com.xunmeng.pinduoduo.common.screenshot.ScreenshotManagerV2$e");
ContentObserverE.onChange.overload('boolean', 'android.net.Uri').implementation =
function(z14, uri) {
    console.log("[!] ScreenshotManagerV2$e.onChange()");
    console.log("    URI: " + uri);
    console.log("    selfChange: " + z14);
    return this.onChange(z14, uri);
};

// Hook 12: 拦截 ScreenshotManagerV2.d() —— 截图数据查询
ScreenshotManagerV2.d.implementation = function(uri) {
    console.log("[!] ScreenshotManagerV2.d()");
    console.log("    URI: " + uri);
    this.d(uri);
};

// Hook 13: 拦截 ScreenshotManagerV2.q() —— 延时任务入队
ScreenshotManagerV2.q.implementation = function(uri) {
    console.log("[!] ScreenshotManagerV2.q()");
    console.log("    URI: " + uri);
    this.q(uri);
};

// Hook 14: 拦截 ScreenshotManagerV2.A() —— 注册 ContentObserver
ScreenshotManagerV2.A.implementation = function() {
    console.log("[!] ScreenshotManagerV2.A() - registerContentObserver");
    Java.use("android.util.Log").getStackTraceString(
        Java.use("java.lang.Exception").$new());
    this.A();
};

// Hook 15: 拦截 ScreenReceiver.onReceive() —— 截图广播
var ScreenReceiver = Java.use(
    "com.xunmeng.pinduoduo.common.screenshot.ScreenshotManagerV2$ScreenReceiver");
ScreenReceiver.onReceive.implementation = function(context, intent) {
    console.log("[!] ScreenReceiver.onReceive()");
    console.log("    Action: " + intent.getAction());
    return this.onReceive(context, intent);
};
```

### 4.4 数据传输拦截

```javascript
// Hook 16: 拦截 ISearchImageUploadService.uploadImage()
// 注意：这是一个接口，需要找到实现类。通过 Router 查找
var Router = Java.use("com.xunmeng.router.Router");
Router.build.implementation = function(name) {
    console.log("[!] Router.build(): " + name);
    return this.build(name);
};

// Hook 17: 拦截 ml1.d.d() —— 图片上传分发
var ml1_d = Java.use("ml1.d");
ml1_d.d.implementation = function(context, byteBuffer, jumpProps) {
    console.log("[!] ml1.d.d() - uploadImage");
    console.log("    searchMet: " + jumpProps.getSearchMet());
    console.log("    source: " + jumpProps.getSource());
    console.log("    width: " + jumpProps.getImageWidth() +
                ", height: " + jumpProps.getImageHeight());
    if (byteBuffer !== null) {
        console.log("    buffer size: " + byteBuffer.capacity());
        // 可选：保存上传前的 ByteBuffer
        var bytes = Java.array('byte', new Array(byteBuffer.capacity()));
        byteBuffer.position(0);
        byteBuffer.get(bytes);
        var fos = Java.use("java.io.FileOutputStream").$new(
            "/data/local/tmp/upload_" + Date.now() + ".raw");
        fos.write(bytes);
        fos.close();
    }
    return this.d(context, byteBuffer, jumpProps);
};

// Hook 18: 拦截 gm1.b 埋点追踪
var gm1_b = Java.use("gm1.b");
gm1_b.a.implementation = function(str) {
    console.log("[!] gm1.b.a() - op: " + str);
    return this.a(str);
};
gm1_b.m.implementation = function(map, map2, map3) {
    console.log("[!] gm1.b.m() - PMMReport 92006");
    console.log("    map: " + map);
    console.log("    map2: " + map2);
    return this.m(map, map2, map3);
};

// Hook 19: 拦截 bb2.a.g() —— 敏感 API 追踪
var bb2_a = Java.use("bb2.a");
bb2_a.g.implementation = function(str, str2, str3) {
    console.log("[!] bb2.a.g() - SensitiveAPI: " + str + "/" + str2 + " from " + str3);
    return this.g(str, str2, str3);
};
```

### 4.5 Native 层 Hook

```javascript
// Hook 20: 拦截 libimage_search_mobile.so 的 JNI 注册
var image_search_mobile = Module.findBaseAddress("libimage_search_mobile.so");
if (image_search_mobile) {
    console.log("[+] libimage_search_mobile.so base: " + image_search_mobile);
    var exports = Module.enumerateExports("libimage_search_mobile.so");
    exports.forEach(function(exp) {
        if (exp.name.indexOf("registerJni") !== -1 ||
            exp.name.indexOf("reset") !== -1) {
            console.log("    " + exp.name + " @ " + exp.address);
            Interceptor.attach(exp.address, {
                onEnter: function(args) {
                    console.log("[!] " + exp.name + " called");
                },
                onLeave: function(retval) {
                    console.log("    ret: " + retval);
                }
            });
        }
    });
}

// Hook 21: 拦截 libdokodoor.so 的 JNI_OnLoad
var dokodoor = Module.findBaseAddress("libdokodoor.so");
if (dokodoor) {
    console.log("[+] libdokodoor.so base: " + dokodoor);
    var jni_onload = Module.findExportByName("libdokodoor.so", "JNI_OnLoad");
    if (jni_onload) {
        Interceptor.attach(jni_onload, {
            onEnter: function(args) {
                console.log("[!] libdokodoor.so JNI_OnLoad called");
            }
        });
    }
}
```

### 4.6 快速 Hook 脚本模板（完整 Frida 脚本）

```javascript
// pdd_screenshot_hook.js —— 完整 Hook 脚本
Java.perform(function() {
    console.log("[*] PDD Screenshot Hook Script v2.0");
    console.log("[*] Target: com.xunmeng.pinduoduo v8.5.0");

    // ===== 1. MediaProjection 授权 =====
    var k = Java.use("qa2.k");
    k.c.implementation = function(mgr, name) {
        console.log("[HOOK] createScreenCaptureIntent from: " + name);
        return this.c(mgr, name);
    };
    k.d.implementation = function(mgr, code, intent, name) {
        console.log("[HOOK] getMediaProjection code=" + code + " from: " + name);
        return this.d(mgr, code, intent, name);
    };

    // ===== 2. 图像捕获 =====
    var Proxy = Java.use("com.xunmeng.pinduoduo.image_search.floating.ImageSearchScreenShotProxyActivity");
    Proxy.o1.implementation = function(w, h, d, z1, z2) {
        console.log("[HOOK] VirtualDisplay creating: " + w + "x" + h + " density=" + d);
        return this.o1(w, h, d, z1, z2);
    };
    Proxy.l1.implementation = function(bitmap, z) {
        console.log("[HOOK] Bitmap to upload: " + bitmap.getWidth() + "x" + bitmap.getHeight());
        // 保存 PNG
        try {
            var fos = Java.use("java.io.FileOutputStream").$new(
                "/data/local/tmp/pdd_cap_" + Date.now() + ".png");
            bitmap.compress(Java.use("android.graphics.Bitmap").CompressFormat.PNG.value, 100, fos);
            fos.close();
            console.log("[+] Saved to /data/local/tmp/");
        } catch(e) {}
        return this.l1(bitmap, z);
    };

    // ===== 3. 相册监听 =====
    var SMV2 = Java.use("com.xunmeng.pinduoduo.common.screenshot.ScreenshotManagerV2");
    SMV2.A.implementation = function() {
        console.log("[HOOK] ScreenshotManagerV2 registering ContentObserver");
        return this.A();
    };
    var CO = Java.use("com.xunmeng.pinduoduo.common.screenshot.ScreenshotManagerV2$e");
    CO.onChange.overload('boolean', 'android.net.Uri').implementation = function(z, uri) {
        console.log("[HOOK] Screenshot ContentObserver fired: " + uri);
        return this.onChange(z, uri);
    };

    // ===== 4. 上传拦截 =====
    var d = Java.use("ml1.d");
    d.d.implementation = function(ctx, buf, props) {
        console.log("[HOOK] Upload image: searchMet=" + props.getSearchMet() +
                    " source=" + props.getSource());
        return this.d(ctx, buf, props);
    };

    console.log("[*] All hooks installed.");
});
```

---

## 附录：证据链总结

```
┌─────────────────────────────────────────────────────────────────┐
│                    截图/相册监控证据链                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [触发层]                                                        │
│  ├─ 用户截图 (电源+音量) → BroadcastReceiver/ScreenshotManagerV2 │
│  ├─ 应用主动截图 → ImageSearchScreenShotProxyActivity            │
│  └─ 浮动窗口触发 → floating.a 单例状态检查                       │
│                                                                 │
│  [授权层]                                                        │
│  ├─ MediaProjectionManager.createScreenCaptureIntent()           │
│  ├─ ScreenShotAdapterService (foregroundServiceType=mediaProject)│
│  └─ floating.a 单例跨组件传递授权状态                             │
│                                                                 │
│  [捕获层]                                                        │
│  ├─ VirtualDisplay("pdd-screen") → ImageReader(RGBA_8888)       │
│  └─ ContentObserver → MediaStore.Images.EXTERNAL_CONTENT_URI     │
│                                                                 │
│  [处理层]                                                        │
│  ├─ Bitmap → ByteBuffer (内存中，不落盘)                         │
│  ├─ 黑帧检测 (buffer.getInt(capacity/2) == 0)                   │
│  └─ Native: libimage_search_mobile.so (Almighty AI 特征提取)     │
│                                                                 │
│  [传输层]                                                        │
│  ├─ ISearchImageUploadService.uploadImage()                     │
│  ├─ 跳转 sjs_search_img.html (Meco WebView)                     │
│  └─ PMMReport 92006 全链路埋点                                   │
│                                                                 │
│  [隐蔽手段]                                                      │
│  ├─ taskAffinity=".ImageSearchProxy" 独立任务栈                   │
│  ├─ 前台服务伪装 ("用于图片搜索的截图服务")                       │
│  ├─ AB 测试动态配置 (远程开关)                                    │
│  └─ 敏感 API 自监控 (bb2.a 埋点)                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```