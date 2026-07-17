# PDD 逆向工程与安全审计项目

> **拼多多 (com.xunmeng.pinduoduo) v8.5.0 + QQ — 深度安全审计**
>
> 静态代码分析 + 动态行为分析 + 双向逆向证据链

---

## 项目概述

本项目对拼多多 Android 客户端 v8.5.0 进行了全面的安全审计，同时逆向分析了 QQ 客户端以验证数据通道。覆盖 PDD 24,827 个 Java 源文件 + QQ 21,267 个 Java 源文件。

**核心发现：PDD 通过 `ScreenshotManagerV2` 的 ContentObserver 监控 Android 系统相册（MediaStore），结合自研 AI 图片识别引擎（`libimage_search_mobile.so`），在用户截取 PDD 商品图片后自动识别并推送推荐。同时 PDD 通过 `SystemServiceHooker` 劫持了 8 个 Android 系统服务。**

---

## 项目结构

```
F:\pdd逆向工程\
├── README.md                                     # 本文件
├── base.apk                                      # 目标 PDD APK (25.9 MB)
├── base_QQ.apk                                   # 目标 QQ APK (403 MB)
├── jadx_output\                                  # PDD JADX 反编译输出
│   └── sources\                                  # 24,827 个 Java 源文件
├── qq_jadx_output\                               # QQ JADX 反编译输出
│   └── sources\                                  # 21,267 个 Java 源文件
├── tools\                                        # 工具链与脚本
│   ├── pdd_frida_hook.py                         # 综合 Frida 动态 Hook 脚本
│   ├── pdd_clipboard_hook.js                     # 剪贴板劫持专项 Hook 脚本
│   ├── deep_static_analysis.py                   # 深度静态分析脚本
│   └── ...                                       # 其他工具脚本
└── 报告文档\
    ├── ultimate_security_report.md               # 综合安全审计报告
    ├── PDD_behavior_perception_analysis.md        # 用户行为感知机制深度分析
    ├── PDD_screenshot_evidence_chain.md           # 截图/相册监控证据链
    ├── PDD_dynamic_security_testing_report.md     # 动态安全测试报告（最终版）
    └── static_analysis_findings.txt               # 静态分析原始结果
```

---

## 报告导航

| 报告 | 内容 | 适用场景 |
|------|------|---------|
| **[ultimate_security_report.md](ultimate_security_report.md)** | 全面的静态安全审计，涵盖权限、保活、截图、剪贴板、URL Scheme、WebView | 了解 PDD 的整体安全风险 |
| **[PDD_behavior_perception_analysis.md](PDD_behavior_perception_analysis.md)** | Binder 层劫持完整证据链，SystemServiceHooker 深度分析 | 理解剪贴板劫持的技术原理 |
| **[PDD_screenshot_evidence_chain.md](PDD_screenshot_evidence_chain.md)** | 截图/相册监控的完整证据链，含 MediaProjection、VirtualDisplay、ImageReader | 深入理解 PDD 的屏幕捕获能力 |
| **[PDD_dynamic_security_testing_report.md](PDD_dynamic_security_testing_report.md)** | **最终版动态安全测试报告**，含 QQ 逆向分析 + 系统相册监控机制 + Frida 验证脚本 | 全面了解 PDD 隐私侵犯行为 |
| **[static_analysis_findings.txt](static_analysis_findings.txt)** | 31,246 个敏感模式匹配的原始结果 | 快速检索特定安全模式 |

---

## 核心发现速览

### 🔴 Critical：Android 系统相册监控（ContentObserver）

PDD 的 `ScreenshotManagerV2` 注册了 ContentObserver 监控 `MediaStore.Images.Media.EXTERNAL_CONTENT_URI`，实时检测 Android 系统相册中所有新增图片。当用户截取 PDD 商品页面截图时，系统自动将截图存入相册，PDD 检测到后通过 AI 图片识别引擎匹配商品。

| 组件 | 功能 |
|------|------|
| `ScreenshotManagerV2` | ContentObserver 监控系统相册（1154 行） |
| `ImageSearchAlmightServiceImpl` | AI 图片搜索引擎 |
| `libimage_search_mobile.so` | Native AI 引擎（商品特征提取） |

### 🔴 Critical：Binder 层系统服务劫持

PDD 的 `SystemServiceHooker` 直接修改 `ServiceManager.sCache`，劫持了 **8 个系统服务**：

