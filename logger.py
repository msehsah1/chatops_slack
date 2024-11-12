# logging_config.py
import logging
import os
import sys
import traceback
from datetime import datetime
from termcolor import colored

# Environment Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
DEBUG = os.getenv('DEBUG', 'False').lower() in ['true', '1', 'yes']
if DEBUG:
    LOG_LEVEL = 'DEBUG'

# Optionally disable color printing
DISABLE_COLOR_PRINTING = False

# Define color mappings for different log levels
LOG_COLORS = {
    logging.DEBUG: 'cyan',
    logging.INFO: 'green',
    logging.WARNING: 'yellow',
    logging.ERROR: 'red',
    logging.CRITICAL: 'magenta',
}

# Custom Formatter with Color Support Based on Log Level
class LevelColoredFormatter(logging.Formatter):
    def format(self, record):
        # Apply color based on the log level
        color = LOG_COLORS.get(record.levelno, 'white')
        if not DISABLE_COLOR_PRINTING:
            levelname = colored(record.levelname, color, attrs=['bold'])
            asctime = colored(self.formatTime(record, self.datefmt), 'light_grey')
            name = colored(record.name, 'light_blue')
            message = record.getMessage()
            formatted_message = f"{asctime} - {name}:{levelname}: {record.filename}:{record.lineno} - {message}"
            return formatted_message
        else:
            return super().format(record)

# Function to create a console handler
def get_console_handler(log_level=logging.INFO):
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    formatter = LevelColoredFormatter(
        fmt='%(asctime)s - %(name)s:%(levelname)s: %(filename)s:%(lineno)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    return console_handler

# Set up the main logger
def setup_logger(name='chatops'):
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    # Prevent duplicate handlers
    if not logger.handlers:
        console_handler = get_console_handler(getattr(logging, LOG_LEVEL, logging.INFO))
        logger.addHandler(console_handler)
    # Prevent log propagation to the root logger
    logger.propagate = False
    return logger

# Function to log uncaught exceptions
def log_uncaught_exceptions(ex_cls, ex, tb):
    logger = logging.getLogger('chatops')
    formatted_tb = ''.join(traceback.format_tb(tb))
    logger.error(f"Uncaught exception:\n{formatted_tb}")
    logger.error(f"{ex_cls.__name__}: {ex}")

# Set the custom exception hook
sys.excepthook = log_uncaught_exceptions

# Initialize the main logger
main_logger = setup_logger('chatops')
if DEBUG:
    main_logger.debug('DEBUG mode enabled.')
main_logger.info('Logging initialized.')
