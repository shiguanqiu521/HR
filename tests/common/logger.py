# -*- coding: utf-8 -*-
"""
日志组件
支持控制台输出 + 文件记录
"""
import logging
import os
from datetime import datetime
from config import Config


class Logger:
    """日志工具类"""
    
    _instance = None
    _logger = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger()
        return cls._instance
    
    def _init_logger(self):
        """初始化日志配置"""
        self._logger = logging.getLogger("hr_test")
        self._logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # 避免重复添加 handler
        if self._logger.handlers:
            return
        
        # 日志格式
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # 控制台 handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)
        
        # 文件 handler
        os.makedirs(Config.LOG_DIR, exist_ok=True)
        log_file = os.path.join(
            Config.LOG_DIR,
            f"test_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)
    
    def get_logger(self):
        """
        获取底层 logging.Logger 实例
        
        Returns:
            logging.Logger: 配置好的日志记录器实例
        """
        return self._logger
    
    def debug(self, msg):
        """
        记录 DEBUG 级别日志
        
        Args:
            msg: 日志消息内容
        """
        self._logger.debug(msg)
    
    def info(self, msg):
        """
        记录 INFO 级别日志
        
        Args:
            msg: 日志消息内容
        """
        self._logger.info(msg)
    
    def warning(self, msg):
        """
        记录 WARNING 级别日志
        
        Args:
            msg: 日志消息内容
        """
        self._logger.warning(msg)
    
    def error(self, msg):
        """
        记录 ERROR 级别日志
        
        Args:
            msg: 日志消息内容
        """
        self._logger.error(msg)
    
    def critical(self, msg):
        """
        记录 CRITICAL 级别日志
        
        Args:
            msg: 日志消息内容
        """
        self._logger.critical(msg)


# 全局日志实例
logger = Logger()
