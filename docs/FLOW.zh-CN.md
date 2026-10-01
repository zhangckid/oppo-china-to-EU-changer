# 刷机流程图与检查点

[English](FLOW.md) | 简体中文 | [项目主页](../README.zh-CN.md)

离线阅读或页面未渲染 Mermaid 时，可打开已渲染的 SVG：[1. 准备 Recovery](images/flow-1-zh-CN.svg) · [2. 转版与首次开机](images/flow-2-zh-CN.svg) · [3. 分区变化](images/flow-3-zh-CN.svg) · [4. 等待与停止](images/flow-4-zh-CN.svg)。这些是流程示意图，不是手机截图。

这些图描述工具为 **Find X9 Ultra（X9U）、PMA110、512 GB、CN403 → CPH2841 EU403** 实现的流程。历史手工转版仅在一台 X9U 上有实机证据；新 CLI 的完整流程尚未在手机上执行。请配合[逐步命令教程](CLI.zh-CN.md)阅读，不能依据流程图跳过检查点。

图中“电脑”表示 CLI 在明确执行后完成或检查的动作；“手机”表示操作者必须亲自完成的动作。GPT 和固件写入由 CN2EU 包自带安装器负责，本项目负责调用和核验。

## 1. 从原厂国行 Android 到准备好的 Recovery

```mermaid
flowchart TD
    A["原厂 PMA110、512 GB、CN403<br/>先另行备份个人数据"] --> B["电脑：doctor 和 prepare<br/>校验四个固定文件，预览运行"]
    B --> C{"机型、内核、输入文件<br/>和磁盘几何均匹配？"}
    C -->|否| STOP["停止并保留证据<br/>进一步操作前核查当前记录"]
    C -->|是| D["电脑：安装 GBL APK"]
    D --> E["手机：临时 Root 并执行 FLASH<br/>确认 FLASH_VERIFY_OK"]
    E --> F["手机：原厂 Recovery 执行 Format Data<br/>个人数据将被清除"]
    F --> G["手机：进入 GBL<br/>重启振动后立即按住音量上"]
    G --> H["电脑：请求解锁 Bootloader<br/>手机：亲自确认解锁提示"]
    H --> I["电脑：核对解锁状态和 Recovery 容量<br/>刷入 recovery_a，重启 OrangeFox"]
    I --> J["电脑：核对国行布局和保留的 GBL<br/>备份 107 个分区与六份 GPT"]
    J --> K["手机：开启 ADB Sideload<br/>电脑：传输 OrangeFox ZIP"]
    K --> L["全新的 OrangeFox Recovery<br/>核对双槽 Recovery 和备份"]
    L --> M["准备安装 CN2EU 包<br/>关闭自动重启，保存安装前日志"]
```

图中的固件备份发生在**安装 GBL、原厂 Format Data 和首次刷入 Recovery 镜像之后**。它不包含 `userdata`，无法找回前面已经清除的个人数据。历史手工案例备份了 121 个所选分区；新 CLI 实现的是自己的 107 个分区备份范围。两者都不能称为原始出厂备份。

Android 与 Recovery 使用原来的 ADB 序列号；GBL 可能显示另一序列号，在 `waiting_gbl` 阶段明确绑定。刷 Recovery 前，CLI 会检查活动槽为 A，且 `recovery_a` 为 104,857,600 字节；安装 OrangeFox ZIP 前检查 `recovery_b` 容量。图中未单独画出的执行检查如果出现意外，也会停止。

## 2. 从 CN2EU Sideload 到欧版 Android

```mermaid
flowchart TD
    A["已准备好的 OrangeFox 会话<br/>保留 GBL，关闭自动重启"] --> B["手机：开启 ADB Sideload<br/>电脑：传输确切的 CN2EU ZIP"]
    B --> C["手机：音量上确认继续<br/>随后音量下选择 ABL = NO"]
    C --> D["原安装器：扩展 GPT<br/>写入 100 个固件目标和 sparse super"]
    D --> E{"日志中有本次 Installation complete<br/>已保留 ABL 且安装无错误？"}
    E -->|否或不确定| STOP["停止：保留 Recovery 状态及全部日志<br/>不要格式化、启动 System 或重试刷写"]
    E -->|是| F["电脑：核对磁盘上的 GPT 与受保护引导链<br/>直接重启到 Recovery"]
    F --> G{"新 Recovery 启动 ID、欧版尺寸<br/>固件和已定义 super 区域摘要均匹配？"}
    G -->|否| STOP
    G -->|是| H["手机：Data - Format Data - 输入 yes<br/>留在本次 Recovery 会话"]
    H --> I{"有本次 userdata 和 metadata<br/>格式化成功的日志证据？"}
    I -->|否| STOP
    I -->|是| J["电脑：再次重启 Recovery<br/>检查欧版布局和 data 的 F2FS 挂载"]
    J --> K["电脑：请求首次启动欧版 Android<br/>手机：完成初始化并重新授权 ADB"]
    K --> L{"欧版身份、系统启动<br/>和初始化状态均符合预期？"}
    L -->|否| STOP
    L -->|是| M["记录为 complete<br/>继续阅读 OTA 与 NFC 兼容性说明"]
```

电脑上的传输百分比不是安装结果，即使百分比看起来停在 100% 之前，也应看安装器日志。CLI 要求本次 Recovery 日志中的完成证据，再检查 100 个固件目标的镜像长度范围，以及 `super` 中 290 个已定义 RAW/FILL 区域。另有 19 个 DONT_CARE 区域没有确定的预期内容，不参与设备读回比较。

第一次重启 Recovery，是让内核重新读取变更后的分区表；Format Data 后再次重启 Recovery，是在新会话中检查 `/data` 文件系统。这是两个独立检查点。`complete` 表示程序设定的转版检查通过，不代表手机全部功能或 OTA/NFC 开卡能力都已通过测试。详见[实机体验](COMPATIBILITY.zh-CN.md)。

## 3. 存储布局发生什么变化

逻辑扇区为 4,096 字节。下列起止扇区均包含端点，且只适用于已审查的 512 GB 配置。

```mermaid
flowchart LR
    subgraph CN["sda 原国行布局"]
        A["第 1–13 分区<br/>固定边界"]
        B["super：sda14<br/>385772 - 5188331"]
        C["userdata<br/>sda15<br/>5188332 - 124070906"]
        A --> B --> C
    end
    subgraph EU["sda 目标欧版布局"]
        D["第 1–13 分区<br/>边界不变"]
        E["super：sda14<br/>385772 - 5378795"]
        F["userdata<br/>sda15<br/>5378796 - 124070906"]
        D --> E --> F
    end
    B -.->|安装器扩展| E
    C -.->|起点移动，必须格式化| F
```

| 组件 | 已审查的行为 | 原因与含义 |
| --- | --- | --- |
| `super` | 从 19,671,285,760 增至 20,451,426,304 字节 | 安装包按原始磁盘偏移流式写入 sparse 镜像；Recovery 重启前，内核可能仍使用旧分区尺寸。 |
| `userdata` | 起点后移，终点仍为 124,070,906 | 转换包不能放在手机内部存储。CLI 从电脑通过 sideload 传输；普通清除不能代替所需的 Format Data。 |
| `sda` 第 1 至 13 个 GPT 分区 | 分区边界保持不变 | 这只指布局不变；部分内容仍会变化，例如 Format Data 会格式化 metadata。 |
| 50 个选定固件镜像 | 向双槽写入，共 100 个目标 | 首次转版涉及两个槽位；后续 OTA updater 使用另一套分区策略。 |
| `abl_a`、`abl_b`、EFISP | 保留已有 GBL 组件 | 转换包提示时必须选 **ABL = NO**；CLI 会核对固定的 GBL 内容。 |
| `recovery_a`、`recovery_b` | 保留设备专用 OrangeFox | OrangeFox IMG/ZIP 阶段负责安装；CN2EU ROM 安装阶段跳过包内自带的 Recovery 镜像。 |
| `userdata` 和 `metadata` | 由最后的 OrangeFox Format Data 格式化 | 工具要求两者本次格式化成功的日志，再进入全新的 Recovery 会话。 |

## 4. 检查点续行不等于自动重试

```mermaid
flowchart TD
    A["读取已有运行记录和 status"] --> B{"处于预期人工等待阶段？"}
    B -->|否：未完成动作或 review_required| STOP["人工核查<br/>没有重置、强制继续、自动重试或回滚"]
    B -->|是| C["操作者完成要求的手机动作<br/>使用确切阶段和序列号 resume"]
    C --> D{"必需的现场检查均匹配？"}
    D -->|否| STOP
    D -->|是| E["变更前持久化保存执行意图"]
    E --> F["执行有时限的命令并检查结果"]
    F --> G{"结果已验证？"}
    G -->|否、中断或不确定| STOP
    G -->|是| H["保存下一个等待阶段或 complete"]
    H --> A
```

退出码 `3` 表示正常等待人工操作；`2` 表示检查或命令失败，需要查看 `status`：用法或主机准备错误可能不改变运行记录，执行阶段失败则可能使其进入 `review_required`。`130` 表示中断。工具不会把超时或断线解释为“没有写入任何字节”。具体响应见[异常处理表](TROUBLESHOOTING.zh-CN.md)。

## 5. 转版之后

当这个转版配置无法通过系统内置更新器升级时，可阅读已发布的 [OTA updater GitHub 仓库](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater)，了解独立审查的后续升级流程。该项目当前文档基线是欧版 `16.0.10.500`，并要求经验证的本地设备配置；刚转到 EU403 的手机不等于已经具备直接执行 updater 的条件。具体见该项目的[中文文档](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater/blob/main/README.zh-CN.md)或英文 README。

已反馈的 NFC 问题是**添加卡片时被 OPPO 拒绝**。国内 NFC App 本身在这台手机上正常运行。本转换工具和 OTA updater 都没有实现 NFC 加卡修复。范围与反馈方式见[兼容性说明](COMPATIBILITY.zh-CN.md)。
