import json
import typing

class Config(dict):
    # CONF_PATH = 

    def __init__(self, conf_path):
        super(Config, self).__init__()
        self.conf_path = conf_path
        self.update(self.load_dirs())

    def load_dirs(self) -> (None, typing.Dict[str, str]):
        try:
            with open(self.conf_path) as f:
                return json.load(f)
        except json.JSONDecodeError:
            return

    def save_conf(self) -> None:
        with open(self.conf_path, 'w') as f:
            json.dump(self, f)

    def current(self) -> str:
        return self['directories'][self['current']]