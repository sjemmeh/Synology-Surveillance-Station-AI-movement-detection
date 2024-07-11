# Synology movement AI detection - WIP
### I tried multiple solutions, but none were working to my specification, so I decided to just write it myself
## Setup:
* Docker:
  * Edit the settings.json file
  * Run the container

* Local:
  * Set up a [Codeproject AI server](https://www.codeproject.com)
  * Edit the settings.json file
  * Install the requirements
  * Run the main.py file

## Setting up
```json
    "SYNO_IP": "", - Synology server IP
    "SYNO_PORT": "5001", - Synology server port
    "SYNO_METHOD": "https", - Synology server method
    "account": "", - Synology user
    "passwd": "", - Synology Password
    
    "AI_IP": "", - CodeProject AI Server IP
    "AI_PORT": "32168", - CodeProject AI Server Port
    
    "LOOK_FOR": ["cat", "person"], - What to look for - For the full list check the link below
    "CAMERAS": [""], - Camera names in the Synology Surveillance station
    "DELAY": 0, - Set a delay in case surveillance station sends a webhook too fast
    
    "NOTIFY_METHODS": ["webhook", "telegram"], - Currently supported methods, can add more. Make sure to reflect changes below too.
    "NOTIFY_DATA": ["OFF", "OFF"], - In case of webhook: webhook full url. For telegram chat ID.

    "TELEGRAM_API_KEY": ""
```
[Supported objects](https://www.codeproject.com/AI/docs/api/api_reference.html#detection)

If you want to add multiple telegram/webhook notifiers, you can add them to the lists:
```json
    "NOTIFY_METHODS": ["webhook", "telegram", "webhook"],
    "NOTIFY_DATA": ["URL", "00000", "URL"]
```
Add a list item to NOTIFY_METHODS, and then add the url/chatid to the NOTIFY_DATA list. It will loop through these.