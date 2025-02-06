import os
import sys
import time
import logging
from loguru import logger

from types import FrameType
from typing import cast


class Logger:
    """输出日志到文件和控制台"""

    def __init__(self):
        # 文件的命名
        LogPath = '/opt/.data/diagnosis/ide/logs'  # 假设这是你的日志路径

        try:
            if not os.path.exists(LogPath):
                # 确保整个路径都被创建
                os.makedirs(LogPath, exist_ok=True)  # 这个方法会在目录已存在时不抛出异常
        except OSError as e:
            # 捕获可能的其他OS错误，如磁盘满等
            LogPath = "logs"
            # logging.error(f"Failed to create directory {LogPath}: {e}")
            # raise  # 或者你可以选择在这里处理异常而不是重新抛出

        log_name = f"syspy_{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime()).replace('-', '_')}.log"
        log_path = os.path.join(LogPath, log_name)
        self.logger = logger
        # 清空所有设置
        self.logger.remove()
        # 判断日志文件夹是否存在，不存在则创建
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        # 日志输出格式
        formatter = "{time:YYYY-MM-DD HH:mm:ss} | {level}: {message}"
        # 添加控制台输出的格式
        self.logger.add(sys.stdout,
                        format="<green>{time:YYYYMMDD HH:mm:ss}</green> | "  # 颜色>时间
                               "{process.name} | "  # 进程名
                               "{thread.name} | "  # 线程名
                               "<cyan>{module}</cyan>.<cyan>{function}</cyan>"  # 模块名.方法名
                               ":<cyan>{line}</cyan> | "  # 行号
                               "<level>{level}</level>: "  # 等级
                               "<level>{message}</level>",  # 日志内容
                        filter=self.exclude_protocol_logs
                        )
        # 日志写入文件
        self.logger.add(log_path,  # 写入目录指定文件
                        format='{time:YYYYMMDD HH:mm:ss} - '  # 时间
                               "{process.name} | "  # 进程名
                               "{thread.name} | "  # 进程名
                               '{module}.{function}:{line} - {level} -{message}',  # 模块名.方法名:行号
                        encoding='utf-8',
                        retention='7 days',  # 设置历史保留时长
                        backtrace=True,  # 回溯
                        diagnose=True,  # 诊断
                        enqueue=True,  # 异步写入
                        rotation="20 MB",  # 每日更新时间
                        filter=self.exclude_protocol_logs
                        )

    def exclude_protocol_logs(self, record):
        return not record["module"].startswith("protocol")

    def init_config(self):
        LOGGER_NAMES = ("uvicorn.asgi", "uvicorn.access", "uvicorn")
        # change handler for default uvicorn logger
        logging.getLogger().handlers = [InterceptHandler()]
        for logger_name in LOGGER_NAMES:
            logging_logger = logging.getLogger(logger_name)
            logging_logger.handlers = [InterceptHandler()]
            logging_logger.setLevel(logging.DEBUG)  # 确保日志级别正确
            logging_logger.propagate = False

    def get_logger(self):
        return self.logger


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:  # noqa: WPS609
            frame = cast(FrameType, frame.f_back)
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage(),
        )


Loggers = Logger()
log = Loggers.get_logger()