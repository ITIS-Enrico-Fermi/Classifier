from os import path
from typing import Dict, Tuple

import sys
sys.path.append(path.dirname(__file__))
from ymlparser import load_yaml

config_file = 'config.yml'
config_file_path = path.join(path.dirname(__file__), config_file)

config_boundarys: Dict[str, Dict[str, Tuple[int, int]]] = tuple()
if path.isfile(config_file_path):
    cb: Dict = load_yaml(config_file_path)
    config_boundarys = {
            'face': {
                'min': (int(cb['min']['face']['width']), int(cb['min']['face']['height'])),
                'max': (int(cb['max']['face']['width']), int(cb['max']['face']['height']))
            },
            'body': {
                'min': (int(cb['min']['body']['width']), int(cb['min']['body']['height'])),
                'max': (int(cb['max']['body']['width']), int(cb['max']['body']['height']))
            }
    }