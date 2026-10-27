# CC Switch Usage Display

把 Windows 或 macOS 上 [CC Switch](https://github.com/farion1231/cc-switch) 的 AI 用量常驻显示在微雪
**ESP32-C6-Touch-AMOLED-2.16**（480 × 480 AMOLED）上。固件同时是一个**带主页的启动器**：
开机进主页，从图标网格里选用量面板、时钟、水平仪等小应用，也可以一键切进
[xiaozhi](https://github.com/78/xiaozhi-esp32) 语音助手，长按按键再回到主页。

![界面总览](docs/preview/00-pages-preview.png)

```text
CC Switch SQLite  -->  Windows/macOS Companion  --Wi-Fi / HTTP-->  ESP32-C6
```

设备**不读取 API Key**，只保存一个随机 Bearer Token；Companion 以**只读**方式打开
CC Switch 的数据库，不修改网关配置。

本项目移植自 [peterroe/magpie-usage-display](https://github.com/peterroe/magpie-usage-display)，
保留了它的 macOS Companion 思路，改成「Windows/macOS Companion + CC Switch + Wi-Fi/HTTP」，
并换成 ESP32-C6 板子、加了主页启动器与多固件分区切换。

## 目录

- [功能](#功能)
- [工作原理](#工作原理)
- [硬件与按键](#硬件与按键)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [多固件分区布局](#多固件分区布局)
- [串口调试命令](#串口调试命令)
- [数据口径](#数据口径)
- [排障](#排障)
- [目录结构](#目录结构)
- [开发与验证状态](#开发与验证状态)
- [许可与归属](#许可与归属)

## 功能

主页是 3 × 4 的图标网格，顶部显示 CC Switch 连接状态、时间和日期，底部显示 Wi-Fi 与电池状态。

- `AI Chat`：切换到 `ota_1` 分区的 xiaozhi 语音助手（见「多固件分区布局」）
- `CC Usage`：用量面板，四页可左右滑动
  - `OVERVIEW`：今日成功率、调用数、错误数、今日费用
  - `REQUESTS`：最近模型、状态码、延迟、平均 TTFT、今日 Token
  - `TOTALS`：30 天请求总数、总 Token、估算费用、最常用模型
  - `CONTEXT`：缓存命中率以及 Input / Output / Cache Read / Cache Write
- `Clock`：PCF85063A RTC 时间（没有网络也能走）
- `Calendar`：月历
- `Level`：QMI8658 水平仪
- `Motion`：加速度 / 角速度实时读数
- `Gallery`：8 种程序化生成的图案，触摸或右键切换
- `Timer`：秒表 / 计次
- `System Test`：PMU、I2C、IMU、RTC、Wi-Fi、内存自检，并可切换 AI 分区
- `Power`：电池电压、电流、温度与供电状态
- `Network`：Wi-Fi、IP、RSSI 与 Companion 连接详情
- `Settings`：亮度、熄屏时间等设置（写入 NVS）

行为细节：用量面板每 15 秒拉取一次数据；60 秒无操作自动熄屏；Companion 可随 Windows
登录或 macOS 登录项自启，并写轮转日志。

用量面板的四页（按 `src/ui.cpp` 的布局与配色渲染，AMOLED 实物对比度更高）：

| OVERVIEW | REQUESTS |
|---|---|
| ![overview](docs/preview/01-overview.png) | ![requests](docs/preview/02-requests.png) |

| TOTALS | CONTEXT |
|---|---|
| ![totals](docs/preview/03-totals.png) | ![context](docs/preview/04-context.png) |

![BOOT 快捷菜单](docs/preview/05-quick-actions.png)

## 工作原理

```text
~/.cc-switch/cc-switch.db                  <- CC Switch 写入
        |
        |  只读 SELECT
        v
Windows/macOS Companion (Python 标准库)
        |  HTTP + Bearer Token
        v
ESP32-C6 启动器  --otadata-->  ota_0 启动器 / ota_1 xiaozhi
```

- Companion 只读打开数据库，通过 `http://<电脑局域网IP>:8787/api/usage` 提供给设备；
  控制类操作走 `/api/action/refresh`、`/api/action/focus`。
- 设备侧只认 Token，不接触任何密钥或会话内容。
- 局域网内是明文 HTTP，Token 只防误访问，**不能替代 TLS**，不要把这个端口暴露到公网。

## 硬件与按键

- [微雪 ESP32-C6-Touch-AMOLED-2.16](https://www.waveshare.com/esp32-c6-touch-amoled-2.16.htm)
  （16 MB flash，带不带电池版本均可），CO5300 AMOLED + CST9220 触摸 + AXP2101 PMU +
  QMI8658 IMU + PCF85063A RTC。
- 带数据传输能力的 USB-C 线，USB 直连即可烧录和看日志（无需外置串口芯片）。

引脚定义在 `src/board_config.h`：

| 功能 | 引脚 |
|---|---|
| I2C SDA / SCL | GPIO8 / GPIO7 |
| CO5300 QSPI CS / CLK | GPIO15 / GPIO0 |
| CO5300 QSPI D0-D3 | GPIO1-GPIO4 |
| CST9220 RST / INT | GPIO11 / GPIO5，I2C 地址 `0x5A` |
| AXP2101（PMU） | I2C 地址 `0x34`，ALDO3 给屏幕供电 |
| PCF85063A（RTC） | I2C 地址 `0x51` |
| QMI8658（IMU） | I2C 地址 `0x6B` |
| BOOT 键 | GPIO9 |
| PWR 键（AXP2101 PWRON 经 BSS138） | GPIO18，高电平有效 |
| KEY 键 | GPIO10 |

三个按键在不同页面作用不同：

| 按键 | 主页 / 应用内 | xiaozhi（AI 分区） |
|---|---|---|
| 左（BOOT，GPIO9） | 短按：熄屏 / 唤醒；长按：回主页 | 长按：回到启动器（`ota_0`） |
| 中（PWR，GPIO18） | 短按：熄屏 / 唤醒 | 按 xiaozhi 自身逻辑 |
| 右（KEY，GPIO10） | 主页：切换选中图标；应用内：应用自定义操作 | 按 xiaozhi 自身逻辑 |

- 主页点击图标直接打开；点 `AI Chat` 会弹出确认对话框。
- 主页右键循环选中，长按（≥ 0.9 秒）打开选中应用；应用内长按右键返回主页。
- 应用内左上角 `← HOME` 按钮也可返回主页。
- 没有硬件复位键；长按中键（PWR）约 6 秒由 AXP2101 硬关机，再按一次开机。

触摸读取按微雪官方 Arduino 示例使用寄存器 `0xD0 0x00`，并修正了官方示例中 `x`
坐标表达式的 C++ 运算符优先级问题。若面板批次方向不同，调整 `readTouchPoint()`
里的 X / Y 映射即可。

## 环境要求

- Windows 10 / 11，或 macOS 12+
- 已安装并运行 [CC Switch](https://github.com/farion1231/cc-switch)，且其中已有用量记录
- Python 3.10+（Companion 只用标准库）
- PlatformIO Core
- 开发板和电脑在同一个局域网

## 快速开始

### 1. 启动 Companion

#### Windows

```powershell
cd .\companion
.\run.ps1
```

首次启动会在 `%USERPROFILE%\.cc-usage-display\config.json` 生成监听地址、端口、
数据库路径和**随机 Token**，控制台会打印本机局域网地址和 Token。
默认监听 `0.0.0.0:8787`。

验证接口：

```powershell
Invoke-RestMethod http://localhost:8787/health

$cfg = Get-Content "$env:USERPROFILE\.cc-usage-display\config.json" | ConvertFrom-Json
$headers = @{ Authorization = "Bearer $($cfg.token)" }
Invoke-RestMethod -Headers $headers http://localhost:8787/api/usage
```

只看一次数据、不常驻：

```powershell
.\run.ps1 --once
```

随 Windows 登录自启 / 取消：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_startup.ps1
powershell -ExecutionPolicy Bypass -File .\uninstall_startup.ps1
```

日志在 `%USERPROFILE%\.cc-usage-display\companion.log`。
首次运行如弹出防火墙提示，请允许 Python 访问**专用网络**。

#### macOS

```bash
cd ./companion
./run.sh
```

首次启动会在 `~/.cc-usage-display/config.json` 生成配置和**随机 Token**。
验证接口：

```bash
curl http://localhost:8787/health
./run.sh --once
```

如需随 macOS 登录自启：

```bash
./install_launch_agent.sh
./uninstall_launch_agent.sh
```

macOS 上 `/api/action/focus` 使用 `open -a "CC Switch"` 启动或激活 CC Switch。

### 2. 配置固件

Windows PowerShell：

```powershell
Set-Location <仓库根目录>
Copy-Item .\include\secrets.example.h .\include\secrets.h
```

macOS / Linux shell：

```bash
cd <仓库根目录>
cp include/secrets.example.h include/secrets.h
```

编辑 `include/secrets.h`：

```cpp
#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASSWORD "your-wifi-password"

// 填写电脑的局域网 IP，不能写 127.0.0.1。
#define DASHBOARD_URL "http://192.168.1.10:8787/api/usage"
#define DASHBOARD_ACTION_URL "http://192.168.1.10:8787/api/action"
#define DASHBOARD_TOKEN "config.json 中的 token"
```

`DASHBOARD_TOKEN` 必须与 `config.json` 里的 `token` 完全一致。
`secrets.h` 已被 `.gitignore` 忽略，不会进版本库。

### 3. 编译与烧录

```text
pio run                                             # 编译（Windows/macOS 都相同）
pio device list                                     # 查串口
```

Windows 示例：

```powershell
pio run -t upload --upload-port COM5                # 烧录启动器
pio device monitor --port COM5 --baud 115200        # 看日志
```

macOS 示例（把串口名替换成 `pio device list` 的实际结果）：

```bash
pio run -t upload --upload-port /dev/cu.usbmodemXXXX
pio device monitor --port /dev/cu.usbmodemXXXX --baud 115200
```

`bootloader.bin` 和 `partitions.bin` 由 PlatformIO 生成在
`.pio/build/esp32-c6-touch-amoled-216/`；xiaozhi 与 assets 镜像需自备，见下一节。
如果电脑识别不到串口，按住板上 **BOOT** 再插 USB 进入下载模式后重试。

## 多固件分区布局

16 MB flash 被划成两个可启动固件槽，定义见 `partitions_16mb_launcher.csv`：

| 分区 | 类型 / 子类型 | 偏移 | 大小 | 用途 |
|---|---|---|---|---|
| `nvs` | data / nvs | `0x009000` | `0x006000` | 设置持久化 |
| `otadata` | data / ota | `0x00F000` | `0x002000` | 引导选择（空 = 启动主页） |
| `phy_init` | data / phy | `0x011000` | `0x001000` | 射频校准 |
| `ota_0` | app / ota_0 | `0x020000` | `0x400000` | 本项目的 Home 启动器 |
| `ota_1` | app / ota_1 | `0x420000` | `0x300000` | xiaozhi 语音助手 |
| `assets` | data / spiffs | `0x720000` | `0x400000` | xiaozhi 语音模型 / 字体资源 |
| `storage` | data / spiffs | `0xB20000` | `0x4D0000` | xiaozhi 运行数据 |
| `coredump` | data / coredump | `0xFF0000` | `0x010000` | 崩溃转储 |

分区命名沿用微雪出厂固件的约定：**出厂固件本身就在 `ota_0`**。xiaozhi 自带的
「长按 BOOT 回到 factory 分区」逻辑找的就是出厂槽，所以启动器必须占用 `ota_0`、
xiaozhi 占用 `ota_1`，长按左键才能正确回到主页。切换分区时不复制任何数据，
只改 `otadata` 里的指针。

```text
otadata 为空              -> 启动 ota_0（Home 启动器）
主页选 AI Chat / 串口 ai  -> 引导分区指向 ota_1，重启进 xiaozhi
xiaozhi 里长按左键        -> 引导分区设回 ota_0，重启回主页
```

首次烧录的完整内容：

```text
0x000000  bootloader.bin
0x008000  partitions.bin
0x020000  firmware.bin        (Home 启动器)
0x420000  xiaozhi-app.bin
0x720000  assets.bin
0x00F000  0x2000 字节 0xFF     (清空 otadata，使设备启动到主页)
```

只改启动器时，重写 `0x020000` 一处即可，不会动到 xiaozhi 和 assets。

### xiaozhi 与 assets 镜像从哪来

本仓库不附带 xiaozhi 固件和语音资源，它们是独立项目、各自有授权：

- 上游工程：<https://github.com/78/xiaozhi-esp32>
- 微雪为本板提供的板级适配在官方仓库 `ESP32-C6-Touch-AMOLED-2.16` 的
  `02_Example/XiaoZhi-vX.Y.Z/` 里，含板级 `config.h` 与
  `boards/waveshare/esp32-c6-touch-amoled-2.16/` 下的 `.cc`。
- 用 ESP-IDF 打开该工程，`idf.py set-target esp32c6`，在 `menuconfig` 里选
  `Xiaozhi Assistant -> Board Type -> Waveshare ESP32-C6-Touch-AMOLED-2.16`，
  然后 `idf.py build`。
- 把 `build/xiaozhi.bin` 写入 `0x420000`；由 `scripts/build_default_assets.py`
  生成的 assets 镜像写入 `0x720000`。
- 也可以直接用微雪固件包 `03_Firmware/02_xiaozhi-*.bin`（整包镜像，需自行取出
  app 段与 assets 段）。

> **不要**用 xiaozhi 自带的 partition table 烧录本板：它的 `ota_0` 也在 `0x020000`，
> 会和启动器互相覆盖。只取它的 app 镜像与 assets 镜像，按上表偏移写入。

## 串口调试命令

115200 波特打开串口（`pio device monitor`），输入命令回车：

| 命令 | 作用 |
|---|---|
| `ai` | 把引导分区设为 `ota_1` 并重启（进入 xiaozhi） |
| `home` | 回到主页界面（不重启） |
| `slot` | 打印当前运行槽，以及两个槽的名称 |
| `reboot` | 重启 |
| `mem` | 打印堆与 LVGL 内存使用情况 |
| `cfg` | 打印屏幕开关、亮度、熄屏时间、空闲时长和三个按键电平 |
| `off` / `on` | 手动熄屏 / 唤醒（用于验证唤醒逻辑） |

屏幕每次开 / 关都会打印 `[screen] ON|OFF via <触发者>`，按键边沿会打印
`[btn] pin=<n> DOWN|UP`，方便定位是谁把屏幕关掉的。

若误入 xiaozhi 而无法返回，擦除 `otadata` 即可回到主页：

```powershell
esptool --chip esp32c6 --port COM5 erase-region 0xF000 0x2000
```

macOS 上把 `COM5` 替换为 `pio device list` 显示的 `/dev/cu.*` 串口名。

Windows 上也可以直接用仓库里的 `回到主页.cmd`（可选带串口号，默认 `COM5`）：

```powershell
.\回到主页.cmd COM5
```

## 数据口径

Companion 直接读取（Windows 和 macOS 默认相同）：

```text
~/.cc-switch/cc-switch.db
```

Windows 上通常是 `C:\Users\<用户名>\.cc-switch\cc-switch.db`，macOS 上通常是
`/Users/<用户名>/.cc-switch/cc-switch.db`。不要使用旧版或其他位置的数据库。

统计会复用 CC Switch 的有效日志规则：当导入的 `codex_session` / `session_log` 与
±10 分钟内成功的代理请求在 token、模型和应用类型上一致时，只计代理请求，避免重复
统计。Token 按 CC Switch 的 `input_token_semantics` 归一化，「Input」表示新增输入，
不包括缓存读写。

今日、7 天和 30 天都从请求明细计算；CC Switch 的 `usage_daily_rollups` 只保存超过
约 30 天的归档，因此不影响本面板的 30 天窗口。费用来自 CC Switch 写入的
`total_cost_usd`，Companion 再按 `~/.cc-usage-display/config.json` 里的
`usd_to_cny` 汇率换算成人民币显示；如果供应商没有配置价格，费用可能显示为 `0.00`。

## 排障

**设备显示 OFFLINE**

- 确认电脑和开发板在同一局域网。
- 确认 `DASHBOARD_URL` 用的是电脑局域网 IP，不是 `127.0.0.1`。
- 在电脑浏览器打开 `http://<电脑IP>:8787/health`。
- Windows 上检查防火墙和网络配置文件是否为「专用」；macOS 上检查防火墙是否允许
  Python 接受局域网连接。

**接口返回 401**
`secrets.h` 里的 Token 与 `config.json` 不一致。改完重新编译烧录。

**显示 STALE**
设备连上了 Wi-Fi，但超过 60 秒没有新数据。检查 Companion 日志、CC Switch 数据库
路径，以及 CC Switch 是否仍在写用量。

**Token 或费用为 0**
打开 `~/.cc-switch/cc-switch.db` 确认 `proxy_request_logs` 有数据。
费用为 0 通常是对应供应商没配模型价格，不是面板算错。

**屏幕黑屏**

- 确认 USB 供电正常。
- 确认 AXP2101 在 I2C 地址 `0x34` 应答。
- 看串口日志里的 `[pmu]`、`[display]`、`[touch]` 信息。
- 若完全没有串口输出，按住 BOOT 再插 USB 进入下载模式重新烧录。

**Companion 启动失败**
看 `~/.cc-usage-display/companion.log`，或前台运行 `companion/run.ps1`（Windows）或
`companion/run.sh`（macOS）直接看异常。端口 `8787` 被占用时可以改 `config.json` 的
`port`，同时同步修改 `secrets.h` 里的两个 URL。

## 目录结构

```text
.
├── src/                          固件（Arduino / PlatformIO）
│   ├── main.cpp                  启动、外设自检、按键、串口命令、分区切换
│   ├── launcher.cpp / .h         主页启动器（图标网格 + 应用调度）
│   ├── apps.cpp / .h             12 个应用页
│   ├── ui.cpp / .h               CC Usage 四页面板
│   ├── ui_kit.cpp / .h           公共 UI 组件
│   ├── net_client.cpp / .h       Wi-Fi + HTTP 拉取用量
│   ├── hw_imu.cpp / .h           QMI8658 驱动
│   ├── hw_rtc.cpp / .h           PCF85063A 驱动
│   ├── app_state.cpp / .h        用量数据结构
│   ├── board_config.h            引脚定义
│   └── sys.h / timeutil.h        平台封装与时间换算
├── companion/                    Windows/macOS Companion（纯标准库 Python）
│   ├── cc_usage_display/         读取 CC Switch 数据库 + HTTP 服务
│   ├── run.sh                     macOS 启动脚本
│   ├── install_launch_agent.sh   macOS 登录自启
│   ├── uninstall_launch_agent.sh 取消 macOS 登录自启
│   └── tests/                    单元测试
├── include/
│   └── secrets.example.h         配置模板（secrets.h 不入库）
├── docs/preview/                 README 用的界面渲染图
├── partitions_16mb_launcher.csv  16 MB 分区表
├── platformio.ini                PlatformIO 工程配置
└── 回到主页.cmd                   一键把设备切回主页（擦除 otadata）
```

## 开发与验证状态

Windows PowerShell：

```powershell
$env:PYTHONPATH = "companion"
python -m unittest discover -s companion/tests -v
pio run
```

macOS / Linux shell：

```bash
PYTHONPATH=companion python3 -m unittest discover -s companion/tests -v
pio run
```

- Companion 单元测试与真实 CC Switch 数据库快照已验证。
- 固件通过 PlatformIO 完整编译（Flash 约 1.52 MB / 4 MB，RAM 约 44%）。
- 启动器已在实机验证：上电自检（PMU / 屏幕 / 触摸 / IMU / RTC）、连 Wi-Fi、拉取
  CC Switch 数据、串口 `ai` / `home` / `reboot` / `mem` / `slot` / `cfg` 命令、
  三个按键的边沿、以及 `AI Chat` → xiaozhi → 长按左键回家 的完整往返。
- xiaozhi 2.2.4 已在实机验证能从 `ota_1` 启动并完成激活。
- 各应用页的实机交互（触摸、三个按键、IMU / RTC 读数）仍需在实物板上逐个确认。

## 许可与归属

本项目基于 [peterroe/magpie-usage-display](https://github.com/peterroe/magpie-usage-display)
的界面与固件结构改造，保留其 MIT 许可与版权声明。第三方依赖说明见
`THIRD_PARTY_NOTICES.md`，字体许可见 `LICENSES/OFL-1.1.txt`。
