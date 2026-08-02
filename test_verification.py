"""
测试启动验证功能

测试设备检测和唤醒验证是否正常工作
"""

import json
import sys
import time

import requests
from device_check import ping_device, wait_for_device_online


def test_device_check():
    """测试设备检测功能"""
    print("=" * 60)
    print("测试1: 设备检测功能")
    print("=" * 60)
    
    # 加载配置
    try:
        with open('config/client_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("\n错误: 配置文件不存在")
        return False
    
    devices = config.get('devices', {})
    if not devices:
        print("\n错误: 配置文件中没有设备")
        return False
    
    print(f"\n配置的设备:")
    for name, device in devices.items():
        ip = device.get('ip')
        if ip:
            print(f"  - {name}: {ip}")
        else:
            print(f"  - {name}: 未配置IP (无法验证启动)")
    
    # 选择一个有IP的设备进行测试
    test_device = None
    for name, device in devices.items():
        if device.get('ip'):
            test_device = (name, device)
            break
    
    if not test_device:
        print("\n警告: 没有配置IP地址的设备，无法测试启动验证功能")
        print("请在配置文件中为设备添加IP地址")
        return False
    
    device_name, device_info = test_device
    ip = device_info['ip']
    
    print(f"\n使用设备进行测试: {device_name} ({ip})")
    
    # 测试Ping
    print(f"\n测试Ping检测...")
    is_online = ping_device(ip, timeout=2)
    
    if is_online:
        print(f"  ✓ 设备 {ip} 在线（可以响应Ping）")
        print(f"  提示: 这意味着启动验证功能可以正常工作")
    else:
        print(f"  ✗ 设备 {ip} 离线或无法Ping")
        print(f"  可能原因:")
        print(f"    1. 设备已关机（正常情况）")
        print(f"    2. 设备防火墙阻止了Ping")
        print(f"    3. IP地址配置错误")
        
        # 如果设备离线，提供测试建议
        print(f"\n  测试建议:")
        print(f"    1. 确保设备处于开机状态")
        print(f"    2. 在设备上测试: ping {ip}")
        print(f"    3. 检查Windows防火墙是否允许ICMP回显请求")
    
    return True


def test_wake_and_verify():
    """测试完整的唤醒和验证流程"""
    print("\n" + "=" * 60)
    print("测试2: 唤醒和验证流程")
    print("=" * 60)
    
    # 加载配置
    try:
        with open('config/client_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("\n错误: 配置文件不存在")
        return False
    
    server_url = config.get('server_url')
    api_key = config.get('api_key')
    
    print(f"\n服务器: {server_url}")
    
    # 测试服务器连接
    print(f"\n检查服务器连接...")
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        if response.status_code == 200:
            print("  ✓ 服务器连接正常")
        else:
            print(f"  ✗ 服务器响应异常")
            return False
    except Exception as e:
        print(f"  ✗ 无法连接服务器: {e}")
        return False
    
    # 选择设备
    devices = config.get('devices', {})
    device_list = list(devices.keys())
    
    if not device_list:
        print("\n错误: 没有配置设备")
        return False
    
    print(f"\n可用设备:")
    for i, name in enumerate(device_list, 1):
        device = devices[name]
        ip = device.get('ip', '未配置')
        desc = device.get('description', '')
        print(f"  {i}. {name} ({ip}) - {desc}")
    
    # 让用户选择（或自动选择第一个）
    if len(device_list) == 1:
        selected_device = device_list[0]
    else:
        try:
            choice = input(f"\n请选择要测试的设备 (1-{len(device_list)}): ").strip()
            if choice:
                selected_device = device_list[int(choice) - 1]
            else:
                selected_device = device_list[0]
        except:
            selected_device = device_list[0]
    
    print(f"\n选择的设备: {selected_device}")
    
    device_info = devices[selected_device]
    ip = device_info.get('ip')
    
    if not ip:
        print(f"  警告: 此设备未配置IP，无法验证启动")
    
    # 发送唤醒请求
    print(f"\n发送唤醒请求...")
    try:
        response = requests.post(
            f"{server_url}/api/wake",
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': api_key
            },
            json={'device': selected_device},
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            task_id = data.get('task_id')
            print(f"  ✓ 唤醒任务已创建，任务ID: {task_id}")
            
            # 等待一下，让树莓派客户端处理
            print(f"\n等待树莓派客户端处理任务...")
            print(f"  (这可能需要15-150秒，取决于设备启动速度)")
            
            # 轮询任务状态
            for i in range(30):  # 最多等待5分钟
                time.sleep(10)
                
                try:
                    status_response = requests.get(
                        f"{server_url}/api/tasks/{task_id}",
                        headers={'X-API-Key': api_key},
                        timeout=5
                    )
                    
                    if status_response.status_code == 200:
                        task_data = status_response.json().get('task', {})
                        status = task_data.get('status')
                        
                        print(f"  [{i*10}秒] 任务状态: {status}")
                        
                        if status == 'completed':
                            result = task_data.get('result', {})
                            message = result.get('message', '')
                            success = result.get('success', False)
                            
                            print(f"\n✓ 任务完成!")
                            print(f"  结果: {message}")
                            
                            if '已验证在线' in message:
                                print(f"\n恭喜！启动验证功能正常工作！")
                            elif '未响应' in message:
                                print(f"\n设备未在预期时间内响应，可能:")
                                print(f"  - 启动时间较长，需要增加verify_timeout")
                                print(f"  - 防火墙阻止了Ping")
                                print(f"  - IP地址配置错误")
                            
                            return True
                        elif status == 'failed':
                            result = task_data.get('result', {})
                            message = result.get('message', '')
                            print(f"\n✗ 任务失败: {message}")
                            return False
                
                except Exception as e:
                    print(f"  查询状态失败: {e}")
            
            print(f"\n超时：任务可能还在处理中")
            print(f"请检查树莓派客户端日志: tail -f logs/client.log")
            
        else:
            data = response.json()
            print(f"  ✗ 创建任务失败: {data.get('message')}")
            return False
            
    except Exception as e:
        print(f"  ✗ 请求失败: {e}")
        return False
    
    return True


def main():
    """主函数"""
    print("\n启动验证功能测试工具\n")
    
    # 测试1: 设备检测
    if not test_device_check():
        print("\n设备检测测试失败")
        return False
    
    # 询问是否进行完整测试
    print("\n" + "=" * 60)
    response = input("\n是否进行完整的唤醒测试？(y/n): ").strip().lower()
    
    if response == 'y':
        if not test_wake_and_verify():
            print("\n唤醒测试失败")
            return False
    else:
        print("\n跳过唤醒测试")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
