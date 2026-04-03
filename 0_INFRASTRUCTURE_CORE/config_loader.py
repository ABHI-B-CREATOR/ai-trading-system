import yaml
import os


class ConfigLoader:

    def __init__(self, path="cloud_config.yaml"):
        self.path = path
        self.config = None
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            raise FileNotFoundError(
                f"Config file not found → {self.path}"
            )

        with open(self.path, "r") as f:
            self.config = yaml.safe_load(f)

    def get(self, *keys):
        data = self.config
        for k in keys:
            data = data.get(k, None)
            if data is None:
                return None
        return data

    def reload(self):
        self._load()


# quick test
if __name__ == "__main__":
    cfg = ConfigLoader()
    print(cfg.get("system", "mode"))