# 快速开始指南

## 概述

这是一个完整的远程唤醒(WOL)解决方案，让你可以从互联网任何地方唤醒局域网内的计算机。

## 5分钟快速部署

### 第1步: 配置目标计算机（需要被唤醒的电脑）

#### Windows系统:
1. 设备管理器 → 网络适配器 → 右键网卡 → 属性 → 电源管理
2. 勾选"允许此设备唤醒计算机"和"只允许魔术包唤醒计算机"
3. 重启进入BIOS，启用 "Wake on LAN" 功能
4. 获取MAC地址: 运行 `ipconfig /all`，记录"物理地址"

#### Linux系统:
```bash
sudo ethtool -s eth0 wol g
ip link show eth0  # 获取MAC地址
```

### 第2步: 部署云服务器

在云服务器上运行：

```bash
# 下载项目文件
cd /opt
git clone <你的仓库地址> remote-wakeup
cd remote-wakeup

# 运行部署脚本
bash deploy_server.sh
```

脚本会自动：
- 安装依赖
- 生成API密钥
- 配置防火墙
- 启动服务

**重要**: 保存脚本输出的API密钥！

### 第3步: 部署树莓派客户端

在树莓派上运行：

```bash
# 下载项目文件
cd ~
git clone <你的仓库地址> remote-wakeup
cd remote-wakeup

# 运行部署脚本
bash deploy_client.sh
```

按提示输入：
- 云服务器地址（如: http://1.2.3.4:5000）
- API密钥（从第2步获取）
- 设备信息（名称、MAC地址、IP地址等）

### 第4步: 测试系统

#### 方法1: 使用Web界面
在浏览器访问: `http://你的服务器IP:5000`

点击设备旁的"唤醒"按钮后，系统会：
1. 发送WOL魔术包
2. 自动验证设备是否成功启动 🆕
3. 返回启动结果，包括启动用时

示例响应：
```
✓ 任务完成
设备 my-pc 已成功启动，用时 45 秒 [✓ 已验证在线，启动用时: 45秒]
```

#### 方法2: 使用curl命令
```bash
curl -X POST http://你的服务器IP:5000/api/wake \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 你的API密钥" \
  -d '{"device": "my-pc"}'
```

响应示例（包含验证结果）：
```json
{
  "task_id": "uuid",
  "result": {
    "success": true,
    "message": "设备 my-pc 已成功启动，用时 45 秒",
    "verification": {
      "verified": true,
      "online": true,
      "boot_time": 45
    }
  }
}
```

#### 方法3: 运行测试脚本
```bash
cd remote-wakeup
python3 test.py  # 基本功能测试
python3 test_verification.py  # 验证功能测试 🆕
```

## 手动安装（不使用部署脚本）

### 云服务器手动安装

```bash
# 1. 安装依赖
pip3 install Flask Flask-CORS requests python-dotenv

# 2. 编辑配置
nano config/server_config.json
# 修改 api_key 为一个安全的随机字符串

# 3. 运行服务器
python3 server.py

# 4. 配置开机自启（可选）
# 参考 DEPLOYMENT.md 中的 systemd 配置
```

### 树莓派手动安装

```bash
# 1. 安装依赖
pip3 install requests python-dotenv

# 2. 编辑配置
nano config/client_config.json
# 修改 server_url 和 api_key
# 添加你的设备信息

# 3. 运行客户端
python3 client.py

# 4. 配置开机自启（可选）
# 参考 DEPLOYMENT.md 中的 systemd 配置
```

## 配置示例

### 服务器配置 (config/server_config.json)
```json
{
  "host": "0.0.0.0",
  "port": 5000,
  "api_key": "生成一个32位以上的随机字符串",
  "debug": false,
  "log_file": "logs/server.log",
  "task_retention_seconds": 3600
}
```

