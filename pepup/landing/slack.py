import json
import requests

from landing.loader import load_credential


def slack_message(message):
    incomming_url = load_credential("SLACK_INCOMMING_URL", "")
    post_data = {"text": '{}'.format(message)}
    data = json.dumps(post_data)
    headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}
    response = requests.post(incomming_url, headers=headers, data=data)
    return None