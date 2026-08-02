"""
完整流程演示脚本

展示从发送唤醒请求到获取反馈的完整流程
"""

import json
import time
import requests


def demo_complete_flow():
    """演示完整的唤醒流程"""
    
    # 加载配置
    with open('config/server_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    server_url = f"http://{config['host']}:{config['port']}"
    if config['host'] == '0.0.0.0':
        server_url = f"http://127.0.0.1:{config['port']}"
    
    api_key = config['api_key']
    
    print("=" * 70)
    print("远程唤醒系统 - 完整流程演示")
    print("=" * 70)
    print()
    
    # 步骤1: 发送唤醒请求
    print("步骤1: 发送唤醒请求")
    print("-" * 70)
    device_name = "my-pc"
    
    try:
        response = requests.post(
            f"{server_url}/api/wake",
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': api_key
            },
            json={'device': device_name},
            timeout=5
        )
        
        if response.status_code == 201:
            data = response.json()
            task_id = data['task_id']
            print(f"✓ 唤醒任务已创建")
            print(f"  设备名: {device_name}")
            print(f"  任务ID: {task_id}")
            print(f"  状态: pending (等待客户端处理)")
        else:
            print(f"✗ 创建任务失败: {response.status_code}")
            print(f"  {response.text}")
            return
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return
    
    print()
    
    # 步骤2: 等待客户端处理
    print("步骤2: 等待客户端处理任务")
    print("-" * 70)
    print("客户端会:")
    print("  1. 轮询服务器获取任务 (每5秒)")
    print("  2. 发送WOL魔术包 (3次)")
    print("  3. 验证设备启动 (Ping检测)")
    print("  4. 上报结果给服务器")
    print()
    print("等待中", end="", flush=True)
    
    # 轮询任务状态
    max_wait = 15  # 最多等待15秒
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        time.sleep(1)
        print(".", end="", flush=True)
        
        try:
            response = requests.get(
                f"{server_url}/api/tasks/{task_id}",
                headers={'X-API-Key': api_key},
                timeout=5
            )
            
            if response.status_code == 200:
                task_data = response.json()['task']
                
                if task_data['status'] == 'completed':
                    print(" ✓")
                    print()
                    
                    # 步骤3: 显示反馈结果
                    print("步骤3: 获取反馈结果")
                    print("-" * 70)
                    
                    result = task_data.get('result', {})
                    success = result.get('success', False)
                    message = result.get('message', '')
                    
                    if success:
                        print(f"✓ 唤醒成功！")
                    else:
                        print(f"✗ 唤醒失败")
                    
                    print(f"\n反馈消息:")
                    print(f"  {message}")
                    
                    print(f"\n任务详情:")
                    print(f"  任务ID: {task_data['task_id']}")
                    print(f"  设备: {task_data['device']}")
                    print(f"  状态: {task_data['status']}")
                    print(f"  创建时间: {task_data['created_at']}")
                    print(f"  完成时间: {task_data['completed_at']}")
                    print(f"  客户端ID: {task_data.get('client_id', 'N/A')}")
                    
                    # 显示验证信息
                    if 'verification' in result:
                        verification = result['verification']
                        print(f"\n启动验证信息:")
                        print(f"  WOL包已发送: {'是' if verification.get('wol_sent') else '否'}")
                        print(f"  已进行验证: {'是' if verification.get('verified') else '否'}")
                        print(f"  设备在线: {'是' if verification.get('online') else '否'}")
                        
                        if verification.get('boot_time') is not None:
                            print(f"  启动耗时: {verification['boot_time']}秒")
                    
                    break
                elif task_data['status'] == 'failed':
                    print(" ✗")
                    print()
                    print("步骤3: 任务处理失败")
                    print("-" * 70)
                    print(f"错误: {task_data.get('result', {}).get('message', '未知错误')}")
                    break
        
        except Exception as e:
            pass
    else:
        print(" ⏱")
        print()
        print("步骤3: 等待超时")
        print("-" * 70)
        print("客户端可能未运行或处理较慢")
        print("您可以稍后使用以下命令查询任务状态:")
        print(f"  curl -H 'X-API-Key: {api_key}' {server_url}/api/tasks/{task_id}")
    
    print()
    print("=" * 70)
    print("演示完成！")
    print("=" * 70)
    print()
    print("提示:")
    print("• 在Web界面上操作会看到相同的流程")
    print("• Web界面会自动轮询任务状态并显示反馈")
    print("• 客户端日志: logs/client.log")
    print("• 服务器日志: logs/server.log")
    print()


if __name__ == '__main__':
    try:
        demo_complete_flow()
    except KeyboardInterrupt:
        print("\n\n演示已取消")
    except Exception as e:
        print(f"\n\n错误: {e}")
