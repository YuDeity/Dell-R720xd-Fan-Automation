from flask import Flask, render_template, request, flash, redirect, url_for
import requests
import json
import warnings

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 改成随机字符串

# 忽略 SSL 警告（自签证书常见）
warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        idrac_ip = request.form.get('idrac_ip')
        username = request.form.get('username')
        password = request.form.get('password')
        action = request.form.get('action')  # 'bios_reset' 或 'idrac_reset'

        base_url = f"https://{idrac_ip}/redfish/v1"
        auth = (username, password)

        try:
            if action == 'bios_reset':
                # BIOS 重置到默认（Dell Redfish OEM action）
                payload = {"ResetType": "Default"}
                response = requests.post(
                    f"{base_url}/Systems/System.Embedded.1/Bios/Actions/Bios.ResetBios",
                    auth=auth,
                    json=payload,
                    verify=False,
                    timeout=30
                )
                if response.status_code in [200, 202, 204]:
                    msg = "BIOS 重置请求已发送成功！服务器需重启生效。"
                else:
                    msg = f"失败: {response.status_code} - {response.text}"

            elif action == 'idrac_reset':
                # iDRAC 重置（factory reset）
                payload = {"ResetType": "ForceRestart"}  # 或用 ResetToDefaults 如果支持
                response = requests.post(
                    f"{base_url}/Managers/iDRAC.Embedded.1/Actions/Manager.Reset",
                    auth=auth,
                    json=payload,
                    verify=False,
                    timeout=30
                )
                if response.status_code in [200, 202, 204]:
                    msg = "iDRAC 重置请求已发送！几分钟后 iDRAC 会重启。"
                else:
                    msg = f"失败: {response.status_code} - {response.text}"

            flash(msg, 'success' if '成功' in msg else 'danger')
        except Exception as e:
            flash(f"连接错误: {str(e)}", 'danger')

        return redirect(url_for('index'))

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)