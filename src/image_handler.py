import requests
from datetime import datetime
import os
import json
import time


SETTINGS = json.load(open("settings.json"))
last_image_name = ""

def detect(camera_name):
    """Check image for specified object"""
    time.sleep(SETTINGS["DELAY"])
    image_data = open(get_image(camera_name), "rb").read()
    URL = "http://" + SETTINGS["AI_IP"] + ":" + SETTINGS["AI_PORT"] + "/v1/vision/detection"
    response = requests.post(URL,
                             files={"image": image_data}).json()
    objects_detected = []
    for detected in response["predictions"]:
        objects_detected.append(detected["label"])

    for item in objects_detected:
        if item in SETTINGS["LOOK_FOR"]:
            return True
    else:
        return False


def get_image(camera_name):
    today = datetime.now()
    """Get image from synology API"""
    camera_id = 0
    global last_image_name

    # Set synology URL
    base_url = SETTINGS["SYNO_METHOD"] + "://" + SETTINGS["SYNO_IP"] + ":" + SETTINGS["SYNO_PORT"] +"/webapi/"
    auth_url = base_url + "auth.cgi?api=SYNO.API.Auth&method=Login&version=6"

    # Initiate API call
    response = requests.get(auth_url, params=SETTINGS)
    auth_data = response.json()

    # Check if connection is successful
    if auth_data['success']:
        sid = auth_data['data']['sid']
    else:
        raise Exception("Authentication failed")

    # Start to get camera ID for the given name
    camera_url = base_url + "entry.cgi?api=SYNO.SurveillanceStation.Camera&method=List&version=9&_sid=" + sid
    response = requests.get(camera_url)
    camera_data = response.json()

    # Get camera id
    if camera_data['success']:
        cameras = camera_data['data']['cameras']
        for camera in cameras:
            if camera['newName'] == camera_name:
                camera_id = camera['id']
    else:
        raise Exception("Failed to retrieve camera list")

    # Save image to folder
    snapshot_url = base_url + f"entry.cgi?api=SYNO.SurveillanceStation.Camera&method=GetSnapshot&version=1&cameraId={camera_id}&_sid=" + sid
    response = requests.get(snapshot_url, stream=True)
    if response.status_code == 200:
        directory = "images/" + today.strftime("%Y") + "/" + today.strftime("%B") + "/" + today.strftime(
            "%d")  # Year/Month/Date/time.jpg
        os.makedirs(directory, exist_ok=True)  # Create dir if it doesn't exist

        filename = directory + "/" + today.strftime("%H-%M-%S") + ".jpg"
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        print(f"Snapshot saved as {filename}")
        last_image_name = filename
    else:
        raise Exception("Failed to capture snapshot")
    # Return the file name
    return filename
