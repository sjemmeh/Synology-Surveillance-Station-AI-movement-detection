import requests
import json
import telepot
import logging


class Notifier:
    def __init__(self, input_file):
        with open(input_file) as settings_file:
            self.SETTINGS = json.load(settings_file)
        self.DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks"

    def notify(self, method, data, image_file, camera_name, objects):
        """Handles notifications based on the specified method."""
        try:
            objects_str = ', '.join(objects)  # Join the objects into a single string separated by commas
            caption = f'Movement detected at {camera_name}! Found: {objects_str}'

            if method == "webhook":
                if data.startswith(self.DISCORD_WEBHOOK_URL):
                    with open(image_file, 'rb') as photo:
                        payload = {"content": caption}
                        files = {'file': photo}
                        response = requests.post(data, data=payload, files=files)
                        response.raise_for_status()
                else:
                    url = data
                    response = requests.post(url)
                    response.raise_for_status()  # Raises an HTTPError for bad responses
            elif method == "telegram":
                bot = telepot.Bot(self.SETTINGS["TELEGRAM_API_KEY"])
                with open(image_file, 'rb') as photo:
                    bot.sendPhoto(data, photo=photo, caption=caption)

        except requests.RequestException as e:
            logging.error(f"Failed to send webhook notification: {e}")
        except telepot.exception.TelegramError as e:
            logging.error(f"Failed to send Telegram notification: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
