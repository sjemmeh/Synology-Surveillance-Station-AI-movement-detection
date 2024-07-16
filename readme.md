# Synology movement AI detection - WIP
### I tried multiple solutions, but none were working to my specification, so I decided to just write it myself
## Setup:
* Clone the repo
* Edit the settings.json file


* Docker:
  * Run the container

* Local:
  * Set up a [Codeproject AI server](https://www.codeproject.com)
  * Install the requirements
  * Run the main.py file

## Settings
|     Setting      |           Default Value            |                                                 Description                                                  |
|:----------------:|:----------------------------------:|:------------------------------------------------------------------------------------------------------------:|
|   SERVER_PORT    |                9999                |                                       HTTP port the server will run on                                       |
|     SYNO_IP      |                 -                  |                                              Synology server IP                                              |
|    SYNO_PORT     |                5001                |                                             Synology server port                                             |
|   SYNO_METHOD    |               HTTPS                |                                            Synology server method                                            |
|   SYNO_ACCOUNT   |                 -                  |                                                Synology user                                                 |
|  SYNO_PASSWORD   |                 -                  |                                              Synology Password                                               |
|      AI_IP       |                 -                  |                                           CodeProject AI Server IP                                           |
|     AI_PORT      |               32168                |                                          CodeProject AI Server Port                                          |
|     LOOK_FOR     |         ["cat", "person"]          | What to look for - [Supported objects](https://www.codeproject.com/AI/docs/api/api_reference.html#detection) | 
|     CAMERAS      |                 -                  |                              Camera names in the Synology Surveillance station                               |
|      DELAY       |                 0                  |                      Set a delay in case surveillance station sends a webhook too fast                       |
|      RECORD      |                True                |                             Calls a record on the synology surveillance station                              |
|   RECORD_TIME    |                 30                 |                         Amount of seconds you want to record after detecting motion                          | 
|  NOTIFY_METHODS  |      ["webhook", "telegram"]       |                                Currently supported methods: Webhook/Telegram                                 |
|   NOTIFY_DATA    |           ["OFF", "OFF"]           |                         In case of webhook: webhook full url. For telegram chat ID.                          |
|  NOTIFY_CAMERAS  | [["Camera_name"], ["Camera_name"]] |                                      Send notify if camera name is true                                      | 
| TELEGRAM_API_KEY |                 -                  |                                               Telegram API key                                               | 




If you want to add multiple telegram/webhook notifiers, you can add them to the lists:
```json
    "NOTIFY_METHODS": ["webhook", "telegram", "webhook"],
    "NOTIFY_DATA": ["URL", "00000", "URL"],
    "NOTIFY_CAMERAS": [["Example, Example2"], ["Example"], ["Example3"]],
```
Add a list item to NOTIFY_METHODS, and then add the url/chat id to the NOTIFY_DATA list. It will loop through these.