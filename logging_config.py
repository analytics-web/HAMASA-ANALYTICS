import logging
import logging.handlers
import os

def setup_logging(app_env: str, log_file: str = None):
    """Configure logging based on environment."""

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(log_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers (important if reloading in dev)
    if root_logger.handlers:
        for h in root_logger.handlers:
            root_logger.removeHandler(h)

    if app_env == "development":
        # Console logging only
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Rotating file handler: 10MB per file, keep 5 backups
            file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    else:  # production
        # Make sure logs directory exists
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            # Rotating file handler: 10MB per file, keep 5 backups
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=5
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        # Also keep console logs at WARNING+ in prod
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
