import requests
import json
import telepot

SETTINGS = json.load(open("settings.json"))


def notify(method, data, image_file, camera_name):
    """Handles notifications"""
    if data != "OFF":
        if method == "webhook":
            url = data
            requests.post(url)
        if method == "telegram":
            bot = telepot.Bot(SETTINGS["TELEGRAM_API_KEY"])
            # Send a photo to the Telegram chat
            caption = f'Movement detected on camera "{camera_name}"!'
            bot.sendPhoto(data, photo=open(image_file, 'rb'), caption=caption)