### 客户端配置 (config/client_config.json)
```json
{
  "server_url": "http://你的云服务器IP:5000",
  "api_key": "与服务器相同的API密钥",
  "poll_interval": 10,
  "verify_timeout": 120,
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

**配置说明**：
- `verify_timeout`: 等待设备启动的超时时间（秒），默认120秒 🆕
- `ip`: 设备IP地址，用于验证启动是否成功，未配置则不验证 🆕

## 常见问题

### Q1: 如何生成安全的API密钥？
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Q2: 如何确定局域网广播地址？
如果你的网络是 `192.168.1.0/24`，广播地址通常是 `192.168.1.255`

### Q3: 无法唤醒计算机怎么办？
1. 确认BIOS已启用WOL
2. 确认网卡支持WOL
3. 确认MAC地址配置正确
4. 在局域网内测试: `python3 wol.py AA:BB:CC:DD:EE:FF`

### Q4: 树莓派无法连接服务器？
1. 检查服务器是否运行: `curl http://服务器IP:5000/health`
2. 检查防火墙是否开放5000端口
3. 检查API密钥是否匹配

### Q5: 如何查看日志？
```bash
# 服务器日志
tail -f logs/server.log

# 客户端日志
tail -f logs/client.log
```

### Q6: 启动验证一直显示"设备未响应"？ 🆕
可能原因及解决方法：
1. **启动时间较长**: 在配置文件中增加 `verify_timeout` (如改为180或240秒)
2. **防火墙阻止Ping**: 在设备防火墙中允许ICMP回显请求
   - Windows: 控制面板 → Windows Defender 防火墙 → 高级设置 → 入站规则 → 启用"文件和打印机共享(回显请求 - ICMPv4-In)"
   - Linux: `sudo ufw allow proto icmp`
3. **IP地址错误**: 确认配置的IP地址正确，建议使用静态IP或DHCP保留
4. **设备未成功启动**: 检查BIOS设置和网卡WOL配置

## 使用API

### 唤醒设备
```bash
curl -X POST http://服务器:5000/api/wake \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 你的密钥" \
  -d '{"device": "设备名称"}'
```

### 查询任务状态
```bash
curl -X GET http://服务器:5000/api/tasks/任务ID \
  -H "X-API-Key: 你的密钥"
```

### 查看统计信息
```bash
curl -X GET http://服务器:5000/api/stats \
  -H "X-API-Key: 你的密钥"
```

## 进阶使用

### 添加多个设备
编辑 `config/client_config.json`，在 `devices` 部分添加更多设备：

```json
"devices": {
  "pc-1": {
    "mac": "AA:BB:CC:DD:EE:FF",
    "broadcast": "192.168.1.255",
    "description": "主计算机"
  },
  "pc-2": {
    "mac": "11:22:33:44:55:66",
    "broadcast": "192.168.1.255",
    "description": "备用计算机"
  }
}
```

然后重启客户端：
```bash
sudo systemctl restart remote-wakeup-client
```

### 配置HTTPS
使用Nginx作为反向代理并配置Let's Encrypt证书，详见 [DEPLOYMENT.md](DEPLOYMENT.md)

### 从移动设备使用
安装支持HTTP请求的App（如Shortcuts、Tasker等），配置API调用即可。

## 目录结构

```
RemoteWakeUp/
├── server.py              # 云服务器端程序
├── client.py              # 树莓派客户端程序
├── wol.py                 # WOL魔术包发送模块
├── test.py                # 测试工具
├── requirements.txt       # Python依赖
├── config/
│   ├── server_config.json # 服务器配置
│   └── client_config.json # 客户端配置
├── logs/                  # 日志目录（自动创建）
├── README.md              # 项目说明
├── QUICKSTART.md          # 本文件
├── DEPLOYMENT.md          # 详细部署指南
└── ARCHITECTURE.md        # 架构说明
```

## 下一步

- 阅读 [ARCHITECTURE.md](ARCHITECTURE.md) 了解系统架构
- 阅读 [DEPLOYMENT.md](DEPLOYMENT.md) 了解详细部署步骤
- 查看 [README.md](README.md) 了解完整功能

## 获取帮助

如遇到问题：
1. 查看日志文件
2. 运行测试脚本: `python3 test.py`
3. 阅读故障排查部分
4. 提交Issue

祝使用愉快！🚀
