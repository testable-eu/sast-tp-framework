import logging
import config

"""
Module that manage logging
"""

class ColoredFormatter(logging.Formatter):
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"

    def format(self, record):
        if record.levelno == logging.WARNING:
            record.msg = f"{self.YELLOW}{record.msg}{self.RESET}"
        elif record.levelno == logging.ERROR:
            record.msg = f"{self.RED}{record.msg}{self.RESET}"
        return super().format(record)


mainLogger = logging.getLogger(config.rootLoggerName)

# Log file formatter and handler
formatter = ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')
mainLogger.setLevel(getattr(logging, config.loggingLevelFile))
main_logfile_path = config.RESULT_DIR / config.logfile
logfile_handler = logging.FileHandler(main_logfile_path)
logfile_handler.setFormatter(formatter)

# Adding handlers to main logger
mainLogger.addHandler(logfile_handler)

# mainLogger.info("Logger module initialized")


def logger_name(name):
    return config.rootLoggerName + "." + name


def add_logger(loggerFile):
    global formatter, mainLogger
    new_logfile_handler = logging.FileHandler(loggerFile)
    new_logfile_handler.setFormatter(formatter)
    mainLogger.addHandler(new_logfile_handler)


def add_console_logger():
    global mainLogger
    # Console formatter and handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.loggingLevelConsole))
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M')
    console_handler.setFormatter(console_formatter)
    mainLogger.addHandler(console_handler)