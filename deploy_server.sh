#!/bin/bash
# 云服务器快速部署脚本

echo "========================================="
echo "远程唤醒系统 - 云服务器部署脚本"
echo "========================================="

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "错误: 请使用root用户运行此脚本"
    echo "使用方法: sudo bash deploy_server.sh"
    exit 1
fi

# 安装Python3和pip
echo ""
echo "[1/6] 安装Python3和依赖..."
if command -v apt-get &> /dev/null; then
    apt-get update
    apt-get install -y python3 python3-pip
elif command -v yum &> /dev/null; then
    yum install -y python3 python3-pip
else
    echo "错误: 不支持的Linux发行版"
    exit 1
fi

# 创建项目目录
echo ""
echo "[2/6] 创建项目目录..."
PROJECT_DIR="/opt/remote-wakeup"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# 安装Python依赖
echo ""
echo "[3/6] 安装Python依赖包..."
pip3 install Flask==3.0.0 Flask-CORS==4.0.0 python-dotenv==1.0.0

# 创建配置文件
echo ""
echo "[4/6] 创建配置文件..."
mkdir -p config logs

# 生成随机密钥
API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 提示用户输入Web密码
echo ""
echo "请设置Web界面访问密码:"
read -s -p "Web密码: " WEB_PASSWORD
echo ""
read -s -p "确认密码: " WEB_PASSWORD_CONFIRM
echo ""

if [ "$WEB_PASSWORD" != "$WEB_PASSWORD_CONFIRM" ]; then
    echo "错误: 两次输入的密码不一致"
    exit 1
fi

if [ -z "$WEB_PASSWORD" ]; then
    echo "警告: 未设置密码，使用默认密码 'admin123'"
    WEB_PASSWORD="admin123"
fi

cat > config/server_config.json <<EOF
{
  "host": "0.0.0.0",
  "port": 5000,
  "api_key": "$API_KEY",
  "web_password": "$WEB_PASSWORD",
  "secret_key": "$SECRET_KEY",
  "debug": false,
  "log_file": "logs/server.log",
  "task_retention_seconds": 3600
}
EOF

echo "配置完成！"
echo "API密钥: $API_KEY"
echo "Web密码: $WEB_PASSWORD"
echo "Secret密钥: $SECRET_KEY"
echo ""
echo "请务必保存这些信息！"

# 配置防火墙
echo ""
echo "[5/6] 配置防火墙..."
if command -v ufw &> /dev/null; then
    ufw allow 5000/tcp
    ufw reload
    echo "ufw防火墙规则已添加"
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=5000/tcp
    firewall-cmd --reload
    echo "firewalld防火墙规则已添加"
else
    echo "警告: 未检测到防火墙，请手动开放5000端口"
fi

# 创建systemd服务
echo ""
echo "[6/6] 创建systemd服务..."
cat > /etc/systemd/system/remote-wakeup-server.service <<EOF
[Unit]
Description=Remote Wake-Up Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/python3 $PROJECT_DIR/server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
systemctl daemon-reload
systemctl enable remote-wakeup-server
systemctl start remote-wakeup-server

echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
echo ""
echo "服务状态:"
systemctl status remote-wakeup-server --no-pager
echo ""
echo "========================================="
echo "重要信息（请保存）："
echo "========================================="
echo "API密钥: $API_KEY"
echo "Web密码: $WEB_PASSWORD"
echo "Secret密钥: $SECRET_KEY"
echo ""
echo "访问地址: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "查看日志: tail -f $PROJECT_DIR/logs/server.log"
echo ""
echo "========================================="
echo "下一步："
echo "1. 访问Web界面并使用上述Web密码登录"
echo "2. 在树莓派客户端配置中使用API密钥"
echo "==========================================="
echo ""
