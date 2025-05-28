import json
import os
import sys

import constants
import utils

CONFIG_FILE_NAME = "config.json"

# Type alias for JSON
JSON = utils.JSON

logger = utils.get_logger()

KITTY_PLUGIN_SCROLLBACK_OPTIONS = ["all", "screen", "none"]


class Config:
    def __init__(self) -> None:
        # Default values are set
        self.terminals = []
        self.subprocesses = []
        self.web_browsers = []
        self.enabled_plugins = {}

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

            # Check for deprecated 'args' keyword in subprocesses
            # Will be removed the version after this change is released
            for program in self.subprocesses:
                if program.get("args") is not None:
                    logger.error("Keyword 'args' is deprecated, use 'include_args' instead")

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

        if "enabled_plugins" in config:
            enabled_plugins = config["enabled_plugins"]
            if not isinstance(enabled_plugins, dict):
                raise TypeError("'enabled_plugins' must be a dictionary")

            self.enabled_plugins = self._parse_plugins(enabled_plugins)
            logger.info("Enabled plugins: %s", self.enabled_plugins)

    def _parse_plugins(self, plugins: JSON) -> JSON:
        # Available plugin parsers. The key is the plugin name and the value is the
        # function used to parse the plugin.
        plugin_parsers = {constants.KITTY_CLASS: parse_kitty_plugin}

        parsed_plugins = {}

        for name, parser in plugin_parsers.items():
            if name in plugins:
                parsed_plugins[name] = parser(plugins[name])

        return parsed_plugins


def parse_kitty_plugin(plugin: JSON) -> JSON:
    if not isinstance(plugin, dict):
        raise TypeError(f"'{constants.KITTY_CLASS}' plugin must be a dictionary")

    if "listen_socket" not in plugin:
        raise TypeError("kitty plugin: 'listen_socket' must be included")

    plugin_config = {
        "listen_socket": plugin["listen_socket"],
        "scrollback": plugin.get("scrollback", "none"),
    }

    if plugin_config["scrollback"] not in KITTY_PLUGIN_SCROLLBACK_OPTIONS:
        raise TypeError(
            f"kitty plugin: 'scrollback' must be one of: {KITTY_PLUGIN_SCROLLBACK_OPTIONS}"
        )

    return plugin_config
