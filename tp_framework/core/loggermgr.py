import logging
import config

"""
Module that manage logging
"""

mainLogger = logging.getLogger(config.rootLoggerName)

# Log file formatter and handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s',
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