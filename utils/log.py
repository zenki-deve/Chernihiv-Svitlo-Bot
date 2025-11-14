from colorama import Fore, Style, init
import logging
import sys

def setup_logger(name=None, log_file=None, log_level=logging.DEBUG):
    """
    Configure a logger with colored console output and optional file logging.

    :param name: Logger name (default None uses the root logger).
    :param log_file: Path to the log file (default None, no file output).
    :param log_level: Logging level (default logging.DEBUG).
    :return: Configured logger instance.
    """
    init(autoreset=True)

    class ColorFormatter(logging.Formatter):
        # Define format and color codes for each logging level
        FORMAT = "%(asctime)s | %(levelname)s | %(lineno)d - %(message)s"
        COLOR_CODES = {
            logging.DEBUG: Fore.BLUE,
            logging.INFO: Fore.GREEN,
            logging.WARNING: Fore.YELLOW,
            logging.ERROR: Fore.RED,
            logging.CRITICAL: Fore.MAGENTA,
        }

        def format(self, record):
            log_fmt = self.FORMAT
            if record.levelno in self.COLOR_CODES:
                color = self.COLOR_CODES[record.levelno]
                log_fmt = color + log_fmt + Style.RESET_ALL
            formatter = logging.Formatter(log_fmt)
            return formatter.format(record)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = ColorFormatter()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # If log_file is provided, add a file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(ColorFormatter.FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger
