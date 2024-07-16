import requests
import json
import telepot
import logging

# Load settings
with open("settings.json") as settings_file:
    SETTINGS = json.load(settings_file)


def notify(method, data, image_file, camera_name, objects):
    """Handles notifications based on the specified method."""
    if data == "OFF":
        return

    try:
        if method == "webhook":
            url = data
            response = requests.post(url)
            response.raise_for_status()  # Raises an HTTPError for bad responses
        elif method == "telegram":
            bot = telepot.Bot(SETTINGS["TELEGRAM_API_KEY"])
            objects_str = ', '.join(objects)  # Join the objects into a single string separated by commas
            caption = f'Movement detected on camera "{camera_name}"! Found: {objects_str}'
            with open(image_file, 'rb') as photo:
                bot.sendPhoto(data, photo=photo, caption=caption)
    except requests.RequestException as e:
        logging.error(f"Failed to send webhook notification: {e}")
    except telepot.exception.TelegramError as e:
        logging.error(f"Failed to send Telegram notification: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
