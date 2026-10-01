"""Human-readable journal guidance; never opens a device or executes a stage."""
import shlex

from .runner import INSTRUCTIONS, status


ZH_ACTIONS = {
    "prepared": "先备份个人数据，核对全新国行 CN403、机型、容量、项目号和内核。准备完成不代表已检查手机；开始命令见 CLI 第 3 节。",
    "waiting_gbl": "手机打开 GBL 应用，取得临时 Root，输入 FLASH 并确认 FLASH_VERIFY_OK。按上游要求在原厂 Recovery Format Data。重启振动后立即按住音量上进入 GBL；全部个人数据会被清除。",
    "waiting_unlock": "在手机屏幕确认 Bootloader 解锁，并保持在 GBL；不要启动 Android。下一执行阶段会检查解锁状态并写入 Recovery。",
    "waiting_recovery": "等待 OrangeFox Recovery ADB 就绪。下一执行阶段检查设备并备份指定固件分区与 GPT；备份不包含个人数据。",
    "waiting_ofox_sideload": "在 OrangeFox 开启 ADB Sideload。下一执行阶段传送匹配的 OrangeFox ZIP。",
    "waiting_ofox_recovery": "等待 OrangeFox ZIP 安装器重启 Recovery 并返回。下一执行阶段核对新启动、双槽 Recovery、受保护分区和备份。",
    "waiting_rom_sideload": "关闭自动重启，在 OrangeFox 开启 ADB Sideload。执行传包后，安装器第一次提示按音量上继续，ABL 提示按音量下选 NO。保持 USB 连接。",
    "waiting_install_result": "保持当前 Recovery，必要时退出 sideload，不要重启。下一执行阶段读取本次安装日志；电脑传输完成不代表手机安装成功。",
    "waiting_fresh_recovery": "等待程序请求的 Recovery 重启完成。下一执行阶段检查新的分区表、100 个固件目标和 super 已定义区域的回读摘要。",
    "waiting_format": "在当前 OrangeFox 中选择 Menu → Partitions management → Static partitions → Data → Format Data，输入 yes 并等待成功；不要启动 System。",
    "waiting_formatted_recovery": "等待格式化后程序请求的 Recovery 重启完成。下一执行阶段核对 /data 后才请求启动 Android。",
    "waiting_android": "完成 Android 初始化，开启 USB 调试并授权这台电脑。下一执行阶段核对 EU403 身份、启动和初始化状态。",
}

SECTIONS = {
    "prepared": 3, "waiting_gbl": 4, "waiting_unlock": 4,
    "waiting_recovery": 5, "waiting_ofox_sideload": 5, "waiting_ofox_recovery": 5,
    "waiting_rom_sideload": 6, "waiting_install_result": 6, "waiting_fresh_recovery": 6,
    "waiting_format": 7, "waiting_formatted_recovery": 7, "waiting_android": 7,
}


def render(directory, language="en"):
    result = status(directory)
    stage, run_status = result["stage"], result["status"]
    zh = language == "zh-CN"
    suffix = ".zh-CN.md" if zh else ".md"
    lines = ["转版操作指引（只读）" if zh else "Conversion guide (read only)",
             f"{'阶段' if zh else 'Stage'}: {stage}",
             f"{'状态' if zh else 'Status'}: {run_status}",
             "仅读取本地记录；未连接或核验手机，未执行操作。" if zh else
             "Local journal only; no phone connection, verification, or action."]
    # Never offer a next-stage instruction for unfinished or inconsistent states.
    if run_status in {"running", "executing"}:
        lines.append("记录中有未完成操作。如原进程仍在运行，让其继续；如已退出，保留现场等待人工核查。不要重复运行。" if zh else
                     "An action is unfinished. Leave the original process running if active; if it ended, preserve the state for manual review. Do not replay it.")
    elif stage == "complete" and run_status == "complete":
        lines.append("转版检查已完成。保持 Bootloader 解锁；OTA 与 NFC 限制见兼容性文档。" if zh else
                     "Conversion checks completed. Keep the bootloader unlocked; see compatibility notes for OTA and NFC limits.")
        lines.append(f"docs/COMPATIBILITY{suffix}")
    elif run_status != "waiting" or stage not in SECTIONS:
        lines.append("停止：保留当前手机状态和运行目录，等待人工核查；无强制继续或重置选项。" if zh else
                     "STOP: preserve the phone state and run directory for manual review; no force or reset option.")
    else:
        lines.append("手机操作 / 下一阶段说明：" if zh else "Phone action / next-stage notes:")
        lines.append(ZH_ACTIONS[stage] if zh else INSTRUCTIONS[stage])
        serial = ("当前 GBL fastboot 序列号（可能与 ADB 不同）" if zh else
                  "current GBL fastboot serial (may differ from ADB)") if stage in {
                      "waiting_gbl", "waiting_unlock"} else (
                  "最初 Android 的 ADB 序列号（Recovery 也使用它）" if zh else
                  "original Android ADB serial (also used in Recovery)")
        lines.append(f"{'执行时使用' if zh else 'For execution use'}: {serial}")
        lines.append(f"{'完整命令' if zh else 'Full commands'}: docs/CLI{suffix} — {'第' if zh else 'section'} {SECTIONS[stage]} {'节' if zh else ''}".rstrip())
        lines.append("完成手机操作并核对状态后，按该节命令继续；本指引不会自动确认。" if zh else
                     "After the phone action and checks, follow that section's command; this guide does not acknowledge it for you.")
    if result.get("error"):
        lines.append(f"{'已保存的错误' if zh else 'Recorded error'}: {result['error']}")
    lines.append(f"{'查看原始记录' if zh else 'Inspect recorded status'}: python3 change.py status {shlex.quote(str(directory))}")
    lines.append(f"{'遇到异常' if zh else 'If something differs'}: docs/TROUBLESHOOTING{suffix}")
    return "\n".join(lines)
