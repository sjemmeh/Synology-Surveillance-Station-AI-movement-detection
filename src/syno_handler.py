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
current_recording_thread = None
stop_event = threading.Event()
thread_lock = threading.Lock()


def create_syno_session():
    """Gets a session ID"""
    login_url = base_url + "auth.cgi?api=SYNO.API.Auth&method=Login&version=6&account=" + SETTINGS[
        "SYNO_ACCOUNT"] + "&passwd=" + SETTINGS["SYNO_PASSWORD"] + "&session=SurveillanceStation&format=sid"
    response = requests.get(login_url)
    response.raise_for_status()
    data = response.json()
    if data['success']:
        return data['data']['sid']
    else:
        raise Exception("Login failed")


def destroy_syno_session(session_id):
    logout_url = f"{base_url}auth.cgi?api=SYNO.API.Auth&method=logout&version=2&session=SurveillanceStation&_sid={session_id}"
    response = requests.get(logout_url)
    response.raise_for_status()
    data = response.json()
    if not data['success']:
        raise Exception("Logout failed")


def get_camera_id(sid, camera_name):
    """Gets a camera ID."""
    camera_url = base_url + "entry.cgi?api=SYNO.SurveillanceStation.Camera&method=List&version=9&_sid=" + sid
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
    try:
        today = datetime.now()
        global last_image_name
        global camera_id

        session_id = create_syno_session()
        camera_id = get_camera_id(session_id, camera_name)

        # Save image to folder
        snapshot_url = base_url + f"entry.cgi?api=SYNO.SurveillanceStation.Camera&method=GetSnapshot&version=1&cameraId={camera_id}&_sid=" + session_id
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
    finally:
        destroy_syno_session(session_id)
        return filename


def perform_record_action(action, session_id):
    """Perform a recording action (start/stop)"""
    url = f"{base_url}entry.cgi?api=SYNO.SurveillanceStation.ExternalRecording&method=Record&version=2&cameraId={camera_id}&action={action}&_sid={session_id}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    if not data['success']:
        raise Exception(f"{action.capitalize()} action failed")


class StopRecordingException(Exception):
    """Custom exception to stop recording"""
    pass


def record_thread(seconds):
    """Create a recording thread"""
    session_id = create_syno_session()
    try:
        perform_record_action("start", session_id)
        start_time = time.time()
        while not stop_event.is_set() and time.time() - start_time < seconds:
            time.sleep(0.1)  # Sleep for a short time to allow for a quick check of the stop event

        if stop_event.is_set():
            raise StopRecordingException("Stop event set, stopping function")

        perform_record_action("stop", session_id)
        print("Recording stopped")
    except StopRecordingException as e:
        print(e)
    finally:
        destroy_syno_session(session_id)


def set_record_thread(seconds):
    """Create a thread to start camera recording"""
    global current_recording_thread
    with thread_lock:
        if current_recording_thread is not None and current_recording_thread.is_alive():
            print("Stopping existing recording thread")
            stop_event.set()  # Signal the current thread to stop
            current_recording_thread.join()  # Wait for the existing thread to finish
        stop_event.clear()  # Clear the stop event for the new thread
        current_recording_thread = threading.Thread(target=record_thread, args=(seconds,))
        current_recording_thread.start()
        print("New recording thread started")
