# Web密码保护功能说明

## 更新内容

为远程唤醒系统添加了Web界面密码保护功能，提升系统安全性。

## 功能特性

### 🔐 安全改进

- **登录验证**: Web界面现在需要密码才能访问
- **Session管理**: 使用Flask session进行用户状态管理
- **自动重定向**: 未登录访问自动跳转到登录页面
- **登出功能**: 提供安全登出机制

### 📋 新增组件

1. **登录页面** (`/login`)
   - 美观的登录界面
   - 密码输入保护
   - 错误提示

2. **登录验证装饰器** (`@require_web_login`)
   - 自动验证登录状态
   - 保护所有需要认证的页面

3. **登出功能** (`/logout`)
   - 清除session
   - 返回登录页面

## 配置说明

### 服务器配置文件

在 `config/server_config.json` 中添加了两个新字段：

```json
{
  "host": "0.0.0.0",
  "port": 5000,
  "api_key": "your-api-key",
  "web_password": "your-web-password",     // 新增：Web界面登录密码
  "secret_key": "your-secret-key",         // 新增：Session加密密钥
  "debug": false,
  "log_file": "logs/server.log",
  "task_retention_seconds": 3600
}
```

### 配置项说明

- **web_password**: 
  - 用途：Web界面登录密码
  - 建议：8位以上强密码
  - 示例：`MyStr0ng!Pass2026`

- **secret_key**: 
  - 用途：Flask session加密密钥
  - 建议：32位以上随机字符串
  - 生成：`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

## 使用方法

### 首次访问

1. 打开浏览器，访问: `http://你的服务器IP:5000`
2. 系统自动跳转到登录页面
3. 输入在配置文件中设置的Web密码
4. 点击"登录"按钮

### 唤醒设备

登录后：
1. 输入API密钥（用于API调用认证）
2. 输入设备名称
3. 点击"唤醒设备"按钮
4. 查看结果反馈

### 登出

点击页面右上角的"登出"链接安全退出。

## 部署更新

### 自动部署

使用更新后的部署脚本 `deploy_server.sh`：

```bash
sudo bash deploy_server.sh
```

脚本会：
1. 自动生成API密钥
2. 提示设置Web密码
3. 自动生成Secret密钥
4. 创建配置文件
5. 启动服务

### 手动配置

1. **编辑配置文件**
   ```bash
   nano config/server_config.json
   ```

2. **添加新字段**
   ```json
   {
     "web_password": "your-password-here",
     "secret_key": "your-secret-key-here"
   }
   ```

3. **生成Secret密钥**
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

4. **重启服务**
   ```bash
   sudo systemctl restart wol-server
   ```

## 安全建议

### 密码强度

✅ **推荐做法**：
- 使用至少8位密码
- 包含大小写字母、数字和特殊字符
- 不要使用常见密码
- 定期更换密码

❌ **避免使用**：
- 简单密码：`123456`, `password`, `admin`
- 个人信息：生日、姓名等
- 字典单词

### Secret Key

✅ **推荐做法**：
- 使用32位以上随机字符串
- 使用 `secrets.token_urlsafe()` 生成
- 保持密钥机密性
- 定期更换

❌ **避免使用**：
- 默认值：`change-this-secret-key`
- 简单字符串：`mysecret123`
- 与其他密钥相同

### 其他建议

1. **启用HTTPS**: 在生产环境使用SSL/TLS加密
2. **限制IP访问**: 通过防火墙限制访问源
3. **定期审计**: 检查服务器日志
4. **备份配置**: 定期备份配置文件

## 测试验证

### 运行测试脚本

```bash
python3 test_web_auth.py
```

测试内容：
- ✅ 未登录访问重定向
- ✅ 登录页面可访问
- ✅ 错误密码被拒绝
- ✅ 正确密码可登录
- ✅ Session正常工作
- ✅ 登出功能正常
- ✅ 登出后需要重新登录

### 手动测试

1. **测试未登录访问**
   - 清除浏览器cookie
   - 访问首页
   - 应该自动跳转到登录页

2. **测试登录**
   - 输入错误密码 → 应该显示错误
   - 输入正确密码 → 应该进入首页

3. **测试登出**
   - 点击登出链接
   - 应该返回登录页
   - 再次访问首页应该需要登录

## 故障排查

### 问题1：登录后立即跳回登录页

**原因**：Secret key未设置或配置错误

**解决**：
```bash
# 生成新的secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 更新配置文件
nano config/server_config.json

# 重启服务
sudo systemctl restart wol-server
```

### 问题2：Session过期太快

**原因**：浏览器cookie设置或服务器重启

**解决**：
- 配置永久session（修改代码）
- 或者重新登录

### 问题3：忘记Web密码

**解决**：
```bash
# 编辑配置文件
nano config/server_config.json

# 修改web_password字段
# 重启服务
sudo systemctl restart wol-server
```

### 问题4：API密钥和Web密码混淆

**说明**：
- **Web密码**：登录Web界面使用
- **API密钥**：调用API接口使用（在Web界面中输入）
- 这是两个不同的认证机制

## 向后兼容性

### 旧版本升级

如果从旧版本升级，需要：

1. **更新配置文件**
   ```bash
   # 备份旧配置
   cp config/server_config.json config/server_config.json.bak
   
   # 添加新字段
   nano config/server_config.json
   ```

2. **添加必需字段**
   ```json
   {
     "web_password": "设置密码",
     "secret_key": "生成密钥"
   }
   ```

3. **重启服务**
   ```bash
   sudo systemctl restart wol-server
   ```

### API兼容性

API接口保持不变：
- ✅ 所有API端点正常工作
- ✅ API密钥认证不受影响
- ✅ 客户端无需修改

## 更新日志

### v1.1 (2026-02-28)

**新增功能**：
- ✨ Web界面密码保护
- ✨ 登录/登出功能
- ✨ Session管理
- ✨ 登录页面UI

**配置变更**：
- ➕ 新增 `web_password` 配置项
- ➕ 新增 `secret_key` 配置项

**部署脚本**：
- 🔄 更新 `deploy_server.sh`
- ➕ 新增 `test_web_auth.py` 测试脚本

**文档更新**：
- 📖 更新部署与使用手册
- 📖 更新README.md
- 📖 更新QUICKSTART.md

## 未来计划

待开发功能：
- [ ] 多用户支持
- [ ] 角色权限管理
- [ ] 登录失败次数限制
- [ ] 两步验证（2FA）
- [ ] OAuth集成
- [ ] 记住登录状态

## 技术细节

### Session实现

使用Flask的session机制：
- 存储在客户端cookie中
- 使用secret_key加密
- 服务器验证签名

### 安全特性

- 密码不存储在cookie中
- Secret key加密session
- 自动CSRF保护（Flask内置）
- 登出清除session

### 装饰器实现

```python
def require_web_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
```

## 参考资料

- Flask Session文档: https://flask.palletsprojects.com/en/3.0.x/api/#sessions
- Python secrets模块: https://docs.python.org/3/library/secrets.html
- OWASP密码指南: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html

---

**更新时间**: 2026-02-28  
**版本**: v1.1  
**作者**: Remote WakeUp Project
