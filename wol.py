"""
Wake-on-LAN 魔术包发送模块

该模块用于生成和发送WOL魔术包来唤醒网络中的计算机
"""

import socket
import struct
import re
import logging


class WOLSender:
    """Wake-on-LAN魔术包发送器"""
    
    def __init__(self, logger=None):
        """
        初始化WOL发送器
        
        Args:
            logger: 日志记录器实例，如果为None则创建默认日志记录器
        """
        self.logger = logger or self._setup_logger()
    
    def _setup_logger(self):
        """设置默认日志记录器"""
        logger = logging.getLogger('WOL')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    def validate_mac_address(self, mac):
        """
        验证MAC地址格式
        
        Args:
            mac: MAC地址字符串
            
        Returns:
            bool: 如果MAC地址格式有效返回True，否则返回False
        """
        # 支持的格式: AA:BB:CC:DD:EE:FF, AA-BB-CC-DD-EE-FF, AABBCCDDEEFF
        pattern = r'^([0-9A-Fa-f]{2}[:-]?){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(pattern, mac))
    
    def normalize_mac_address(self, mac):
        """
        标准化MAC地址为字节序列
        
        Args:
            mac: MAC地址字符串
            
        Returns:
            bytes: 6字节的MAC地址
            
        Raises:
            ValueError: 如果MAC地址格式无效
        """
        if not self.validate_mac_address(mac):
            raise ValueError(f"无效的MAC地址格式: {mac}")
        
        # 移除所有分隔符
        mac = mac.replace(':', '').replace('-', '').upper()
        
        # 转换为字节
        return bytes.fromhex(mac)
    
    def create_magic_packet(self, mac_address):
        """
        创建WOL魔术包
        
        魔术包格式：
        - 6字节的0xFF（同步流）
        - 16次重复的目标MAC地址（6字节 × 16 = 96字节）
        总共102字节
        
        Args:
            mac_address: 目标计算机的MAC地址
            
        Returns:
            bytes: WOL魔术包数据
        """
        mac_bytes = self.normalize_mac_address(mac_address)
        
        # 创建魔术包: 6个0xFF + 16次MAC地址
        magic_packet = b'\xFF' * 6 + mac_bytes * 16
        
        self.logger.debug(
            f"创建魔术包: 长度={len(magic_packet)}字节, "
            f"MAC={mac_address}"
        )
        
        return magic_packet
    
    def send_magic_packet(self, mac_address, broadcast='255.255.255.255', port=9):
        """
        发送WOL魔术包
        
        Args:
            mac_address: 目标计算机的MAC地址
            broadcast: 广播地址，默认为全网广播255.255.255.255
            port: 目标UDP端口，通常为7或9
            
        Returns:
            bool: 发送成功返回True，失败返回False
        """
        try:
            # 创建魔术包
            magic_packet = self.create_magic_packet(mac_address)
            
            # 创建UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # 发送魔术包
            sock.sendto(magic_packet, (broadcast, port))
            sock.close()
            
            self.logger.info(
                f"成功发送WOL魔术包: MAC={mac_address}, "
                f"广播地址={broadcast}:{port}"
            )
            return True
            
        except Exception as e:
            self.logger.error(
                f"发送WOL魔术包失败: MAC={mac_address}, "
                f"错误={str(e)}"
            )
            return False
    
    def wake(self, mac_address, broadcast='255.255.255.255', port=9, count=1):
        """
        唤醒目标计算机（支持多次发送以提高可靠性）
        
        Args:
            mac_address: 目标计算机的MAC地址
            broadcast: 广播地址
            port: UDP端口
            count: 发送次数，默认为1
            
        Returns:
            bool: 所有发送都成功返回True，否则返回False
        """
        success_count = 0
        
        for i in range(count):
            if self.send_magic_packet(mac_address, broadcast, port):
                success_count += 1
            
            # 如果需要多次发送，稍微延迟
            if count > 1 and i < count - 1:
                import time
                time.sleep(0.1)
        
        if success_count == count:
            self.logger.info(
                f"唤醒操作完成: MAC={mac_address}, "
                f"成功发送{success_count}/{count}次"
            )
            return True
        else:
            self.logger.warning(
                f"唤醒操作部分失败: MAC={mac_address}, "
                f"成功发送{success_count}/{count}次"
            )
            return False


def wake_on_lan(mac_address, broadcast='255.255.255.255', port=9):
    """
    便捷函数：发送WOL魔术包唤醒计算机
    
    Args:
        mac_address: 目标计算机的MAC地址
        broadcast: 广播地址
        port: UDP端口
        
    Returns:
        bool: 发送成功返回True，失败返回False
    """
    sender = WOLSender()
    return sender.wake(mac_address, broadcast, port)


if __name__ == '__main__':
    # 测试代码
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python wol.py <MAC地址> [广播地址] [端口]")
        print("示例: python wol.py AA:BB:CC:DD:EE:FF 192.168.1.255 9")
        sys.exit(1)
    
    mac = sys.argv[1]
    broadcast = sys.argv[2] if len(sys.argv) > 2 else '255.255.255.255'
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 9
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 发送WOL包
    success = wake_on_lan(mac, broadcast, port)
    
    if success:
        print(f"✓ 成功发送唤醒包到 {mac}")
        sys.exit(0)
    else:
        print(f"✗ 发送唤醒包失败")
        sys.exit(1)
