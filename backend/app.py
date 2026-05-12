import os

import yaml

from applications import create_app

app = create_app()


def _load_runtime_config():
    config_path = os.getenv("CONFIG_PATH", "../config.yaml")
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file.read()) or {}
    except FileNotFoundError:
        return {}


if __name__ == "__main__":
    config = _load_runtime_config()
    host = (config.get("host") or {}).get("backend", "0.0.0.0")
    port = int((config.get("port") or {}).get("backend", 5008))
    app.run(host=host, port=port, debug=False)
