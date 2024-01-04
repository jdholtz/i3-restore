import json
import os
import sys

import utils

CONFIG_FILE_NAME = "config.json"

# Type alias for JSON
JSON = utils.JSON

logger = utils.get_logger()


class Config:
    def __init__(self):
        # Default values are set
        self.terminals = []
        self.subprocesses = []
        self.web_browsers = []

        config = self._read_config()

        # Set the configuration values if provided
        try:
            self._parse_config(config)
        except TypeError as err:
            logger.error("Error in configuration file:")
            logger.error(err)
            sys.exit(1)

    def _read_config(self) -> JSON:
        project_dir = os.path.dirname(os.path.dirname(__file__))
        config_file = project_dir + "/" + CONFIG_FILE_NAME

        try:
            with open(config_file) as file:
                config = json.load(file)
            logger.info("Configuration file found at %s", config_file)
        except FileNotFoundError:
            logger.info("No configuration file found at %s", config_file)
            config = {}

        return config

    def _parse_config(self, config: JSON) -> None:
        if "subprocesses" in config:
            self.subprocesses = config["subprocesses"]
            logger.info("Subprocesses configuration: %s", self.subprocesses)

            if not isinstance(self.subprocesses, list):
                raise TypeError("'subprocesses' must be a list")

        if "terminals" in config:
            self.terminals = config["terminals"]
            logger.info("Terminals configuration: %s", self.terminals)

            if not isinstance(self.terminals, list):
                raise TypeError("'terminals' must be a list")

        if "web_browsers" in config:
            self.web_browsers = config["web_browsers"]
            logger.info("Web browsers configuration: %s", self.web_browsers)

            if not isinstance(self.web_browsers, list):
                raise TypeError("'web_browsers' must be a list")
