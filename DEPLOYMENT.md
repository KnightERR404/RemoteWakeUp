# 系统部署指南

## 系统架构概述

本系统实现从互联网远程唤醒局域网内计算机的功能，架构如下：

```
用户 → 云服务器(API) → 树莓派(客户端) → 目标计算机
```

## 部署前准备

### 1. 硬件要求

- **云服务器**: 任意云服务商的VPS，1核1G即可
- **树莓派**: 树莓派3B+或更高版本，需要有线网络连接
- **路由器**: 支持端口转发（可选）
- **目标计算机**: 支持WOL功能的网卡和BIOS

### 2. 软件要求

- Python 3.7 或更高版本
- pip (Python包管理器)

### 3. 网络要求

- 云服务器需要公网IP
- 树莓派需要能够访问互联网
- 树莓派与目标计算机在同一局域网

## 详细部署步骤

### 第一步：配置目标计算机

#### Windows系统

1. **启用网卡WOL功能**
   - 按 `Win + X`，选择"设备管理器"
   - 展开"网络适配器"
   - 右键点击网卡 → 选择"属性"
   - 切换到"电源管理"选项卡
   - 勾选以下选项：
     - ✓ 允许此设备唤醒计算机
     - ✓ 只允许魔术包唤醒计算机
   - 点击"确定"保存

2. **启用BIOS WOL功能**
   - 重启计算机，进入BIOS设置（通常按Del、F2或F12）
   - 找到电源管理选项（Power Management）
   - 启用以下选项：
     - Wake on LAN
     - Wake on PCI-E (或 Wake on PCIe Device)
   - 保存并退出BIOS

3. **获取MAC地址**
   ```cmd
   ipconfig /all
   ```
   找到"物理地址"，格式如: `AA-BB-CC-DD-EE-FF`

4. **网络设置**
   - 建议设置静态IP地址
   - 记录IP地址和广播地址（通常是网段的.255地址）

#### Linux系统

1. **检查WOL支持**
   ```bash
   sudo ethtool eth0 | grep Wake-on
   ```
   输出应包含: `Supports Wake-on: g`

2. **启用WOL**
   ```bash
   sudo ethtool -s eth0 wol g
   ```

3. **永久启用WOL**（Ubuntu/Debian）
   ```bash
   # 创建systemd服务
   sudo nano /etc/systemd/system/wol.service
   ```
   
   添加以下内容：
   ```ini
   [Unit]
   Description=Enable Wake-on-LAN
   After=network.target
   
   [Service]
   Type=oneshot
   ExecStart=/sbin/ethtool -s eth0 wol g
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   启用服务：
   ```bash
   sudo systemctl enable wol.service
   sudo systemctl start wol.service
   ```

4. **获取MAC地址**
   ```bash
   ip link show eth0
   ```

### 第二步：部署云服务器

1. **连接到云服务器**
   ```bash
   ssh root@your-server-ip
   ```

2. **安装Python和pip**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3 python3-pip -y
   
   # CentOS/RHEL
   sudo yum install python3 python3-pip -y
   ```

3. **创建项目目录**
   ```bash
   mkdir -p /opt/remote-wakeup
   cd /opt/remote-wakeup
   ```

4. **上传项目文件**
   ```bash
   # 方法1: 使用scp从本地上传
   scp -r RemoteWakeUp root@your-server-ip:/opt/
   
   # 方法2: 使用git克隆（如果已上传到仓库）
   git clone <your-repo-url> .
   
   # 方法3: 手动创建文件
   # 将server.py, wol.py, requirements.txt等文件上传
   ```

5. **安装依赖**
   ```bash
   cd /opt/remote-wakeup
   pip3 install -r requirements.txt
   ```

6. **配置服务器**
   ```bash
   nano config/server_config.json
   ```
   
   修改以下内容：
   ```json
   {
     "host": "0.0.0.0",
     "port": 5000,
     "api_key": "your-secure-random-api-key-here",
     "debug": false,
     "log_file": "logs/server.log",
     "task_retention_seconds": 3600
   }
   ```
   
   **重要**: 请生成一个安全的随机API密钥，例如：
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

