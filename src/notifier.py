import requests


def notify(method, data):
    """Handles notifications"""
    if method == "webhook":
        url = data
        requests.post(url)
