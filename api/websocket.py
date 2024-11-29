import json
import requests

from django.conf import settings

api_key = settings.CENTRIFUGO_API_KEY

def send_message_to_centrifuge(channel: str, message: dict, type: str = "message"):
    print("Sending a message to channel", channel)
    message['type'] = type
    data = json.dumps({
        "channel": channel,
        "data": message
    })

    headers = {'Content-type': 'application/json', 'X-API-Key': api_key}
    resp = requests.post(
        "http://127.0.0.1:8000/api/publish", 
        data=data, 
        headers=headers
    )
    return resp.json()

def broadcast_message_to_centrifuge(channels: list, message: dict):
    data = json.dumps({
        "channels": channels,
        "data": message
    })

    headers = {'Content-type': 'application/json', 'X-API-Key': api_key}
    resp = requests.post(
        "http://127.0.0.1:8000/api/broadcast",
        data=data,
        headers=headers
    )
    return resp.json()