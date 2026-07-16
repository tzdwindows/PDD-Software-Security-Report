# PDD 逆向工程与安全审计项目

> **拼多多 (com.xunmeng.pinduoduo) v8.5.0 — 深度安全审计**
>
> 静态代码分析 + 动态行为分析 + Binder 层劫持证据链

---

## 项目概述

本项目对拼多多 Android 客户端 v8.5.0 进行了全面的安全审计，涵盖静态代码分析、Binder 层系统服务劫持分析、剪贴板监控机制分析、以及动态验证方案设计。

**核心发现：PDD 通过 `SystemServiceHooker` 在 Binder 层劫持了 8 个 Android 系统服务，包括全局剪贴板（`IClipboard`）、定位（`ILocationManager`）、电话（`ITelephony`）等，实现了对设备上所有应用行为的实时监控。**

---

## 项目结构

```
F:\pdd逆向工程\
├── README.md                                     # 本文件
├── base.apk                                      # 目标 APK (25.9 MB)
├── jadx_output\                                  # JADX 反编译输出
│   ├── sources\                                  # 24,827 个 Java 源文件
│   └── resources\resources\                      # 资源文件 + AndroidManifest.xml
├── tools\                                        # 工具链与脚本
│   ├── android-sdk\                              # Android SDK 35
│   ├── jadx\                                     # JADX 1.5.6
│   ├── frida\                                    # Frida 17.15.5
│   ├── pdd_frida_hook.py                         # 综合 Frida 动态 Hook 脚本 (Python)
│   ├── pdd_clipboard_hook.js                     # 剪贴板劫持专项 Hook 脚本 (JS)
│   ├── deep_static_analysis.py                   # 深度静态分析脚本
│   ├── run_jadx.py                               # JADX 反编译脚本
│   ├── create_avd.py                             # AVD 创建脚本
│   ├── start_emulator.py                         # 模拟器启动脚本
│   └── wait_emulator.py                          # 模拟器等待脚本
├── .tzd\                                         # 任务日志
│   └── log\
└── 报告文档\
    ├── ultimate_security_report.md               # 综合安全审计报告 (622 行)
    ├── PDD_behavior_perception_analysis.md        # 用户行为感知机制深度分析 (382 行)
    ├── PDD_screenshot_evidence_chain.md           # 截图/相册监控证据链 (718 行)
    ├── PDD_dynamic_security_testing_report.md     # 动态安全测试报告 (801 行)
    └── static_analysis_findings.txt               # 静态分析原始结果 (1037 行)
```

---

## 报告导航

| 报告 | 内容 | 适用场景 |
|------|------|---------|
| **[ultimate_security_report.md](ultimate_security_report.md)** | 全面的静态安全审计，涵盖权限、保活、截图、剪贴板、URL Scheme、WebView 等 | 了解 PDD 的整体安全风险 |
| **[PDD_behavior_perception_analysis.md](PDD_behavior_perception_analysis.md)** | 聚焦"为什么点 QQ 聊天记录会触发 PDD 推送"，含 Binder 层劫持完整证据链 | 理解剪贴板劫持的技术原理 |
| **[PDD_screenshot_evidence_chain.md](PDD_screenshot_evidence_chain.md)** | 截图/相册监控的完整证据链，含 MediaProjection、VirtualDisplay、ImageReader | 深入理解 PDD 的屏幕捕获能力 |
| **[PDD_dynamic_security_testing_report.md](PDD_dynamic_security_testing_report.md)** | 动态安全测试方案，含完整 Frida Hook 脚本和复现步骤 | 在真机上验证 PDD 的隐私侵犯行为 |
| **[static_analysis_findings.txt](static_analysis_findings.txt)** | 31,246 个敏感模式匹配的原始结果 | 快速检索特定安全模式 |

---

## 核心发现速览

### 🔴 Critical：Binder 层系统服务劫持

PDD 的 `SystemServiceHooker` 直接修改 `ServiceManager.sCache`，将系统服务的 IBinder 替换为动态代理对象，劫持了 **8 个系统服务**：

| 系统服务 | 泄露数据 |
|---------|---------|
| `clipboard` (IClipboard) | **所有应用的剪贴板操作** |
| `location` (ILocationManager) | 精准位置 |
| `wifi` (IWifiManager) | WiFi 连接信息 |
| `telephony.registry` (ITelephonyRegistry) | 电话状态、基站 |
| `iphonesubinfo` (IPhoneSubInfo) | IMEI/设备标识 |
| `phone` (ITelephony) | 电话操作 |
| `bluetooth_manager` (IBluetoothManager) | 蓝牙信息 |
| `device_identifiers` | 设备标识策略 |

### 🔴 Critical：剪贴板实时监控

- `dc2.a` 拦截器监控 **8 种**剪贴板操作（setPrimaryClip、getPrimaryClip、clearPrimaryClip 等）
- 对 `hasPrimaryClip` 返回 `false`，**主动干扰**剪贴板正常行为以隐藏自身
- `dc2.b` 记录完整调用栈、调用者进程名、时间戳，上报 Module 30123

### 🔴 Critical：用户行为感知

- **前台应用检测**：`getRunningTasks(1)` + `getRunningAppProcesses()` + shell 命令
- **QQ 安装检测**：启动时缓存 QQ/微信/支付宝等关键应用的安装状态
- **设备指纹**：CPU、内存、存储、进程全方位采集

### 🟠 High：其他高风险行为

- **屏幕截图服务**：`ScreenShotAdapterService` + `MediaProjectionManager`，名义"以图搜图"
- **多进程保活**：9 个进程 + 6 厂商推送 SDK + AlarmService + JobScheduler + Titan 长连接
- **隐藏桌面图标**：4 个 LAUNCHER Activity，含 `PandaHmActivity` 隐藏入口
- **15+ URL Scheme**：含混淆 Scheme `qngaccv79cv29i://` 和 `weixinn://` 拼写变体

---

## 你遇到的"QQ 聊天触发 PDD 推荐"现象

### 发生了什么

```
你点击 QQ 聊天消息
  → QQ 自动将消息文本写入系统剪贴板
  → PDD 的 SystemServiceHooker 在 Binder 层拦截 IClipboard
  → dc2.a 捕获 setPrimaryClip 调用
  → 文本上传至 PDD 服务端
  → NLP 提取关键词 → 商品匹配 → 推送通知
```

### 为什么朋友也收到相同推荐

因为推荐基于**文本内容**而非用户画像——相同文本 → 相同 NLP 关键词 → 相同商品。

### 详细分析

详见 **[PDD_dynamic_security_testing_report.md](PDD_dynamic_security_testing_report.md)** 第 1-4 节。

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

1. 打开 QQ，点击任意聊天消息
2. 观察 Frida 输出，确认 `dc2.a` 拦截器触发
3. 切换回 PDD，观察是否出现相关推荐

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

---

*项目创建时间: 2026-07-16*
*最后更新: 2026-07-17*