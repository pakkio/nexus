import configparser
import os
from pathlib import Path

_config = configparser.ConfigParser()
_config.read(Path(__file__).parent / 'config.ini')

def _get(key: str, fallback: str = '') -> str:
    return _config.get('models', key, fallback=fallback)

MODEL_DEFAULT         = _get('default',          'google/gemini-2.0-flash-001')
MODEL_PROFILE         = _get('profile_analysis', MODEL_DEFAULT)
MODEL_GUIDE           = _get('guide_selection',  MODEL_DEFAULT)
MODEL_LLSETTEXT       = _get('llsettext',        MODEL_DEFAULT)
MODEL_EVAL            = _get('eval',             'google/gemma-3-4b-it:free')
