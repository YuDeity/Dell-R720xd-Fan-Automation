# Dell R720xd iDRAC 风扇自动控制 Web 面板

##注意！ index.html演示模板请放在templates/##
## 根目录/
# ├── app.py
# ├── templates/
# │   └── index.html
基于 Flask + ipmitool 的简单 Web 界面，用于远程/本地控制 Dell PowerEdge R720xd 的风扇转速，支持自动根据 CPU 温度调节。

## 特性

- Web 界面实时显示最高 CPU 温度、风扇速度（百分比 + hex）、自动模式状态
- 一键手动设置 Low / Med / High 风扇速度
- 自动模式：根据温度阈值自动调节（默认 ≤65°C → 10%、65-80°C → 20%、>80°C → 20%）
- 显示最近 20 条运行日志
- 页面每 30 秒自动刷新（可关闭）
- 配置全部通过环境变量完成，代码中不硬编码敏感信息

## 前置要求

- Dell PowerEdge R720xd（其他 iDRAC7 机型如 R710/R720/R730 可能兼容，但 hex 值需自行验证）
- iDRAC 已启用 IPMI over LAN（iDRAC 设置 → 网络 → 服务 → IPMI → 启用）
- 运行环境（推荐 Debian/Ubuntu 等 Linux）已安装：
  - `ipmitool`
  - Python 3
  - Flask (`pip install flask`)

## 快速安装与启动

```bash
# 1. 安装依赖（Debian/Ubuntu 示例）
sudo apt update
sudo apt install python3 python3-pip ipmitool -y
pip3 install flask


# 2. 设置环境变量（必须！）
export IDRAC_IP="192.168.1.88"          # 替换成你的 iDRAC IP
export IDRAC_USER="root"                # 默认 root，也可修改
export IDRAC_PASS="你的iDRAC密码"       # 强烈建议用强密码

# 5. 启动（前台测试）
python3 app.py

## 温度阈值（℃）
TEMP_LOW  = 65
TEMP_HIGH = 80

## 风扇速度（hex 值，对应大致百分比，R720xd 常见值）
FAN_SPEEDS = {
    "low":  "0x0a",   # ≈10%   安全最低值，别设太低（如 0x00~0x05 风险高）
    "med":  "0x14",   # ≈20%
    "high": "0x14"    # ≈20%   建议根据需要改为 "0x1e" ≈30% 或更高
}

CHECK_INTERVAL = 30   # 检查间隔（秒）
