"""
测试Web界面密码保护功能

验证Web登录和session管理是否正常工作
"""

import json
import sys
import requests
from requests.cookies import RequestsCookieJar


def test_web_authentication():
    """测试Web认证功能"""
    print("=" * 60)
    print("测试Web界面密码保护功能")
    print("=" * 60)
    
    # 加载配置
    try:
        with open('config/server_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("\n错误: 配置文件不存在")
        return False
    
    server_url = f"http://{config.get('host', 'localhost')}:{config.get('port', 5000)}"
    web_password = config.get('web_password', '')
    
    if config.get('host') == '0.0.0.0':
        server_url = f"http://localhost:{config.get('port', 5000)}"
    
    print(f"\n服务器地址: {server_url}")
    print(f"Web密码: {'已配置' if web_password else '未配置'}")
    
    # 创建session
    session = requests.Session()
    
    # 测试1: 未登录访问首页应该重定向到登录页
    print("\n[测试1] 未登录访问首页...")
    try:
        response = session.get(server_url, allow_redirects=False)
        
        if response.status_code in [302, 303, 307, 308]:
            print("  ✓ 正确重定向到登录页面")
            if '/login' in response.headers.get('Location', ''):
                print("  ✓ 重定向到 /login 路径")
            else:
                print(f"  ✗ 重定向到: {response.headers.get('Location')}")
        else:
            print(f"  ✗ 未重定向，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ 请求失败: {e}")
        print(f"  提示: 请确保服务器正在运行: python server.py")
        return False
    
    # 测试2: 访问登录页面
    print("\n[测试2] 访问登录页面...")
    try:
        response = session.get(f"{server_url}/login")
        
        if response.status_code == 200:
            print("  ✓ 登录页面可访问")
            if '密码' in response.text and 'password' in response.text:
                print("  ✓ 登录页面包含密码输入框")
            else:
                print("  ✗ 登录页面格式异常")
        else:
            print(f"  ✗ 登录页面访问失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ 请求失败: {e}")
        return False
    
    # 测试3: 使用错误密码登录
    print("\n[测试3] 使用错误密码登录...")
    try:
        response = session.post(
            f"{server_url}/login",
            data={'password': 'wrong-password'},
            allow_redirects=False
        )
        
        if response.status_code == 200:
            if '密码错误' in response.text or '错误' in response.text:
                print("  ✓ 正确拒绝错误密码")
            else:
                print("  ✗ 未显示错误信息")
        elif response.status_code in [302, 303]:
            print("  ✗ 错误：错误密码也能登录")
            return False
        else:
            print(f"  ✗ 意外的状态码: {response.status_code}")
    except Exception as e:
        print(f"  ✗ 请求失败: {e}")
        return False
    
    # 测试4: 使用正确密码登录
    print("\n[测试4] 使用正确密码登录...")
    if not web_password:
        print("  ⚠ 跳过: 未配置Web密码")
    else:
        try:
            response = session.post(
                f"{server_url}/login",
                data={'password': web_password},
                allow_redirects=False
            )
            
            if response.status_code in [302, 303]:
                print("  ✓ 登录成功，重定向到首页")
                
                # 检查是否设置了cookie
                if session.cookies:
                    print("  ✓ Session cookie已设置")
                else:
                    print("  ✗ 未设置session cookie")
                    return False
            else:
                print(f"  ✗ 登录失败，状态码: {response.status_code}")
                print(f"  响应内容: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"  ✗ 请求失败: {e}")
            return False
        
        # 测试5: 已登录状态访问首页
        print("\n[测试5] 已登录状态访问首页...")
        try:
            response = session.get(server_url)
            
            if response.status_code == 200:
                print("  ✓ 成功访问首页")
                if '远程唤醒系统' in response.text:
                    print("  ✓ 页面内容正确")
                if '登出' in response.text:
                    print("  ✓ 显示登出链接")
            else:
                print(f"  ✗ 访问失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ 请求失败: {e}")
            return False
        
        # 测试6: 登出
        print("\n[测试6] 测试登出功能...")
        try:
            response = session.get(f"{server_url}/logout", allow_redirects=False)
            
            if response.status_code in [302, 303]:
                print("  ✓ 登出成功，重定向到登录页")
            else:
                print(f"  ✗ 登出失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ 请求失败: {e}")
            return False
        
        # 测试7: 登出后访问首页应该重定向
        print("\n[测试7] 登出后访问首页...")
        try:
            response = session.get(server_url, allow_redirects=False)
            
            if response.status_code in [302, 303]:
                print("  ✓ 正确重定向到登录页")
            else:
                print(f"  ✗ 未重定向，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ 请求失败: {e}")
            return False
    
    print("\n" + "=" * 60)
    print("所有测试通过！Web密码保护功能正常工作。")
    print("=" * 60)
    
    return True


def main():
    """主函数"""
    print("\nWeb认证功能测试工具\n")
    
    success = test_web_authentication()
    
    if success:
        print("\n✓ 测试完成，系统工作正常")
        return 0
    else:
        print("\n✗ 测试失败，请检查配置和服务器状态")
        return 1


if __name__ == '__main__':
    sys.exit(main())
