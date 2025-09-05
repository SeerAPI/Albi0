import logging
import sys

import loguru

logger = loguru.logger


class LoguruHandler(logging.Handler):  # pragma: no cover
	"""将 logging 的日志转发到 loguru。"""

	def emit(self, record: logging.LogRecord):
		try:
			level = logger.level(record.levelname).name
		except ValueError:
			level = record.levelno

		frame, depth = sys._getframe(6), 6
		while frame and frame.f_code.co_filename == logging.__file__:
			frame = frame.f_back
			depth += 1

		logger.opt(depth=depth, exception=record.exc_info).log(
			level, record.getMessage()
		)
