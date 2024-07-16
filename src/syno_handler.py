import requests
from datetime import datetime
import os
import json
import time
import threading

SETTINGS = json.load(open("settings.json"))
last_image_name = ""
base_url = SETTINGS["SYNO_METHOD"] + "://" + SETTINGS["SYNO_IP"] + ":" + SETTINGS["SYNO_PORT"] + "/webapi/"
camera_id = 0
global_sid = ""
# Global variables
camera_threads = {}  # Dictionary to store camera threads
thread_locks = {}  # Dictionary to store locks for each camera thread
stop_events = {}  # Dictionary to store stop events for each camera


def create_syno_session():
    global global_sid
    """Gets a session ID"""
    login_url = base_url + "auth.cgi?api=SYNO.API.Auth&method=Login&version=6&account=" + SETTINGS[
        "SYNO_ACCOUNT"] + "&passwd=" + SETTINGS["SYNO_PASSWORD"] + "&session=SurveillanceStation&format=sid"
    response = requests.get(login_url)
    response.raise_for_status()
    data = response.json()
    if data['success']:
        global_sid = data['data']['sid']
    else:
        raise Exception("Login failed")


def get_camera_id(camera_name):
    """Gets a camera ID."""
    camera_url = base_url + "entry.cgi?api=SYNO.SurveillanceStation.Camera&method=List&version=9&_sid=" + global_sid
    response = requests.get(camera_url)
    camera_data = response.json()

    # Get camera id
    if camera_data['success']:
        cameras = camera_data['data']['cameras']
        for camera in cameras:
            if camera['newName'] == camera_name:
                return camera['id']
    else:
        raise Exception("Failed to retrieve camera list")


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
        os.remove(last_image_name)
        return False


def get_image(camera_name):
    """Get image from synology API"""

    today = datetime.now()
    global last_image_name
    global camera_id

    camera_id = get_camera_id(camera_name)

    # Save image to folder
    snapshot_url = base_url + f"entry.cgi?api=SYNO.SurveillanceStation.Camera&method=GetSnapshot&version=1&cameraId={camera_id}&_sid=" + global_sid
    response = requests.get(snapshot_url, stream=True)
    if response.status_code == 200:
        directory = "images/" + camera_name + "/" + today.strftime("%Y") + "/" + today.strftime(
            "%B") + "/" + today.strftime(
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
    return filename


def perform_record_action(action, camera_id):
    """Perform a recording action (start/stop)"""
    url = f"{base_url}entry.cgi?api=SYNO.SurveillanceStation.ExternalRecording&method=Record&version=2&cameraId={camera_id}&action={action}&_sid={global_sid}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    if not data['success']:
        raise Exception(f"{action.capitalize()} action failed")


class StopRecordingException(Exception):
    """Custom exception to stop recording"""
    pass


def record_thread(seconds, camera_id, stop_event):
    """Create a recording thread"""
    try:
        perform_record_action("start", camera_id)
        start_time = time.time()
        while not stop_event.is_set() and time.time() - start_time < seconds:
            time.sleep(0.1)  # Sleep for a short time to allow for a quick check of the stop event

        if stop_event.is_set():
            raise StopRecordingException("Stop event set, stopping function")

        perform_record_action("stop", camera_id)
        print(f"Recording on camera {camera_id} stopped normally")
    except StopRecordingException as e:
        perform_record_action("stop", camera_id)
        print(f"Recording on camera {camera_id} stopped due to stop event: {e}")


def set_record_thread(seconds, camera_name):
    """Create a thread to start camera recording"""
    camera_id = get_camera_id(camera_name)

    if camera_name not in thread_locks:
        thread_locks[camera_name] = threading.Lock()

    with thread_locks[camera_name]:
        if camera_name in camera_threads and camera_threads[camera_name].is_alive():
            print(f"Stopping existing recording thread for camera {camera_name}")
            stop_events[camera_name].set()  # Signal the current thread to stop
            camera_threads[camera_name].join()  # Wait for the existing thread to finish

        stop_events[camera_name] = threading.Event()  # Create a new stop event for the new thread
        camera_threads[camera_name] = threading.Thread(target=record_thread,
                                                       args=(seconds, camera_id, stop_events[camera_name]))
        camera_threads[camera_name].start()
        print(f"New recording thread started for camera {camera_name}")