| 系统服务 | 泄露数据 |
|---------|---------|
| `clipboard` (IClipboard) | 所有应用的剪贴板操作 |
| `location` (ILocationManager) | 精准位置 |
| `wifi` (IWifiManager) | WiFi 连接信息 |
| `telephony.registry` | 电话状态、基站 |
| `iphonesubinfo` | IMEI/设备标识 |
| `phone` | 电话操作 |
| `bluetooth_manager` | 蓝牙信息 |
| `device_identifiers` | 设备标识策略 |

### 🔴 Critical：用户行为感知

- **前台应用检测**：`getRunningTasks(1)` + `getRunningAppProcesses()` + shell 命令
- **QQ 安装检测**：启动时缓存 QQ/微信/支付宝等关键应用的安装状态
- **设备指纹**：CPU、内存、存储、进程全方位采集

### 🟠 High：其他高风险行为

- **屏幕截图服务**：`ScreenShotAdapterService` + `MediaProjectionManager`，名义"以图搜图"
- **多进程保活**：9 个进程 + 6 厂商推送 SDK + AlarmService + JobScheduler + Titan 长连接
- **隐藏桌面图标**：4 个 LAUNCHER Activity，含 `PandaHmActivity` 隐藏入口
- **15+ URL Scheme**：含混淆 Scheme `qngaccv79cv29i://`

---

## 你遇到的"QQ 聊天触发 PDD 推荐"现象

### 真正发生了什么

```
群聊中有人截了 PDD 商品页面截图 → 发到 QQ 群
  → Android 系统自动把截图存入系统相册 (/Pictures/Screenshots/)
  → PDD 的 ScreenshotManagerV2 ContentObserver 检测到新图片
  → libimage_search_mobile.so AI 引擎识别图片中的商品
  → 商品匹配 → 推送推荐
```

### 为什么朋友也收到相同推荐

因为大家看到的都是同一张 PDD 商品截图，PDD 的图片识别引擎对同一张图片返回相同的商品匹配结果。

### 调查历程（经过三轮假设修正）

| 轮次 | 假设 | 结论 |
|------|------|------|
| 第一轮 | QQ 写剪贴板 → PDD Binder 劫持 | ❌ QQ 生产版不写剪贴板 |
| 第二轮 | 腾讯广告生态 (GDT/AMS) 数据共享 | ❌ 腾讯不售卖聊天记录 |
| **最终** | **PDD 监控 Android 系统相册 + AI 图片识别** | ✅ **代码级证据完整** |

### 详细分析

详见 **[PDD_dynamic_security_testing_report.md](PDD_dynamic_security_testing_report.md)**。

---

## 快速开始：动态验证

### 前置条件

- Root 真机（或可用模拟器）
- ADB 已连接
- Frida 环境已安装

### 1. 安装目标 APK

```bash
adb install base.apk
```

### 2. 部署 Frida Server

```bash
adb push tools/frida/frida-server-17.15.5-android-x86_64 /data/local/tmp/
adb shell chmod 755 /data/local/tmp/frida-server-17.15.5-android-x86_64
```

### 3. 启动 Frida 并注入 Hook

```bash
adb shell su -c '/data/local/tmp/frida-server-17.15.5-android-x86_64 &'
adb forward tcp:27042 tcp:27042

# 使用 Python 版综合 Hook 脚本（监控 15+ 类行为）
python tools/pdd_frida_hook.py

# 或使用 JS 版剪贴板专项 Hook 脚本
frida -U -f com.xunmeng.pinduoduo -l tools/pdd_clipboard_hook.js --no-pause
```

### 4. 复现测试

1. 在 PDD App 中截图一张商品页面
2. 观察 Frida 输出，确认 `ScreenshotManagerV2` ContentObserver 触发
3. 打开 PDD，观察是否出现相关推荐

---

## 工具链

| 工具 | 版本 | 用途 |
|------|------|------|
| JADX | 1.5.6 | APK 反编译为 Java 源码 |
| Frida | 17.15.5 | 动态 Hook 与运行时分析 |
| Android SDK | 35 | ADB、模拟器、构建工具 |
| Python | 3.14 | 自动化分析脚本 |

---

## 风险等级

| 维度 | 评分 (1-10) |
|------|------------|
| 隐私侵犯程度 | **9/10** |
| 技术隐蔽性 | **8/10** |
| 数据收集广度 | **9/10** |
| 用户可控性 | **2/10** |
| **总体风险** | **🔴 CRITICAL (9.0/10)** |

---

## 免责声明

本项目仅用于安全研究和教育目的。所有分析基于公开可获取的 APK 文件，未对 PDD 服务器发起任何攻击性测试。报告中引用的代码均来自 JADX 反编译结果。

**腾讯不售卖聊天记录，QQ 不泄露聊天内容。**

---

*项目创建时间: 2026-07-16*
*最后更新: 2026-07-17*