7. **配置防火墙**
   ```bash
   # Ubuntu (ufw)
   sudo ufw allow 5000/tcp
   sudo ufw reload
   
   # CentOS (firewalld)
   sudo firewall-cmd --permanent --add-port=5000/tcp
   sudo firewall-cmd --reload
   ```

8. **创建systemd服务**
   ```bash
   sudo nano /etc/systemd/system/remote-wakeup-server.service
   ```
   
   添加以下内容：
   ```ini
   [Unit]
   Description=Remote Wake-Up Server
   After=network.target
   
   [Service]
   Type=simple
   User=root
   WorkingDirectory=/opt/remote-wakeup
   ExecStart=/usr/bin/python3 /opt/remote-wakeup/server.py
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```

9. **启动服务**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable remote-wakeup-server
   sudo systemctl start remote-wakeup-server
   
   # 查看状态
   sudo systemctl status remote-wakeup-server
   
   # 查看日志
   tail -f /opt/remote-wakeup/logs/server.log
   ```

10. **测试服务器**
    ```bash
    curl http://localhost:5000/health
    ```
    
    应返回: `{"status":"healthy","timestamp":"..."}`

### 第三步：部署树莓派客户端

1. **连接到树莓派**
   ```bash
   ssh pi@raspberrypi.local
   ```

2. **安装Python和pip**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip -y
   ```

3. **创建项目目录**
   ```bash
   mkdir -p /home/pi/remote-wakeup
   cd /home/pi/remote-wakeup
   ```

4. **上传项目文件**
   ```bash
   # 从本地上传
   scp client.py wol.py requirements.txt pi@raspberrypi.local:/home/pi/remote-wakeup/
   scp -r config pi@raspberrypi.local:/home/pi/remote-wakeup/
   ```

5. **安装依赖**
   ```bash
   cd /home/pi/remote-wakeup
   pip3 install -r requirements.txt
   ```

6. **配置客户端**
   ```bash
   nano config/client_config.json
   ```
   
   修改以下内容：
   ```json
   {
     "server_url": "http://your-server-ip:5000",
     "api_key": "your-secure-random-api-key-here",
     "poll_interval": 10,
     "log_file": "logs/client.log",
     "devices": {
       "my-pc": {
         "mac": "AA:BB:CC:DD:EE:FF",
         "ip": "192.168.1.100",
         "broadcast": "192.168.1.255",
         "port": 9,
         "description": "我的主计算机"
       }
     }
   }
   ```
   
   **配置说明**:
   - `server_url`: 云服务器的地址（使用公网IP）
   - `api_key`: 与服务器配置相同的API密钥
   - `poll_interval`: 轮询间隔（秒）
   - `devices`: 可唤醒的设备列表
     - `mac`: 目标计算机的MAC地址
     - `ip`: 目标计算机的IP地址（可选）
     - `broadcast`: 局域网广播地址
     - `port`: WOL端口（通常为9或7）

7. **获取局域网广播地址**
   ```bash
   ip addr show
   ```
   例如网络为 `192.168.1.0/24`，广播地址为 `192.168.1.255`

8. **测试客户端**
   ```bash
   python3 client.py
   ```
   
   观察日志输出，确认能够连接到服务器

9. **创建systemd服务**
   ```bash
   sudo nano /etc/systemd/system/remote-wakeup-client.service
   ```
   
   添加以下内容：
   ```ini
   [Unit]
   Description=Remote Wake-Up Client
   After=network.target
   
   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/remote-wakeup
   ExecStart=/usr/bin/python3 /home/pi/remote-wakeup/client.py
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```

