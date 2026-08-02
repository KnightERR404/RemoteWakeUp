"""
远程唤醒系统 - 树莓派客户端

定期轮询云服务器获取唤醒任务，并发送WOL魔术包唤醒局域网内的目标计算机
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime

import requests

from wol import WOLSender
from device_check import ping_device, wait_for_device_online


class RemoteWakeUpClient:
    """远程唤醒客户端"""
    
    def __init__(self, config_path='config/client_config.json'):
        """
        初始化客户端
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self.load_config(config_path)
        self.logger = self.setup_logging()
        self.wol_sender = WOLSender(self.logger)
        self.client_id = str(uuid.uuid4())
        self.running = False
        
        self.logger.info(f"客户端初始化完成: client_id={self.client_id}")
    
    def load_config(self, config_path):
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 验证必需的配置项
            required_fields = ['server_url', 'api_key', 'devices']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"配置文件缺少必需字段: {field}")
            
            return config
            
        except FileNotFoundError:
            print(f"错误: 配置文件不存在: {config_path}")
            raise
        except json.JSONDecodeError as e:
            print(f"错误: 配置文件格式错误: {e}")
            raise
    
    def setup_logging(self):
        """设置日志系统"""
        log_file = self.config.get('log_file', 'logs/client.log')
        
        # 创建日志目录
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 配置日志
        logger = logging.getLogger('RemoteWakeUpClient')
        logger.setLevel(logging.INFO)
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def poll_server(self):
        """轮询服务器获取待处理任务"""
        try:
            url = f"{self.config['server_url']}/api/poll"
            headers = {
                'X-API-Key': self.config['api_key']
            }
            params = {
                'client_id': self.client_id
            }
            
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('tasks', [])
            elif response.status_code == 401:
                self.logger.error("认证失败: API密钥无效")
                return []
            elif response.status_code == 403:
                self.logger.error("权限被拒绝: 请检查API密钥")
                return []
            else:
                self.logger.warning(
                    f"轮询服务器失败: status={response.status_code}"
                )
                return []
                
        except requests.exceptions.ConnectionError:
            self.logger.error("无法连接到服务器")
            return []
        except requests.exceptions.Timeout:
            self.logger.warning("服务器请求超时")
            return []
        except Exception as e:
            self.logger.error(f"轮询服务器异常: {str(e)}")
            return []
    
    def report_result(self, task_id, success, message):
        """向服务器上报任务执行结果"""
        try:
            url = f"{self.config['server_url']}/api/report"
            headers = {
                'X-API-Key': self.config['api_key'],
                'Content-Type': 'application/json'
            }
            data = {
                'task_id': task_id,
                'success': success,
                'message': message,
                'client_id': self.client_id
            }
            
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.debug(f"任务结果上报成功: task_id={task_id}")
                return True
            else:
                self.logger.warning(
                    f"任务结果上报失败: task_id={task_id}, "
                    f"status={response.status_code}"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"上报任务结果异常: {str(e)}")
            return False
    
    def wake_device(self, device_name):
        """并验证启动状态
        
        Args:
            device_name: 设备名称
            
        Returns:
            tuple: (success, message, verification_result)
        """
        devices = self.config.get('devices', {})
        
        if device_name not in devices:
            message = f"未知的设备: {device_name}"
            self.logger.warning(message)
            return False, message, None
        
        device = devices[device_name]
        mac = device.get('mac')
        ip = device.get('ip')
        broadcast = device.get('broadcast', '255.255.255.255')
        port = device.get('port', 9)
        
        if not mac:
            message = f"设备配置缺少MAC地址: {device_name}"
            self.logger.error(message)
            return False, message, None
        
        self.logger.info(
            f"正在唤醒设备: {device_name} "
            f"(MAC={mac}, 广播={broadcast}:{port})"
        )
        
        # 发送WOL魔术包（发送3次以提高可靠性）
        wol_success = self.wol_sender.wake(
            mac_address=mac,
            broadcast=broadcast,
            port=port,
            count=3
        )
        
        if not wol_success:
            message = f"发送唤醒包失败: {device_name}"
            self.logger.error(message)
            return False, message, None
        
        self.logger.info(f"唤醒包已发送到设备: {device_name}")
        
        # 如果配置了IP地址，等待设备上线并验证
        verification_result = {
            'wol_sent': True,
            'verified': False,
            'online': False,
            'boot_time': None
        }
        
        if ip:
            self.logger.info(f"等待设备 {device_name} ({ip}) 启动...")
            
            # 获取等待时间配置（默认120秒）
            wait_time = self.config.get('verify_timeout', 120)
            
            # 等待设备上线
            is_online, elapsed = wait_for_device_online(ip, max_wait_seconds=wait_time)
            
            verification_result['verified'] = True
            verification_result['online'] = is_online
            verification_result['boot_time'] = elapsed
            
            if is_online:
                message = f"设备 {device_name} 已成功启动，用时 {elapsed} 秒"
                self.logger.info(message)
                return True, message, verification_result
            else:
                message = f"设备 {device_name} 在 {wait_time} 秒内未响应，可能启动失败或需要更长时间"
                self.logger.warning(message)
                return False, message, verification_result
        else:
            # 没有配置IP，无法验证，只返回WOL发送成功
            message = f"唤醒包已发送到设备 {device_name}（未配置IP，无法验证启动）"
            self.logger.info(message)
            return True, message, verification_result
        return success, message
    
    def process_task(self, task):
        """
        处理单个任务（包含启动验证）
        
        Args:
            task: 任务字典，包含task_id和device
        """
        task_id = task['task_id']
        device = task['device']
        
        self.logger.info(f"开始处理任务: task_id={task_id}, device={device}")
        
        # 执行唤醒操作并验证
        success, message, verification = self.wake_device(device)
        
        # 准备上报数据
        result_message = message
        if verification and verification['verified']:
            if verification['online']:
                result_message += f" [✓ 已验证在线，启动用时: {verification['boot_time']}秒]"
            else:
                result_message += " [✗ 验证失败：设备未响应]"
        
        # 上报结果
        self.report_result(task_id, success, result_message)
        
        self.logger.info(
            f"任务处理完成: task_id={task_id}, success={success}"
        )
    
    def run(self):
        """运行客户端主循环"""
        self.running = True
        poll_interval = self.config.get('poll_interval', 10)
        
        self.logger.info("=" * 50)
        self.logger.info("远程唤醒客户端启动")
        self.logger.info(f"服务器地址: {self.config['server_url']}")
        self.logger.info(f"轮询间隔: {poll_interval}秒")
        self.logger.info(f"已配置设备数: {len(self.config.get('devices', {}))}")
        self.logger.info("=" * 50)
        
        # 显示已配置的设备
        for device_name, device_info in self.config.get('devices', {}).items():
            self.logger.info(
                f"设备: {device_name} - {device_info.get('description', '')} "
                f"(MAC: {device_info.get('mac', 'N/A')})"
            )
        
        last_poll_time = 0
        
        try:
            while self.running:
                current_time = time.time()
                
                # 检查是否到达轮询时间
                if current_time - last_poll_time >= poll_interval:
                    # 轮询服务器
                    tasks = self.poll_server()
                    
                    if tasks:
                        self.logger.info(f"获取到 {len(tasks)} 个待处理任务")
                        
                        # 处理每个任务
                        for task in tasks:
                            self.process_task(task)
                    
                    last_poll_time = current_time
                
                # 短暂休眠以降低CPU使用率
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("收到中断信号，正在停止客户端...")
            self.running = False
        except Exception as e:
            self.logger.error(f"客户端运行异常: {str(e)}", exc_info=True)
            self.running = False
        
        self.logger.info("客户端已停止")
    
    def stop(self):
        """停止客户端"""
        self.running = False


def main():
    """主函数"""
    import sys
    
    # 检查配置文件
    config_path = 'config/client_config.json'
    if not os.path.exists(config_path):
        print(f"错误: 配置文件不存在: {config_path}")
        print("请先创建配置文件并填写服务器地址、API密钥和设备信息")
        sys.exit(1)
    
    # 创建并运行客户端
    try:
        client = RemoteWakeUpClient(config_path)
        client.run()
    except KeyboardInterrupt:
        print("\n程序已终止")
        sys.exit(0)
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
