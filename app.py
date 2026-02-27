from flask import Flask, render_template, request, jsonify
import subprocess
import threading
import time
import os
import sys

app = Flask(__name__)

# 从环境变量读取配置（更安全，推荐方式）
IDRAC_IP   = os.getenv("IDRAC_IP",   "192.168.0.100")   # 请自行修改默认值或保持为空
IDRAC_USER = os.getenv("IDRAC_USER", "root")
IDRAC_PASS = os.getenv("IDRAC_PASS")

# 如果密码没设置，直接退出程序
if not IDRAC_PASS:
    print("错误：请设置环境变量 IDRAC_PASS")
    print("示例：export IDRAC_PASS='你的iDRAC密码'")
    sys.exit(1)

# 检查间隔（秒）
CHECK_INTERVAL = 30

# 风扇速度 hex 值（对应大致百分比，R720xd 常见值）
# 注意：不同固件/机型可能有差异，建议先手动测试
FAN_SPEEDS = {
    "low":  "0x0a",   # ≈10%  （0x0a 通常是安全的最低转速，别设太低如 0x00~0x05）
    "med":  "0x14",   # ≈20%
    "high": "0x14"    # >80°C 目前也用 20%，可改为 "0x1e" ≈30% 或更高
}

# 温度阈值（℃）
TEMP_LOW  = 65
TEMP_HIGH = 80

# 全局变量
auto_mode = True
current_fan_hex = "0x14"          # 初始值，仅用于显示
current_temp = "N/A"
status_log = []

def run_ipmi(cmd):
    """执行 ipmitool 命令"""
    full_cmd = [
        "ipmitool", "-I", "lanplus",
        "-H", IDRAC_IP,
        "-U", IDRAC_USER,
        "-P", IDRAC_PASS
    ] + cmd
    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode != 0:
            return f"Error: {result.stderr.strip() or 'ipmitool 返回非零退出码'}"
        output = result.stdout.strip()
        return output or "OK"
    except subprocess.TimeoutExpired:
        return "Error: ipmitool 命令超时"
    except Exception as e:
        return f"Exception: {str(e)}"

def enable_manual_mode():
    """启用手动风扇控制模式"""
    return run_ipmi(["raw", "0x30", "0x30", "0x01", "0x00"])

def set_fan_speed(hex_val):
    """设置风扇速度（hex 格式，如 0x14）"""
    global current_fan_hex
    result = run_ipmi(["raw", "0x30", "0x30", "0x02", "0xff", hex_val])
    if "Error" not in result:
        current_fan_hex = hex_val
    return result

def get_max_cpu_temp():
    """获取所有 CPU 的最高温度"""
    output = run_ipmi(["sdr", "type", "Temperature"])
    if "Error" in output or not output:
        return None
    
    lines = output.splitlines()
    cpu_temps = []
    for line in lines:
        if "CPU" in line.upper() and "|" in line:
            parts = line.split("|")
            if len(parts) > 4:
                temp_part = parts[4].strip()
                # 提取数字部分（如 "47 degrees C" → 47）
                try:
                    temp = int(temp_part.split()[0])
                    cpu_temps.append(temp)
                except (ValueError, IndexError):
                    pass
    return max(cpu_temps) if cpu_temps else None

def auto_control_loop():
    global auto_mode, current_temp, status_log
    # 程序启动时先强制启用手动模式
    enable_manual_mode()
    
    while True:
        if auto_mode:
            temp = get_max_cpu_temp()
            if temp is not None:
                current_temp = temp
                log_msg = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Temp: {temp}°C"
                
                if temp > TEMP_HIGH:
                    result = set_fan_speed(FAN_SPEEDS["high"])
                    log_msg += f" → High ({FAN_SPEEDS['high']})"
                elif temp > TEMP_LOW:
                    result = set_fan_speed(FAN_SPEEDS["med"])
                    log_msg += f" → Med ({FAN_SPEEDS['med']})"
                else:
                    result = set_fan_speed(FAN_SPEEDS["low"])
                    log_msg += f" → Low ({FAN_SPEEDS['low']})"
                
                # 如果设置失败，记录错误
                if "Error" in result:
                    log_msg += f"  (设置失败: {result})"
                
                status_log.append(log_msg)
                if len(status_log) > 20:
                    status_log.pop(0)
            else:
                status_log.append(
                    f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 无法读取温度"
                )
        
        time.sleep(CHECK_INTERVAL)

# 启动后台自动控制线程
threading.Thread(target=auto_control_loop, daemon=True).start()

@app.route("/")
def index():
    fan_display = current_fan_hex
    percent_map = {"0x0a": "10%", "0x14": "20%", "0x1e": "30%"}  # 可扩展
    percent = percent_map.get(current_fan_hex, "??%")
    
    return render_template(
        "index.html",
        temp=current_temp,
        fan=fan_display,
        percent=percent,
        auto=auto_mode,
        logs=status_log
    )

@app.route("/set_fan", methods=["POST"])
def set_fan():
    speed = request.form.get("speed")
    if speed in FAN_SPEEDS:
        hex_val = FAN_SPEEDS[speed]
        result = set_fan_speed(hex_val)
        return jsonify({
            "status": "success" if "Error" not in result else "error",
            "result": result,
            "fan": hex_val
        })
    return jsonify({"status": "error", "message": "无效的速度选项"})

@app.route("/toggle_auto", methods=["POST"])
def toggle_auto():
    global auto_mode
    auto_mode = not auto_mode
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    if auto_mode:
        status_log.append(f"{now} - 自动模式已开启")
        # 开启时立即运行一次调节
        threading.Thread(target=auto_control_loop, daemon=True).start()  # 可选：立即触发一次
    else:
        status_log.append(f"{now} - 自动模式已关闭")
    return jsonify({"auto": auto_mode})

if __name__ == "__main__":
    print(f"启动 Dell R720xd 风扇控制 Web 面板...")
    print(f"iDRAC: {IDRAC_IP}   用户: {IDRAC_USER}")
    print("访问地址: http://0.0.0.0:5000 （或你的服务器IP:5000）")
    app.run(host="0.0.0.0", port=5000, debug=False)