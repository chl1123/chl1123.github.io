import os
import sys
import time

from loguru import logger


class Logger:
    """输出日志到文件和控制台"""

    def __init__(self, log_prefix: str = 'syspy', console: bool = False, file: bool = True):
        self.log_prefix = log_prefix
        # 文件的命名
        log_dir = '/opt/.data/diagnosis/ide/logs'  # 日志路径
        # 初始化路径设置
        self.log_dir = self._validate_log_dir(log_dir)
        # 初始化logger核心配置
        self._configure_logger(console, file)

    def _validate_log_dir(self, path: str) -> str:
        """路径有效性验证"""
        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            return path
        except OSError as e:
            fallback_path = "logs"
            os.makedirs(fallback_path, exist_ok=True)
            print(f"Failed to create directory {path}: {e}")
            return fallback_path

    def _configure_logger(self, console: bool, file: bool):
        """核心配置方法"""
        self.logger = logger
        self.logger.remove()  # 清除默认配置

        if console:
            self._add_console_handler()

        if file:
            self._add_file_handler()

    def _add_console_handler(self):
        """控制台输出配置"""
        console_format = (
            "<green>{time:YYYYMMDD HH:mm:ss}</green> | "  # 颜色>时间
            "{process.name} | {thread.name} | "  # 进程名 | 线程名
            "<cyan>{module}</cyan>.<cyan>{function}</cyan>:<cyan>{line}</cyan> | "  # 模块名.方法名:行号
            "<level>{level}</level>: <level>{message}</level>"  # 等级: 日志内容
        )
        self.logger.add(
            sys.stdout,
            format=console_format,
            filter=self._exclude_protocol_logs,
            colorize=True  # 显式启用颜色
        )

    def _add_file_handler(self):
        """文件输出配置"""
        log_name = f"{self.log_prefix}_{time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime())}.log"
        log_path = os.path.join(self.log_dir, log_name)
        file_format = (
            "{time:YYYYMMDD HH:mm:ss} | "  # 时间
            "{process.name} | {thread.name} | "  # 进程名 | 线程名
            "{module}.{function}:{line} | {level} | {message}"  # 模块名.方法名:行号
        )
        self.logger.add(
            log_path,
            format=file_format,
            encoding="utf-8",
            rotation="20 MB",  # 最大文件大小
            retention=10,  # 最多保留20个文件
            enqueue=True,  # 异步写入
            backtrace=True,  # 回溯
            diagnose=True,  # 诊断
            filter=self._exclude_protocol_logs,
        )

    def _exclude_protocol_logs(self, record):
        return not record["module"].startswith("protocol")

    def get_logger(self):
        return self.logger


Loggers = Logger(console=True)
log = Loggers.get_logger()
