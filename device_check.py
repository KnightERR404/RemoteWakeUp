"""
简单的设备在线检测模块

用于检测设备是否成功启动
"""

import platform
import subprocess
import logging
import time


def ping_device(ip_address, timeout=2, count=1):
    """
    Ping设备检测是否在线
    
    Args:
        ip_address: 设备IP地址
        timeout: 超时时间（秒）
        count: ping次数
        
    Returns:
        bool: 设备在线返回True，否则返回False
    """
    try:
        system = platform.system()
        
        # 根据操作系统设置ping命令参数
        if system == "Windows":
            cmd = ['ping', '-n', str(count), '-w', str(timeout * 1000), ip_address]
        else:
            # Linux/Mac
            cmd = ['ping', '-c', str(count), '-W', str(timeout), ip_address]
        
        # 执行ping命令，不显示输出
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout + 1
        )
        
        return result.returncode == 0
        
    except Exception:
        return False


def wait_for_device_online(ip_address, max_wait_seconds=120, check_interval=5):
    """
    等待设备上线
    
    Args:
        ip_address: 设备IP地址
        max_wait_seconds: 最大等待时间（秒）
        check_interval: 检查间隔（秒）
        
    Returns:
        tuple: (is_online, elapsed_time)
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait_seconds:
        if ping_device(ip_address, timeout=2):
            elapsed = int(time.time() - start_time)
            return True, elapsed
        
        time.sleep(check_interval)
    
    elapsed = int(time.time() - start_time)
    return False, elapsed
