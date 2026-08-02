# 远程唤醒系统 (Remote Wake-on-LAN)

## 系统架构

本系统实现从互联网外部远程唤醒局域网内计算机的功能，并自动验证启动是否成功，包含三个核心组件：

```
互联网用户
    ↓ (HTTP请求)
云服务器 (server.py)
    ↓ (定期轮询)
树莓派 (client.py)
    ↓ (WOL魔术包)
目标计算机 (被唤醒)
    ↓ (Ping检测)
树莓派 (验证启动) ✓
    ↓ (上报结果)
云服务器 (显示反馈)
```

### 核心功能

- ✅ **远程唤醒**：从互联网发送WOL魔术包唤醒计算机
- ✅ **启动验证**：自动检测设备是否成功启动（通过Ping）
- ✅ **启动反馈**：显示启动耗时和状态，让您知道唤醒是否成功
- ✅ **多设备支持**：管理多台设备
- ✅ **Web界面**：友好的Web控制面板

### 组件说明

1. **云服务器端** (`server.py`)
   - 提供RESTful API接口接收唤醒请求
   - 维护任务队列
   - 提供查询接口供树莓派客户端轮询

2. **树莓派客户端** (`client.py`)
   - 部署在局域网内
   - 定期轮询云服务器获取唤醒任务
   - 发送WOL魔术包唤醒目标计算机
   - **验证设备启动状态并上报结果** 🆕

3. **WOL模块** (`wol.py`)
   - 生成并发送Wake-on-LAN魔术包

4. **设备检测模块** (`device_check.py`) 🆕
   - Ping检测设备是否在线
   - 等待设备启动并记录耗时

## 快速开始

### 环境要求

- Python 3.7+
- Flask (用于云服务器)
- requests (用于树莓派客户端)

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

1. **云服务器配置** (`config/server_config.json`)
   ```json
   {
     "host": "0.0.0.0",
     "port": 5000,
     "api_key": "your-secret-api-key",
     "web_password": "your-web-password",
     "secret_key": "your-secret-key-for-session"
   }
   ```
   
   **配置说明** 🔐：
   - `api_key`: API接口访问密钥
   - `web_password`: Web界面登录密码
   - `secret_key`: Session加密密钥

2. **树莓派客户端配置** (`config/client_config.json`)
   ```json
   {
     "server_url": "http://your-server-ip:5000",
     "api_key": "your-secret-api-key",
     "poll_interval": 10,
     "verify_timeout": 120,
     "devices": {
       "my-pc": {
         "mac": "AA:BB:CC:DD:EE:FF",
         "ip": "192.168.1.100",
         "broadcast": "192.168.1.255"
       }
     }
   }
   ```

   **配置说明**：
   - `verify_timeout`: 等待设备启动的最大时间（秒），默认120秒
   - `ip`: 设备IP地址，用于验证启动是否成功（必须配置才能验证）

### 部署步骤

#### 1. 部署云服务器

```bash
cd RemoteWakeUp
python server.py
```

#### 2. 部署树莓派客户端

```bash
cd RemoteWakeUp
python client.py
```

#### 3. 发送唤醒请求

```bash
# 使用curl发送唤醒请求
curl -X POST http://your-server-ip:5000/api/wake \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key" \
  -d '{"device": "my-pc"}'
```

或访问Web界面: `http://your-server-ip:5000`

**Web界面使用** 🔐：
1. 首次访问会跳转到登录页面
2. 输入Web密码（server_config.json中的web_password）
3. 登录后输入API密钥和设备名称进行唤醒操作
4. 右上角可以登出

## 目标计算机设置

### Windows系统

1. 进入设备管理器 → 网络适配器
2. 右键网卡 → 属性 → 电源管理
3. 勾选"允许此设备唤醒计算机"
4. 勾选"只允许魔术包唤醒计算机"
5. 进入BIOS设置，启用"Wake on LAN"功能

### Linux系统

```bash
# 检查WOL支持
sudo ethtool eth0 | grep Wake-on

# 启用WOL
sudo ethtool -s eth0 wol g
```

## API接口文档

### 1. 发送唤醒请求

- **URL**: `/api/wake`
- **方法**: `POST`
- **认证**: API Key (请求头 `X-API-Key`)
- **请求体**:
  ```json
  {
    "device": "my-pc"
  }
  ```
- **响应**:
  ```json
  {
    "status": "success",
    "message": "Wake-up task created",
    "task_id": "uuid"
  }
  ```

### 2. 查询任务状态

- **URL**: `/api/tasks/<task_id>`
- **方法**: `GET`
- **认证**: API Key
- **响应示例**:
  ```json
  {
    "status": "success",
    "task": {
      "device": "my-pc",
      "status": "completed",
      "result": {
        "success": true,
        "message": "设备 my-pc 已成功启动，用时 45 秒 [✓ 已验证在线，启动用时: 45秒]"
      }
    }
  }
  ```

**启动验证说明** 🆕：
- 如果设备配置了IP地址，系统会自动等待并验证设备是否成功启动
- 验证成功会显示实际启动耗时
- 验证失败会提示设备未响应，可能需要更长时间或启动失败

### 3. 客户端轮询接口

- **URL**: `/api/poll`
- **方法**: `GET`
- **认证**: API Key

## 安全建议

1. 修改默认API密钥
2. 使用HTTPS（配置SSL证书）
3. 限制IP访问（配置防火墙）
4. 定期更换API密钥
5. 启用日志审计

## 故障排查

### 问题1: 无法唤醒计算机

- 检查目标计算机BIOS是否启用WOL
- 检查网卡驱动是否支持WOL
- 确认MAC地址配置正确
- 检查局域网广播地址配置

### 问题2: 显示"已发送唤醒包"但验证失败 🆕

**可能原因**：
- 设备启动时间较长（超过配置的verify_timeout）
- 设备防火墙阻止了Ping请求
- IP地址配置错误或设备使用了DHCP获得不同IP

**解决方法**：
- 增加 `verify_timeout` 值（如改为180秒）
- 在Windows防火墙中允许ICMP回显请求
- 为设备配置静态IP或DHCP保留
- 检查设备当前IP：`ipconfig`（Windows）或 `ip addr`（Linux）

### 问题3: 客户端无法连接服务器

- 检查服务器防火墙配置
- 确认服务器URL和端口正确
- 验证API密钥是否匹配

### 问题3: 树莓派客户端无法发送魔术包

- 检查树莓派网络连接
- 确认树莓派与目标计算机在同一局域网
- 检查Python版本和依赖包

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
