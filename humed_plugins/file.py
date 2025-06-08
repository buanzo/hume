import json
from pathlib import Path

TRANSFER_METHOD = 'file'

CONFIG_TEMPLATE = {
    'path': 'humed.log'
}

def send(humepkt=None, config=None):
    """Append JSON packet to a log file."""
    path = config.get('path', 'humed.log') if isinstance(config, dict) else 'humed.log'
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a') as f:
        f.write(json.dumps(humepkt) + '\n')
    return True
