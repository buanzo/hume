import requests

TRANSFER_METHOD = 'http'

CONFIG_TEMPLATE = {
    'url': 'http://localhost:8000/events',
    'timeout': 5,
}

def send(humepkt=None, config=None):
    """Send JSON packet via HTTP POST."""
    if humepkt is None or not isinstance(config, dict):
        return False
    url = config.get('url')
    timeout = config.get('timeout', 5)
    if not url:
        return False
    try:
        resp = requests.post(url, json=humepkt, timeout=timeout)
        return resp.status_code in (200, 201, 202)
    except Exception:
        return False
