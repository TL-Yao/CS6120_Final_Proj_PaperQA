import logging

def setup_logger(name):
    """
    setup and return a configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # if logger has handlers, return logger
    if logger.handlers:
        return logger

    # create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # add handler to logger
    logger.addHandler(console_handler)

    return logger 