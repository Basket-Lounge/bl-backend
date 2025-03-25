import json
import requests
import logging

from django.conf import settings


logger = logging.getLogger(__name__)
api_key = settings.CENTRIFUGO_API_KEY
centrifugo_url = settings.CENTRIFUGO_URL


def disconnect_user_from_channel(user_id: int, channel: str):
    logger.info("Disconnecting user %s from channel %s", user_id, channel)

    data = json.dumps({
        "user": str(user_id),
        "channel": channel
    })

    try:
        headers = {'Content-type': 'application/json', 'X-API-Key': api_key}
        resp = requests.post(
            f"{centrifugo_url}/api/unsubscribe",
            data=data,
            headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info("Response from centrifugo: %s", data)

        if data.get('error', None):
            logger.error("Error disconnecting user from channel: %s", data['error'])
            return None
        
        return data
    except requests.exceptions.HTTPError as e:
        logger.error("Error disconnecting user from channel: %s", e)
        return None

def send_message_to_centrifuge(channel: str, message: dict, type: str = "message"):
    logger.info("Sending a message to channel %s", channel)

    message['type'] = type
    data = json.dumps({
        "channel": channel,
        "data": message
    })

    try:
        headers = {'Content-type': 'application/json', 'X-API-Key': api_key}
        resp = requests.post(
            f"{centrifugo_url}/api/publish", 
            data=data, 
            headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info("Response from centrifugo: %s", data)

        if data.get('error', None):
            logger.error("Error sending message to centrifugo: %s", data['error'])
            return None
        
        return data
    except requests.exceptions.ConnectionError as e:
        logger.error("Error connecting to centrifugo: %s", e)
        return None
    except requests.exceptions.HTTPError as e:
        logger.error("Error sending message to centrifugo: %s", e)
        return None
    except Exception as e:
        logger.error("Error sending message to centrifugo: %s", e)
        return None

def broadcast_message_to_centrifuge(channels: list, message: dict):
    logger.info("Broadcasting a message to channels %s", channels)

    data = json.dumps({
        "channels": channels,
        "data": message
    })

    try:
        headers = {'Content-type': 'application/json', 'X-API-Key': api_key}
        resp = requests.post(
            f"{centrifugo_url}/api/broadcast",
            data=data,
            headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info("Response from centrifugo: %s", data)

        if data.get('error', None):
            logger.error("Error broadcasting message to centrifugo: %s", data['error'])
            return None
        
        return data
    except requests.exceptions.HTTPError as e:
        logger.error("Error broadcasting message to centrifugo: %s", e)
        return None