import logging

def get_logger():
    logger = logging.getLogger("EXTRACTOR_V4")
    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    fmt = logging.Formatter("[%(levelname)s] %(message)s")
    ch.setFormatter(fmt)

    logger.addHandler(ch)
    return logger
