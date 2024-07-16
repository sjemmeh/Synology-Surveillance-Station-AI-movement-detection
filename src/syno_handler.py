import requests
from datetime import datetime
import os
import json
import time
import threading
import logging

# Load settings
with open("settings.json") as settings_file:
    SETTINGS = json.load(settings_file)

# Global variables
last_image_name = ""
base_url = f"{SETTINGS['SYNO_METHOD']}://{SETTINGS['SYNO_IP']}:{SETTINGS['SYNO_PORT']}/webapi/"
global_sid = ""
camera_threads = {}  # Dictionary to store camera threads
thread_locks = {}  # Dictionary to store locks for each camera thread
stop_events = {}  # Dictionary to store stop events for each camera

filtered_objects = []

#TODO: Remove usage of globals - Create proper classes.

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
    camera_url = f"{base_url}entry.cgi?api=SYNO.SurveillanceStation.Camera&method=List&version=9&_sid={global_sid}"
    response = requests.get(camera_url)
    response.raise_for_status()
    camera_data = response.json()

    if camera_data['success']:
        for camera in camera_data['data']['cameras']:
            if camera['newName'] == camera_name:
                return camera['id']
    raise Exception("Failed to retrieve camera list or camera not found")


def detect(camera_name):
    """Get an image from a camera and check for objects"""
    time.sleep(SETTINGS["DELAY"])
    global filtered_objects

    try:
        image_file = get_image(camera_name)
    except Exception as e:
        logging.error(f"Failed to get image from camera {camera_name}: {e}")
        return False

    try:
        with open(image_file, "rb") as image_data:
            url = f"http://{SETTINGS['AI_IP']}:{SETTINGS['AI_PORT']}/v1/vision/detection"
            response = requests.post(url, files={"image": image_data})
            response.raise_for_status()
            response_data = response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to send image to AI server: {e}")
        return False
    except Exception as e:
        logging.error(f"Error reading image file: {e}")
        return False

    objects_detected = [detected["label"] for detected in response_data.get("predictions", [])]

    filtered_objects.extend(o for o in objects_detected if o not in filtered_objects and o in SETTINGS["LOOK_FOR"])

    if any(item in SETTINGS["LOOK_FOR"] for item in objects_detected):
        return True
    else:
        os.remove(image_file)
        return False


def get_image(camera_name):
    global last_image_name
    """Get image from Synology API for the specified camera."""
    today = datetime.now()
    camera_id = get_camera_id(camera_name)

    snapshot_url = (
        f"{base_url}entry.cgi?api=SYNO.SurveillanceStation.Camera&method=GetSnapshot"
        f"&version=1&cameraId={camera_id}&_sid={global_sid}"
    )

    try:
        response = requests.get(snapshot_url, stream=True)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Failed to get snapshot from camera {camera_name}: {e}")
        return None

    directory = os.path.join("images", camera_name, today.strftime("%Y"), today.strftime("%B"), today.strftime("%d"))
    os.makedirs(directory, exist_ok=True)
    filename = os.path.join(directory, f"{today.strftime('%H-%M-%S')}.jpg")

    try:
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        logging.info(f"Snapshot saved as {filename}")
    except Exception as e:
        logging.error(f"Failed to save snapshot to {filename}: {e}")
        return None
    last_image_name = filename
    return filename


def perform_record_action(action, camera_id):
    """Perform a recording action (start/stop) for a given camera ID"""
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
            time.sleep(0.1)  # Allow for a quick check of the stop event

        if stop_event.is_set():
            raise StopRecordingException("Stop event set, stopping function")

        perform_record_action("stop", camera_id)
        logging.info(f"Recording on camera {camera_id} stopped normally")
    except StopRecordingException as e:
        perform_record_action("stop", camera_id)
        logging.info(f"Recording on camera {camera_id} stopped due to stop event: {e}")


def set_record_thread(seconds, camera_name):
    """Create a thread to start camera recording"""
    camera_id = get_camera_id(camera_name)

    if camera_name not in thread_locks:
        thread_locks[camera_name] = threading.Lock()

    with thread_locks[camera_name]:
        if camera_name in camera_threads and camera_threads[camera_name].is_alive():
            logging.info(f"Stopping existing recording thread for camera {camera_name}")
            stop_events[camera_name].set()  # Signal the current thread to stop
            camera_threads[camera_name].join()  # Wait for the existing thread to finish

        stop_events[camera_name] = threading.Event()  # Create a new stop event for the new thread
        camera_threads[camera_name] = threading.Thread(
            target=record_thread, args=(seconds, camera_id, stop_events[camera_name])
        )
        camera_threads[camera_name].start()
        logging.info(f"New recording thread started for camera {camera_name}")
