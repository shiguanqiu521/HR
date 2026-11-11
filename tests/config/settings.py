# -*- coding: utf-8 -*-
"""
环境配置管理模块
支持运行时动态切换环境（dev / test / prod）

环境配置优先级（从高到低）：
    1. 操作系统环境变量（如 export HR_BASE_URL=...）
    2. .env.{环境名} 文件中的配置
    3. 代码中的默认值

使用方式：
    from config import Config
    print(Config.BASE_URL)          # 读取当前环境配置

    from config.settings import switch_env
    switch_env("test")              # 运行时切换到测试环境
    print(Config.BASE_URL)          # 已变为测试环境地址

命令行切换（pytest）：
    pytest --env test
    pytest --env prod
"""
import os
from dotenv import load_dotenv

# .env 文件所在目录（与 settings.py 同级）
_ENV_DIR = os.path.dirname(os.path.abspath(__file__))

# 项目根目录（tests/ 目录，用于计算日志和报告的绝对路径）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_ENV_DIR))

# 支持的环境列表
VALID_ENVS = ("dev", "test", "prod")

# .env 文件中使用的配置键名
_ENV_KEYS = ("HR_BASE_URL", "HR_ADMIN_USER", "HR_ADMIN_PWD", "HR_LOG_LEVEL", "HR_JWT_SECRET")


class _EnvProxy:
    """
    环境配置代理对象

    通过属性访问获取当前环境的配置值。
    调用 switch_env() 后，Config 代理的所有属性自动更新为新环境值。

    Attributes:
        BASE_URL: 服务基础地址
        ADMIN_USERNAME: 管理员用户名
        ADMIN_PASSWORD: 管理员密码
        REQUEST_TIMEOUT: HTTP 请求超时时间（秒）
        LOG_LEVEL: 日志级别
        JWT_SECRET: 后端 hr.auth.jwt-secret，仅用于 TC-AUTH-014 本地自签过期 token；默认空
        LOG_DIR: 日志文件输出目录（绝对路径）
        REPORT_DIR: 测试报告输出目录（绝对路径）
        ENV_NAME: 当前环境名称
    """

    def __init__(self):
        self._env_name = None
        self._reload()

    def _reload(self):
        """从当前 os.environ 重新加载所有配置项"""
        self.BASE_URL = os.environ.get("HR_BASE_URL", "http://localhost:8080")
        self.ADMIN_USERNAME = os.environ.get("HR_ADMIN_USER", "admin")
        self.ADMIN_PASSWORD = os.environ.get("HR_ADMIN_PWD", "admin123")
        self.REQUEST_TIMEOUT = 10
        self.LOG_LEVEL = os.environ.get("HR_LOG_LEVEL", "INFO")
        self.JWT_SECRET = os.environ.get("HR_JWT_SECRET", "")
        self.LOG_DIR = os.path.join(_PROJECT_ROOT, "logs")
        self.REPORT_DIR = os.path.join(_PROJECT_ROOT, "reports")

    def load_env(self, env_name: str):
        """
        加载指定环境的 .env 文件并刷新配置

        Args:
            env_name: 环境名称（dev / test / prod）

        Raises:
            ValueError: 环境名称不在 VALID_ENVS 中
        """
        if env_name not in VALID_ENVS:
            raise ValueError(f"未知环境: {env_name!r}，可选: {VALID_ENVS}")

        env_file = os.path.join(_ENV_DIR, f".env.{env_name}")
        if not os.path.exists(env_file):
            raise FileNotFoundError(f"环境配置文件不存在: {env_file}")

        # 清除上一个环境写入 os.environ 的键，避免残留值污染新环境
        for key in _ENV_KEYS:
            os.environ.pop(key, None)

        # 加载新环境的 .env 文件，override=True 使其覆盖已有的 os.environ
        load_dotenv(env_file, override=True)

        self._env_name = env_name
        self._reload()

    @property
    def ENV_NAME(self) -> str:
        """当前环境名称（dev / test / prod）"""
        return self._env_name or os.environ.get("HR_ENV", "dev")

    def __repr__(self):
        return (
            f"<EnvConfig env={self.ENV_NAME!r} "
            f"base_url={self.BASE_URL!r} "
            f"log_level={self.LOG_LEVEL!r}>"
        )


# ── 全局单例 ────────────────────────────────────────────────────────────────
# 其他模块通过 from config import Config 使用，属性访问方式不变
Config = _EnvProxy()


def switch_env(env_name: str):
    """
    运行时切换环境配置

    切换后，全局 Config 对象的所有属性（BASE_URL、ADMIN_USERNAME 等）
    自动更新为新环境的值，无需重新导入。

    Args:
        env_name: 目标环境名称（dev / test / prod）

    Raises:
        ValueError: 环境名称不合法
        FileNotFoundError: 对应的 .env 文件不存在

    Example:
        >>> switch_env("test")
        >>> Config.BASE_URL
        'http://test-server:8080'
    """
    Config.load_env(env_name)