10. **启动客户端服务**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable remote-wakeup-client
    sudo systemctl start remote-wakeup-client
    
    # 查看状态
    sudo systemctl status remote-wakeup-client
    
    # 查看日志
    tail -f /home/pi/remote-wakeup/logs/client.log
    ```

### 第四步：测试系统

1. **使用Web界面**
   
   在浏览器中访问: `http://your-server-ip:5000`
   
   - 输入API密钥
   - 输入设备名称（如 `my-pc`）
   - 点击"唤醒设备"按钮

2. **使用curl命令**
   ```bash
   curl -X POST http://your-server-ip:5000/api/wake \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your-api-key" \
     -d '{"device": "my-pc"}'
   ```

3. **查看日志**
   
   **服务器日志**:
   ```bash
   tail -f /opt/remote-wakeup/logs/server.log
   ```
   
   **客户端日志**:
   ```bash
   tail -f /home/pi/remote-wakeup/logs/client.log
   ```

4. **验证结果**
   
   目标计算机应该在几秒钟内启动（前提是处于关机或休眠状态）

## 使用HTTPS（推荐）

为了安全性，建议使用HTTPS。可以使用Nginx作为反向代理并配置SSL证书。

1. **安装Nginx和Certbot**
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx -y
   ```

2. **配置Nginx**
   ```bash
   sudo nano /etc/nginx/sites-available/remote-wakeup
   ```
   
   添加配置：
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }
   ```

3. **启用站点并获取SSL证书**
   ```bash
   sudo ln -s /etc/nginx/sites-available/remote-wakeup /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   
   sudo certbot --nginx -d your-domain.com
   ```

4. **更新客户端配置**
   ```json
   "server_url": "https://your-domain.com"
   ```

## 故障排查

### 问题1: 无法唤醒计算机

**可能原因**:
- BIOS未启用WOL
- 网卡驱动不支持WOL
- MAC地址配置错误
- 计算机完全断电（需要保持电源连接）

**排查步骤**:
1. 检查BIOS设置
2. 在局域网内测试WOL: `python3 wol.py AA:BB:CC:DD:EE:FF`
3. 检查MAC地址是否正确
4. 确保计算机连接电源

### 问题2: 客户端无法连接服务器

**可能原因**:
- 服务器防火墙阻止
- API密钥不匹配
- 服务器未启动

**排查步骤**:
1. 检查服务器状态: `sudo systemctl status remote-wakeup-server`
2. 测试网络连通性: `curl http://server-ip:5000/health`
3. 检查API密钥是否匹配
4. 查看服务器日志

### 问题3: 服务异常退出

**排查步骤**:
1. 查看systemd日志: `sudo journalctl -u remote-wakeup-server -n 50`
2. 查看应用日志: `tail -100 logs/server.log`
3. 检查Python依赖是否完整: `pip3 list`

## 安全建议

1. **使用强API密钥**: 至少32个字符的随机字符串
2. **启用HTTPS**: 使用SSL证书加密通信
3. **限制IP访问**: 使用防火墙规则限制访问
4. **定期更新**: 保持系统和依赖包更新
5. **监控日志**: 定期检查异常访问
6. **使用VPN**: 考虑通过VPN访问服务器

## 高级配置

### 配置多个客户端

可以在不同的局域网部署多个树莓派客户端，它们可以唤醒各自局域网内的设备。

### 配置邮件通知

可以集成邮件通知功能，在唤醒任务完成后发送通知邮件。

### 配置Web Hook

可以配置Web Hook，在特定事件发生时调用外部API。

## 维护

### 查看服务状态
```bash
# 服务器
sudo systemctl status remote-wakeup-server

# 客户端
sudo systemctl status remote-wakeup-client
```

### 重启服务
```bash
# 服务器
sudo systemctl restart remote-wakeup-server

# 客户端
sudo systemctl restart remote-wakeup-client
```

### 查看日志
```bash
# 服务器
tail -f /opt/remote-wakeup/logs/server.log

# 客户端
tail -f /home/pi/remote-wakeup/logs/client.log
```

### 更新配置
修改配置文件后需要重启相应的服务。

## 支持

如有问题，请查看日志文件或提交Issue。
