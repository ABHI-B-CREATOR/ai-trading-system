import logging
import logging.config
import yaml
import os


def setup_logging(
        config_path="logging_config.yaml",
        default_level=logging.INFO):

    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f.read())
            logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


def get_logger(name):
    return logging.getLogger(name)