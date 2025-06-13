import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

class ConfigManager:
    _config = None

    @classmethod
    def load(cls):
        if cls._config is not None:
            return cls._config
        if not os.path.exists(CONFIG_PATH):
            raise FileNotFoundError("Initiate config")
        with open(CONFIG_PATH, 'r') as f:
            cls._config = json.load(f)
        return cls._config

    @classmethod
    def save(cls, config_dict):
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config_dict, f, indent=2)
        cls._config = config_dict

    @classmethod
    def get_env(cls):
        return cls.load().get("environment", {})

    @classmethod
    def get_servers(cls):
        return cls.load().get("mcpServers", {})

    @classmethod
    def get_path(cls):
        return CONFIG_PATH