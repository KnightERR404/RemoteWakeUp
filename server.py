"""
远程唤醒系统 - 云服务器端

提供RESTful API接口，接收唤醒请求并维护任务队列供树莓派客户端轮询
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_cors import CORS


# 初始化Flask应用
app = Flask(__name__)
app.secret_key = None  # 将在加载配置后设置
CORS(app)

# 全局变量
config = {}
tasks = {}  # 任务队列: {task_id: {device, status, created_at, completed_at, client_id}}
logger = None


def setup_logging(log_file='logs/server.log'):
    """设置日志系统"""
    global logger
    
    # 创建日志目录
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 配置日志
    logger = logging.getLogger('RemoteWakeUpServer')
    logger.setLevel(logging.INFO)
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def load_config(config_path='config/server_config.json'):
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"配置文件不存在: {config_path}")
        # 返回默认配置
        return {
            'host': '0.0.0.0',
            'port': 5000,
            'api_key': 'change-this-to-a-secure-random-key',
            'web_password': 'change-this-password',
            'secret_key': 'change-this-secret-key-to-random-string',
            'debug': False,
            'log_file': 'logs/server.log',
            'task_retention_seconds': 3600
        }
    except json.JSONDecodeError as e:
        logger.error(f"配置文件格式错误: {e}")
        raise


def require_web_login(f):
    """Web界面登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def require_api_key(f):
    """API密钥认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            logger.warning(f"未提供API密钥: IP={request.remote_addr}")
            return jsonify({
                'status': 'error',
                'message': '未提供API密钥'
            }), 401
        
        if api_key != config.get('api_key'):
            logger.warning(f"无效的API密钥: IP={request.remote_addr}")
            return jsonify({
                'status': 'error',
                'message': 'API密钥无效'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def cleanup_old_tasks():
    """清理过期的任务"""
    retention_seconds = config.get('task_retention_seconds', 3600)
    cutoff_time = datetime.now() - timedelta(seconds=retention_seconds)
    
    tasks_to_remove = []
    for task_id, task in tasks.items():
        created_at = datetime.fromisoformat(task['created_at'])
        if created_at < cutoff_time:
            tasks_to_remove.append(task_id)
    
    for task_id in tasks_to_remove:
        del tasks[task_id]
        logger.info(f"清理过期任务: task_id={task_id}")


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Web登录页面"""
    if request.method == 'POST':
        password = request.form.get('password')
        
        if password == config.get('web_password'):
            session['logged_in'] = True
            logger.info(f"Web登录成功: IP={request.remote_addr}")
            return redirect(url_for('index'))
        else:
            logger.warning(f"Web登录失败: IP={request.remote_addr}")
            error = '密码错误'
    else:
        error = None
    
    # 如果已登录，直接跳转到主页
    if session.get('logged_in'):
        return redirect(url_for('index'))
    
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>登录 - 远程唤醒系统</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
                background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0d1b2a 100%);
                background-attachment: fixed;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
                position: relative;
                overflow-x: hidden;
            }}
            
            /* 动态背景粒子效果 */
            body::before {{
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-image: 
                    radial-gradient(circle at 20% 50%, rgba(0, 116, 217, 0.15) 0%, transparent 50%),
                    radial-gradient(circle at 80% 80%, rgba(147, 51, 234, 0.15) 0%, transparent 50%),
                    radial-gradient(circle at 40% 20%, rgba(59, 130, 246, 0.1) 0%, transparent 50%);
                animation: float 20s ease-in-out infinite;
                pointer-events: none;
            }}
            
            @keyframes float {{
                0%, 100% {{ transform: translate(0, 0) scale(1); }}
                33% {{ transform: translate(30px, -30px) scale(1.1); }}
                66% {{ transform: translate(-20px, 20px) scale(0.9); }}
            }}
            
            .container {{
                background: rgba(15, 23, 42, 0.85);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(59, 130, 246, 0.2);
                border-radius: 24px;
                padding: 48px 40px;
                box-shadow: 
                    0 8px 32px rgba(0, 0, 0, 0.5),
                    0 0 100px rgba(59, 130, 246, 0.1),
                    inset 0 0 60px rgba(59, 130, 246, 0.03);
                max-width: 440px;
                width: 100%;
                position: relative;
                animation: slideUp 0.6s ease-out;
            }}
            
            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateY(30px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            
            .lock-icon {{
                width: 80px;
                height: 80px;
                margin: 0 auto 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(147, 51, 234, 0.2));
                border-radius: 20px;
                font-size: 40px;
                box-shadow: 0 0 40px rgba(59, 130, 246, 0.3);
                animation: pulse 2s ease-in-out infinite;
            }}
            
            @keyframes pulse {{
                0%, 100% {{
                    box-shadow: 0 0 40px rgba(59, 130, 246, 0.3);
                    transform: scale(1);
                }}
                50% {{
                    box-shadow: 0 0 60px rgba(59, 130, 246, 0.5);
                    transform: scale(1.05);
                }}
            }}
            
            h1 {{
                color: #f1f5f9;
                margin-bottom: 12px;
                font-size: 32px;
                text-align: center;
                font-weight: 700;
                letter-spacing: -0.5px;
                background: linear-gradient(135deg, #f1f5f9 0%, #cbd5e1 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            
            .subtitle {{
                color: #94a3b8;
                margin-bottom: 36px;
                font-size: 15px;
                text-align: center;
                font-weight: 400;
            }}
            
            .form-group {{
                margin-bottom: 24px;
            }}
            
            label {{
                display: block;
                color: #cbd5e1;
                margin-bottom: 10px;
                font-weight: 500;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            input {{
                width: 100%;
                padding: 14px 16px;
                background: rgba(30, 41, 59, 0.6);
                border: 1.5px solid rgba(59, 130, 246, 0.3);
                border-radius: 12px;
                font-size: 15px;
                color: #f1f5f9;
                transition: all 0.3s ease;
                font-family: inherit;
            }}
            
            input::placeholder {{
                color: #64748b;
            }}
            
            input:focus {{
                outline: none;
                border-color: #3b82f6;
                background: rgba(30, 41, 59, 0.8);
                box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1),
                            0 0 20px rgba(59, 130, 246, 0.2);
            }}
            
            button {{
                width: 100%;
                padding: 16px;
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(59, 130, 246, 0.4);
            }}
            
            button::before {{
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
                transition: left 0.5s;
            }}
            
            button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 30px rgba(59, 130, 246, 0.5);
            }}
            
            button:hover::before {{
                left: 100%;
            }}
            
            button:active {{
                transform: translateY(0);
            }}
            
            .error {{
                background: rgba(239, 68, 68, 0.15);
                color: #fca5a5;
                padding: 14px;
                border-radius: 12px;
                margin-bottom: 24px;
                border: 1px solid rgba(239, 68, 68, 0.3);
                text-align: center;
                font-size: 14px;
                animation: shake 0.5s ease;
            }}
            
            @keyframes shake {{
                0%, 100% {{ transform: translateX(0); }}
                25% {{ transform: translateX(-10px); }}
                75% {{ transform: translateX(10px); }}
            }}
            
            /* 移动端适配 */
            @media (max-width: 480px) {{
                body {{
                    padding: 16px;
                }}
                
                .container {{
                    padding: 36px 24px;
                    border-radius: 20px;
                }}
                
                h1 {{
                    font-size: 26px;
                }}
                
                .subtitle {{
                    font-size: 14px;
                }}
                
                .lock-icon {{
                    width: 64px;
                    height: 64px;
                    font-size: 32px;
                }}
                
                input {{
                    padding: 12px 14px;
                    font-size: 14px;
                }}
                
                button {{
                    padding: 14px;
                    font-size: 15px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="lock-icon">🔒</div>
            <h1>远程唤醒系统</h1>
            <p class="subtitle">请输入密码以继续访问</p>
            
            {'<div class="error">❌ ' + error + '</div>' if error else ''}
            
            <form method="POST">
                <div class="form-group">
                    <label for="password">访问密码</label>
                    <input type="password" id="password" name="password" 
                           placeholder="输入您的密码" required autofocus>
                </div>
                
                <button type="submit">🔓 解锁并登录</button>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route('/logout')
def logout():
    """登出"""
    session.pop('logged_in', None)
    logger.info(f"用户登出: IP={request.remote_addr}")
    return redirect(url_for('login'))


@app.route('/')
@require_web_login
def index():
    """Web界面首页"""
    html = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>远程唤醒系统</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
                background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0d1b2a 100%);
                background-attachment: fixed;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
                position: relative;
                overflow-x: hidden;
            }
            
            /* 动态背景效果 */
            body::before {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-image: 
                    radial-gradient(circle at 20% 50%, rgba(0, 116, 217, 0.15) 0%, transparent 50%),
                    radial-gradient(circle at 80% 80%, rgba(147, 51, 234, 0.15) 0%, transparent 50%),
                    radial-gradient(circle at 40% 20%, rgba(59, 130, 246, 0.1) 0%, transparent 50%);
                animation: float 20s ease-in-out infinite;
                pointer-events: none;
            }
            
            @keyframes float {
                0%, 100% { transform: translate(0, 0) scale(1); }
                33% { transform: translate(30px, -30px) scale(1.1); }
                66% { transform: translate(-20px, 20px) scale(0.9); }
            }
            
            .container {
                background: rgba(15, 23, 42, 0.85);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(59, 130, 246, 0.2);
                border-radius: 24px;
                padding: 40px;
                box-shadow: 
                    0 8px 32px rgba(0, 0, 0, 0.5),
                    0 0 100px rgba(59, 130, 246, 0.1),
                    inset 0 0 60px rgba(59, 130, 246, 0.03);
                max-width: 600px;
                width: 100%;
                animation: slideUp 0.6s ease-out;
            }
            
            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
                flex-wrap: wrap;
                gap: 12px;
            }
            
            h1 {
                color: #f1f5f9;
                font-size: 32px;
                font-weight: 700;
                display: flex;
                align-items: center;
                gap: 12px;
                letter-spacing: -0.5px;
                background: linear-gradient(135deg, #f1f5f9 0%, #cbd5e1 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .logout-btn {
                color: #94a3b8;
                text-decoration: none;
                font-size: 14px;
                padding: 8px 16px;
                border-radius: 8px;
                background: rgba(30, 41, 59, 0.6);
                border: 1px solid rgba(59, 130, 246, 0.2);
                transition: all 0.3s ease;
                display: inline-flex;
                align-items: center;
                gap: 6px;
            }
            
            .logout-btn:hover {
                background: rgba(30, 41, 59, 0.9);
                border-color: #3b82f6;
                color: #cbd5e1;
                transform: translateY(-1px);
            }
            
            .subtitle {
                color: #94a3b8;
                margin-bottom: 32px;
                font-size: 15px;
                font-weight: 400;
            }
            
            .form-group {
                margin-bottom: 24px;
            }
            
            label {
                display: block;
                color: #cbd5e1;
                margin-bottom: 10px;
                font-weight: 500;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            input {
                width: 100%;
                padding: 14px 16px;
                background: rgba(30, 41, 59, 0.6);
                border: 1.5px solid rgba(59, 130, 246, 0.3);
                border-radius: 12px;
                font-size: 15px;
                color: #f1f5f9;
                transition: all 0.3s ease;
                font-family: inherit;
            }
            
            input::placeholder {
                color: #64748b;
            }
            
            input:focus {
                outline: none;
                border-color: #3b82f6;
                background: rgba(30, 41, 59, 0.8);
                box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1),
                            0 0 20px rgba(59, 130, 246, 0.2);
            }
            
            button {
                width: 100%;
                padding: 16px;
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(59, 130, 246, 0.4);
            }
            
            button::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
                transition: left 0.5s;
            }
            
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 30px rgba(59, 130, 246, 0.5);
            }
            
            button:hover::before {
                left: 100%;
            }
            
            button:active {
                transform: translateY(0);
            }
            
            .status {
                margin-top: 24px;
                padding: 16px;
                border-radius: 12px;
                display: none;
                animation: slideIn 0.3s ease;
                font-size: 14px;
            }
            
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateY(-10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .status.success {
                background: rgba(16, 185, 129, 0.15);
                color: #6ee7b7;
                border: 1px solid rgba(16, 185, 129, 0.3);
            }
            
            .status.error {
                background: rgba(239, 68, 68, 0.15);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.3);
            }
            
            .info {
                margin-top: 32px;
                padding: 24px;
                background: rgba(30, 41, 59, 0.4);
                border: 1px solid rgba(59, 130, 246, 0.15);
                border-radius: 16px;
                font-size: 13px;
                color: #94a3b8;
            }
            
            .info h3 {
                color: #cbd5e1;
                margin-bottom: 16px;
                font-size: 16px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .info p {
                margin-bottom: 10px;
                line-height: 1.7;
                padding-left: 20px;
                position: relative;
            }
            
            .info p::before {
                content: '▹';
                position: absolute;
                left: 0;
                color: #3b82f6;
                font-weight: bold;
            }
            
            .info p:last-child {
                margin-bottom: 0;
            }
            
            /* 移动端适配 */
            @media (max-width: 640px) {
                body {
                    padding: 16px;
                }
                
                .container {
                    padding: 28px 24px;
                    border-radius: 20px;
                }
                
                h1 {
                    font-size: 24px;
                }
                
                .subtitle {
                    font-size: 14px;
                    margin-bottom: 24px;
                }
                
                .header {
                    flex-direction: column;
                    align-items: flex-start;
                }
                
                .logout-btn {
                    align-self: flex-end;
                }
                
                input {
                    padding: 12px 14px;
                    font-size: 14px;
                }
                
                button {
                    padding: 14px;
                    font-size: 15px;
                }
                
                .info {
                    padding: 20px;
                    font-size: 12px;
                }
                
                .info h3 {
                    font-size: 15px;
                }
                
                .info p {
                    padding-left: 16px;
                }
            }
            
            @media (max-width: 400px) {
                .container {
                    padding: 24px 20px;
                }
                
                h1 {
                    font-size: 22px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1><span>🌐</span>远程唤醒系统</h1>
                <a href="/logout" class="logout-btn">
                    <span>🚪</span>登出
                </a>
            </div>
            <p class="subtitle">Wake-on-LAN 控制面板</p>
            
            <div class="form-group">
                <label for="apiKey">API 密钥</label>
                <input type="password" id="apiKey" placeholder="输入您的 API 密钥">
            </div>
            
            <div class="form-group">
                <label for="deviceName">设备名称</label>
                <input type="text" id="deviceName" placeholder="例如: my-pc">
            </div>
            
            <button onclick="wakeDevice()">💫 唤醒设备</button>
            
            <div id="status" class="status"></div>
            
            <div class="info">
                <h3>📋 使用说明</h3>
                <p>输入您的 API 密钥（在配置文件中设置）</p>
                <p>输入要唤醒的设备名称（在树莓派配置中定义）</p>
                <p>点击"唤醒设备"按钮发送唤醒请求</p>
                <p>系统会通过树莓派发送 WOL 魔术包并验证启动</p>
            </div>
        </div>
        
        <script>
            async function wakeDevice() {
                const apiKey = document.getElementById('apiKey').value;
                const deviceName = document.getElementById('deviceName').value;
                const statusDiv = document.getElementById('status');
                
                if (!apiKey || !deviceName) {
                    showStatus('⚠️ 请填写所有字段', 'error');
                    return;
                }
                
                try {
                    const response = await fetch('/api/wake', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-API-Key': apiKey
                        },
                        body: JSON.stringify({ device: deviceName })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        showStatus(`✓ ${data.message}`, 'success');
                    } else {
                        showStatus(`✗ ${data.message}`, 'error');
                    }
                } catch (error) {
                    showStatus(`✗ 请求失败: ${error.message}`, 'error');
                }
            }
            
            function showStatus(message, type) {
                const statusDiv = document.getElementById('status');
                statusDiv.textContent = message;
                statusDiv.className = `status ${type}`;
                statusDiv.style.display = 'block';
                
                setTimeout(() => {
                    statusDiv.style.display = 'none';
                }, 5000);
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route('/api/wake', methods=['POST'])
@require_api_key
def wake_device():
    """接收唤醒请求并创建任务"""
    try:
        data = request.get_json()
        device = data.get('device')
        
        if not device:
            return jsonify({
                'status': 'error',
                'message': '未指定设备名称'
            }), 400
        
        # 创建任务
        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            'device': device,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'completed_at': None,
            'client_id': None,
            'result': None
        }
        
        logger.info(
            f"创建唤醒任务: task_id={task_id}, device={device}, "
            f"IP={request.remote_addr}"
        )
        
        # 清理过期任务
        cleanup_old_tasks()
        
        return jsonify({
            'status': 'success',
            'message': '唤醒任务已创建',
            'task_id': task_id
        }), 201
        
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '服务器内部错误'
        }), 500


@app.route('/api/tasks/<task_id>', methods=['GET'])
@require_api_key
def get_task(task_id):
    """查询任务状态"""
    task = tasks.get(task_id)
    
    if not task:
        return jsonify({
            'status': 'error',
            'message': '任务不存在'
        }), 404
    
    return jsonify({
        'status': 'success',
        'task': task
    }), 200


@app.route('/api/poll', methods=['GET'])
@require_api_key
def poll_tasks():
    """客户端轮询接口，获取待处理的任务"""
    client_id = request.args.get('client_id', 'unknown')
    
    # 查找待处理的任务
    pending_tasks = []
    for task_id, task in tasks.items():
        if task['status'] == 'pending':
            pending_tasks.append({
                'task_id': task_id,
                'device': task['device']
            })
    
    logger.debug(
        f"客户端轮询: client_id={client_id}, "
        f"待处理任务数={len(pending_tasks)}"
    )
    
    return jsonify({
        'status': 'success',
        'tasks': pending_tasks
    }), 200


@app.route('/api/report', methods=['POST'])
@require_api_key
def report_task_result():
    """客户端上报任务执行结果"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        success = data.get('success', False)
        message = data.get('message', '')
        client_id = data.get('client_id', 'unknown')
        
        if not task_id:
            return jsonify({
                'status': 'error',
                'message': '未指定任务ID'
            }), 400
        
        task = tasks.get(task_id)
        if not task:
            return jsonify({
                'status': 'error',
                'message': '任务不存在'
            }), 404
        
        # 更新任务状态
        task['status'] = 'completed' if success else 'failed'
        task['completed_at'] = datetime.now().isoformat()
        task['client_id'] = client_id
        task['result'] = {
            'success': success,
            'message': message
        }
        
        logger.info(
            f"任务完成: task_id={task_id}, success={success}, "
            f"client_id={client_id}, message={message}"
        )
        
        return jsonify({
            'status': 'success',
            'message': '任务状态已更新'
        }), 200
        
    except Exception as e:
        logger.error(f"上报任务结果失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '服务器内部错误'
        }), 500


@app.route('/api/stats', methods=['GET'])
@require_api_key
def get_stats():
    """获取系统统计信息"""
    pending = sum(1 for t in tasks.values() if t['status'] == 'pending')
    completed = sum(1 for t in tasks.values() if t['status'] == 'completed')
    failed = sum(1 for t in tasks.values() if t['status'] == 'failed')
    
    return jsonify({
        'status': 'success',
        'stats': {
            'total_tasks': len(tasks),
            'pending': pending,
            'completed': completed,
            'failed': failed
        }
    }), 200


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200


def main():
    """主函数"""
    global config, logger
    
    # 加载配置
    config = load_config()
    
    # 设置Flask secret key（用于session加密）
    app.secret_key = config.get('secret_key', 'change-this-secret-key-to-random-string')
    if app.secret_key == 'change-this-secret-key-to-random-string':
        logger.warning("警告: 使用默认secret_key不安全，请在配置文件中设置")
    
    # 设置日志
    logger = setup_logging(config.get('log_file', 'logs/server.log'))
    
    # 启动信息
    logger.info("=" * 50)
    logger.info("远程唤醒系统 - 云服务器端启动")
    logger.info(f"监听地址: {config['host']}:{config['port']}")
    logger.info(f"Web密码保护: {'已启用' if config.get('web_password') else '未启用'}")
    logger.info(f"调试模式: {config.get('debug', False)}")
    logger.info("=" * 50)
    
    # 启动Flask应用
    app.run(
        host=config['host'],
        port=config['port'],
        debug=config.get('debug', False)
    )


if __name__ == '__main__':
    main()
