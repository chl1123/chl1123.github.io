import logging
from logging.handlers import RotatingFileHandler
from typing import Any

log_dir = '/opt/.data/diagnosis/ide/logs/'


class Logger:

    def __init__(self, filename):
        self.filename = filename
        self.formatter = '%(asctime)s %(filename)s:%(lineno)d %(levelname)s: %(message)s'
        self.__logger = self._create_logger()
        self.__logger.addHandler(self._file_logger())
        self.__logger.addHandler(self._console_logger())

    def _create_logger(self):
        _logger = logging.getLogger("rbk.script")
        _logger.setLevel(level=logging.INFO)
        return _logger

    def _file_logger(self):
        size_rotate_file = RotatingFileHandler(filename=log_dir + self.filename + ".log", maxBytes=1024 * 1024,
                                               backupCount=5, encoding='utf-8')
        size_rotate_file.setFormatter(logging.Formatter(self.formatter))
        size_rotate_file.setLevel(logging.DEBUG)
        return size_rotate_file

    def _console_logger(self):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level=logging.DEBUG)
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
