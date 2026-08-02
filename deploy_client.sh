#!/bin/bash
# 树莓派客户端快速部署脚本

echo "========================================="
echo "远程唤醒系统 - 树莓派客户端部署脚本"
echo "========================================="

# 安装Python3和pip
echo ""
echo "[1/5] 安装Python3和依赖..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip

# 创建项目目录
echo ""
echo "[2/5] 创建项目目录..."
PROJECT_DIR="$HOME/remote-wakeup"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# 安装Python依赖
echo ""
echo "[3/5] 安装Python依赖包..."
pip3 install requests==2.31.0 python-dotenv==1.0.0

# 创建目录
mkdir -p config logs

# 配置文件
echo ""
echo "[4/5] 配置客户端..."
echo ""
read -p "请输入云服务器地址 (例如: http://1.2.3.4:5000): " SERVER_URL
read -p "请输入API密钥: " API_KEY
read -p "请输入轮询间隔(秒) [默认: 10]: " POLL_INTERVAL
POLL_INTERVAL=${POLL_INTERVAL:-10}

echo ""
echo "现在配置要唤醒的设备..."
read -p "设备名称 (例如: my-pc): " DEVICE_NAME
read -p "设备MAC地址 (例如: AA:BB:CC:DD:EE:FF): " DEVICE_MAC
read -p "设备IP地址 (例如: 192.168.1.100): " DEVICE_IP
read -p "广播地址 (例如: 192.168.1.255): " DEVICE_BROADCAST
read -p "设备描述 (例如: 我的主计算机): " DEVICE_DESC

cat > config/client_config.json <<EOF
{
  "server_url": "$SERVER_URL",
  "api_key": "$API_KEY",
  "poll_interval": $POLL_INTERVAL,
  "log_file": "logs/client.log",
  "devices": {
    "$DEVICE_NAME": {
      "mac": "$DEVICE_MAC",
      "ip": "$DEVICE_IP",
      "broadcast": "$DEVICE_BROADCAST",
      "port": 9,
      "description": "$DEVICE_DESC"
    }
  }
}
EOF

echo "配置文件已创建"

# 创建systemd服务
echo ""
echo "[5/5] 创建systemd服务..."
sudo tee /etc/systemd/system/remote-wakeup-client.service > /dev/null <<EOF
[Unit]
Description=Remote Wake-Up Client
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/python3 $PROJECT_DIR/client.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable remote-wakeup-client
sudo systemctl start remote-wakeup-client

echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
echo ""
echo "服务状态:"
sudo systemctl status remote-wakeup-client --no-pager
echo ""
echo "查看日志: tail -f $PROJECT_DIR/logs/client.log"
echo ""
echo "添加更多设备: 编辑 $PROJECT_DIR/config/client_config.json"
echo "然后重启服务: sudo systemctl restart remote-wakeup-client"
echo ""
