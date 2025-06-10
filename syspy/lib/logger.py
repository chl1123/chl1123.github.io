import logging
import os
import time
from logging.handlers import RotatingFileHandler
from typing import Any

log_dir = '/opt/.data/diagnosis/rbk/logs/scripts/'


class BackupCountRotatingFileHandler(RotatingFileHandler):
    def __init__(self, base_filename: str, maxBytes: int, backupCount: int, encoding: str = None,
                 totalBackupCount: int = 50):
        """ 按照文件大小、限制同前缀文件个人和总文件个数的轮转处理器

        Args:
            base_filename: 日志前缀路径
            maxBytes: 单个文件最大字节数
            backupCount: 相同前缀限制文件数量
            encoding: 编码
            totalBackupCount: log_dir目录限制总文件数量
        """
        self.base_filename = base_filename
        self.total_backup_count = totalBackupCount
        # 日志追加
        self.current_logfile = self._find_existing_log_file() or self._generate_log_filename()
        super().__init__(filename=self.current_logfile, maxBytes=maxBytes, backupCount=backupCount, encoding=encoding)

    def _find_existing_log_file(self):
        """
        查找已有日志路径
        """
        base_filename_log_files = [
            f for f in os.listdir(log_dir)
            if f.startswith(os.path.basename(self.base_filename)) and f.endswith(".log")
        ]
        if base_filename_log_files:
            # 按修改时间排序（最新的在最后）
            base_filename_log_files.sort(key=lambda f: os.path.getmtime(os.path.join(log_dir, f)), reverse=True)
            return os.path.join(log_dir, base_filename_log_files[0])
        return None

    def _generate_log_filename(self):
        """
        生成带时间戳的日志文件名
        """
        timestamp = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime())
        return f"{self.base_filename}_{timestamp}.log"

    def doRollover(self):
        """
        覆盖 RotatingFileHandler 的 doRollover 方法，在轮转时生成新的时间戳文件名，
        并删除超出 backupCount 的旧文件。
        """
        # 关闭当前文件流
        if self.stream:
            self.stream.close()
            self.stream = None

        # 删除超出 backupCount 的旧文件
        self._cleanup_old_logs()

        # 生成新的日志文件名
        self.current_logfile = self._generate_log_filename()

        # 打开新的日志文件
        self.baseFilename = self.current_logfile
        if not self.delay:
            self.stream = self._open()

    def _cleanup_old_logs(self):
        """
        删除超出 backupCount 的旧日志文件，并限制总的日志文件数量
        """
        if self.backupCount > 0:
            # 获取所有以 base_filename 开头的文件
            base_filename_log_files = [
                f for f in os.listdir(log_dir)
                if f.startswith(os.path.basename(self.base_filename)) and f.endswith(".log")
            ]
            # 按修改时间排序（最新的在最后）
            base_filename_log_files.sort(key=lambda f: os.path.getmtime(os.path.join(log_dir, f)), reverse=True)

            # 删除超出 backupCount 的文件
            for log_file in base_filename_log_files[self.backupCount:]:
                try:
                    os.remove(os.path.join(log_dir, log_file))
                except Exception as e:
                    print(f"Failed to delete old log file {log_file}: {e}")

        if self.total_backup_count > 0:
            # 获取所有以 base_filename 开头的文件
            log_files = [
                f for f in os.listdir(log_dir)
                if f.endswith(".log")
            ]
            # 按修改时间排序（最新的在最后）
            log_files.sort(key=lambda f: os.path.getmtime(os.path.join(log_dir, f)), reverse=True)

            # 限制总的日志文件数量
            total_log_files = len(log_files)
            if total_log_files > self.total_backup_count:
                for log_file in log_files[self.total_backup_count:]:
                    try:
                        os.remove(os.path.join(log_dir, log_file))
                    except Exception as e:
                        print(f"Failed to delete old log file {log_file}: {e}")


class Logger:

    def __init__(self, filename):
        self.filename = filename
        self.formatter = '%(asctime)s %(filename)s:%(lineno)d %(levelname)s: %(message)s'
        self._ensure_log_directory_exists()
        self.__logger = self._create_logger()

    def _ensure_log_directory_exists(self):
        """
        确保日志目录存在
        """
        log_directory = os.path.dirname(log_dir)
        if not os.path.exists(log_directory):
            os.makedirs(log_directory, exist_ok=True)

    def _create_logger(self):
        _logger = logging.getLogger("rbk.script")
        _logger.setLevel(logging.DEBUG)
        if not _logger.handlers:
            _logger.addHandler(self._file_logger())
            _logger.addHandler(self._console_logger())
        return _logger

    def _file_logger(self):
        """
        使用自定义的 TimedRotatingFileHandler 创建文件日志处理器
        """
        handler = BackupCountRotatingFileHandler(
            base_filename=f"{log_dir}{self.filename}",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,  # 同类日志文件保留5个
            encoding='utf-8',
            totalBackupCount=50  # 总共保留50个日志文件
        )
        handler.setFormatter(logging.Formatter(self.formatter))
        handler.setLevel(logging.DEBUG)
        return handler

    def _console_logger(self):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level=logging.INFO)
        console_handler.setFormatter(logging.Formatter(self.formatter))
        return console_handler

    def _format_message(self, msg: Any, *args) -> str:
        """统一消息格式化处理"""
        if isinstance(msg, str):
            try:
                return msg % args  # 尝试标准格式化
            except (TypeError, ValueError):
                return f"{msg} {' '.join(map(str, args))}".strip()
        return f"{msg} {' '.join(map(str, args))}".strip()

    def debug(self, msg: Any, *args, **kwargs):
        self.__logger.debug(self._format_message(msg, *args), stacklevel=2, **kwargs)

    def info(self, msg: Any, *args, **kwargs):
        self.__logger.info(self._format_message(msg, *args), stacklevel=2, **kwargs)

    def warning(self, msg: Any, *args, **kwargs):
        self.__logger.warning(self._format_message(msg, *args), stacklevel=2, **kwargs)

    def error(self, msg: Any, *args, **kwargs):
        self.__logger.error(self._format_message(msg, *args), stacklevel=2, **kwargs)

    def critical(self, msg: Any, *args, **kwargs):
        self.__logger.critical(self._format_message(msg, *args), stacklevel=2, **kwargs)


if __name__ == '__main__':
    logger = Logger("test")
    for i in range(100000000):
        logger.info(i, 1)
