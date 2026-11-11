# -*- coding: utf-8 -*-
"""
配置模块
提供全局 Config 对象和环境切换函数 switch_env

使用示例：
    from config import Config, switch_env

    # 读取当前环境配置
    print(Config.BASE_URL)

    # 运行时切换环境
    switch_env("test")
    print(Config.BASE_URL)  # 已更新为测试环境地址
"""
from .settings import Config, switch_env, VALID_ENVS

__all__ = ["Config", "switch_env", "VALID_ENVS"]
