"""
测试脚本 - 用于测试WOL功能和系统连接
"""

import json
import sys
import time

import requests

from wol import WOLSender


def test_wol_module():
    """测试WOL模块"""
    print("\n" + "="*50)
    print("测试1: WOL模块")
    print("="*50)
    
    sender = WOLSender()
    
    # 测试MAC地址验证
    test_cases = [
        ("AA:BB:CC:DD:EE:FF", True),
        ("AA-BB-CC-DD-EE-FF", True),
        ("AABBCCDDEEFF", True),
        ("AA:BB:CC:DD:EE", False),
        ("ZZ:BB:CC:DD:EE:FF", False),
    ]
    
    print("\nMAC地址验证测试:")
    for mac, expected in test_cases:
        result = sender.validate_mac_address(mac)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {mac}: {result}")
    
    # 测试魔术包创建
    print("\n魔术包创建测试:")
    try:
        packet = sender.create_magic_packet("AA:BB:CC:DD:EE:FF")
        print(f"  ✓ 魔术包长度: {len(packet)} 字节")
        print(f"  ✓ 预期长度: 102 字节")
        if len(packet) == 102:
            print("  ✓ 魔术包格式正确")
        else:
            print("  ✗ 魔术包格式错误")
    except Exception as e:
        print(f"  ✗ 错误: {str(e)}")


def test_server_connection(server_url, api_key):
    """测试服务器连接"""
    print("\n" + "="*50)
    print("测试2: 服务器连接")
    print("="*50)
    
    print(f"\n服务器地址: {server_url}")
    
    # 测试健康检查
    print("\n健康检查:")
    try:
        response = requests.get(f"{server_url}/health", timeout=10)
        if response.status_code == 200:
            print(f"  ✓ 服务器正常运行")
            data = response.json()
            print(f"  ✓ 时间戳: {data.get('timestamp')}")
        else:
            print(f"  ✗ 服务器响应异常: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"  ✗ 无法连接到服务器")
        print(f"  提示: 请检查服务器是否启动，地址是否正确")
        return False
    except Exception as e:
        print(f"  ✗ 错误: {str(e)}")
        return False
    
    # 测试API认证
    print("\nAPI认证测试:")
    try:
        headers = {'X-API-Key': api_key}
        response = requests.get(
            f"{server_url}/api/stats",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            print(f"  ✓ API密钥有效")
            data = response.json()
            stats = data.get('stats', {})
            print(f"  ✓ 任务统计: 总计{stats.get('total_tasks', 0)}个")
        elif response.status_code == 401:
            print(f"  ✗ 未提供API密钥")
            return False
        elif response.status_code == 403:
            print(f"  ✗ API密钥无效")
            print(f"  提示: 请检查配置文件中的API密钥是否与服务器一致")
            return False
        else:
            print(f"  ✗ 服务器响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ 错误: {str(e)}")
        return False
    
    return True


def test_wake_request(server_url, api_key, device):
    """测试唤醒请求"""
    print("\n" + "="*50)
    print("测试3: 发送唤醒请求")
    print("="*50)
    
    print(f"\n目标设备: {device}")
    
    try:
        headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
        data = {'device': device}
        
        response = requests.post(
            f"{server_url}/api/wake",
            headers=headers,
            json=data,
            timeout=10
        )
        
        result = response.json()
        
        if response.status_code == 201:
            print(f"  ✓ 唤醒任务已创建")
            print(f"  ✓ 任务ID: {result.get('task_id')}")
            return result.get('task_id')
        else:
            print(f"  ✗ 创建任务失败: {result.get('message')}")
            return None
    except Exception as e:
        print(f"  ✗ 错误: {str(e)}")
        return None


def test_task_status(server_url, api_key, task_id):
    """测试任务状态查询"""
    print("\n" + "="*50)
    print("测试4: 查询任务状态")
    print("="*50)
    
    print(f"\n任务ID: {task_id}")
    
    try:
        headers = {'X-API-Key': api_key}
        response = requests.get(
            f"{server_url}/api/tasks/{task_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            task = result.get('task', {})
            print(f"  ✓ 任务查询成功")
            print(f"  ✓ 设备: {task.get('device')}")
            print(f"  ✓ 状态: {task.get('status')}")
            print(f"  ✓ 创建时间: {task.get('created_at')}")
            if task.get('completed_at'):
                print(f"  ✓ 完成时间: {task.get('completed_at')}")
            if task.get('client_id'):
                print(f"  ✓ 处理客户端: {task.get('client_id')}")
            return True
        else:
            print(f"  ✗ 查询失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ 错误: {str(e)}")
        return False


def main():
    """主函数"""
    print("\n" + "="*50)
    print("远程唤醒系统 - 测试工具")
    print("="*50)
    
    # 加载配置
    try:
        with open('config/client_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("\n错误: 配置文件不存在")
        print("请先创建 config/client_config.json")
        sys.exit(1)
    except json.JSONDecodeError:
        print("\n错误: 配置文件格式错误")
        sys.exit(1)
    
    server_url = config.get('server_url')
    api_key = config.get('api_key')
    devices = config.get('devices', {})
    
    if not server_url or not api_key:
        print("\n错误: 配置文件缺少必需字段")
        sys.exit(1)
    
    # 测试WOL模块
    test_wol_module()
    
    # 测试服务器连接
    if not test_server_connection(server_url, api_key):
        print("\n测试终止: 服务器连接失败")
        sys.exit(1)
    
    # 选择设备
    if not devices:
        print("\n错误: 配置文件中没有设备")
        sys.exit(1)
    
    print("\n可用设备:")
    device_list = list(devices.keys())
    for i, device_name in enumerate(device_list, 1):
        device = devices[device_name]
        print(f"  {i}. {device_name} - {device.get('description', '')}")
    
    if len(device_list) == 1:
        selected_device = device_list[0]
        print(f"\n自动选择唯一设备: {selected_device}")
    else:
        try:
            choice = input(f"\n请选择设备 (1-{len(device_list)}): ")
            selected_device = device_list[int(choice) - 1]
        except (ValueError, IndexError):
            print("无效的选择")
            sys.exit(1)
    
    # 测试唤醒请求
    task_id = test_wake_request(server_url, api_key, selected_device)
    
    if task_id:
        # 等待任务处理
        print("\n等待客户端处理任务...")
        for i in range(5):
            time.sleep(2)
            print(f"  等待中... ({i+1}/5)")
            test_task_status(server_url, api_key, task_id)
    
    print("\n" + "="*50)
    print("测试完成")
    print("="*50)
    print("\n提示:")
    print("  - 如果任务状态仍为 'pending'，请检查客户端是否运行")
    print("  - 如果任务状态为 'completed'，说明系统运行正常")
    print("  - 如果目标计算机未启动，请检查WOL配置")
    print("")


if __name__ == '__main__':
    main()
