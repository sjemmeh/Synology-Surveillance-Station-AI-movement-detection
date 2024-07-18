import requests
from datetime import datetime
import os
import json
import time
import threading
import logging


class Synology:
    def __init__(self, input_file):
        with open(input_file) as settings_file:
            self.SETTINGS = json.load(settings_file)

        self.base_url = (
            f"{self.SETTINGS['SYNO_METHOD']}://{self.SETTINGS['SYNO_IP']}:{self.SETTINGS['SYNO_PORT']}/webapi/"
        )
        self.global_sid = ""
        self.camera_threads = {}
        self.thread_locks = {}
        self.stop_events = {}
        self.found_objects = []

        self.last_image_name = ""

    def create_syno_session(self):
        """Gets a session ID"""
        login_url = (
                self.base_url + "auth.cgi?api=SYNO.API.Auth&method=Login&version=6"
                                f"&account={self.SETTINGS['SYNO_ACCOUNT']}&passwd={self.SETTINGS['SYNO_PASSWORD']}"
                                "&session=SurveillanceStation&format=sid"
        )
        try:
            response = requests.get(login_url)
            response.raise_for_status()
            data = response.json()
            if data['success']:
                self.global_sid = data['data']['sid']
            else:
                raise Exception("Login failed")
        except requests.RequestException as e:
            logging.error(f"Failed to create Synology session: {e}")
            raise

    def get_camera_id(self, camera_name):
        """Gets a camera ID."""
        camera_url = (
            f"{self.base_url}entry.cgi?api=SYNO.SurveillanceStation.Camera&method=List&version=9"
            f"&_sid={self.global_sid}"
        )
        try:
            response = requests.get(camera_url)
            response.raise_for_status()
            camera_data = response.json()
            if camera_data['success']:
                for camera in camera_data['data']['cameras']:
                    if camera['newName'] == camera_name:
                        return camera['id']
            raise Exception("Failed to retrieve camera list or camera not found")
        except requests.RequestException as e:
            logging.error(f"Failed to get camera ID for {camera_name}: {e}")
            raise

    def detect(self, camera_name):
        """Get an image from a camera and check for objects"""
        time.sleep(self.SETTINGS["DELAY"])

        try:
            image_file = self.get_image(camera_name)
        except Exception as e:
            logging.error(f"Failed to get image from camera {camera_name}: {e}")
            return False

        try:
            with open(image_file, "rb") as image_data:
                url = f"http://{self.SETTINGS['AI_IP']}:{self.SETTINGS['AI_PORT']}/v1/vision/detection"
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

        self.found_objects.clear()
        self.found_objects.extend(
            o for o in objects_detected if o not in self.found_objects and o in self.SETTINGS["LOOK_FOR"]
        )

        if any(item in self.SETTINGS["LOOK_FOR"] for item in objects_detected):
            return True
        else:
            os.remove(image_file)
            return False

    def get_image(self, camera_name):
        """Get image from Synology API for the specified camera."""
        today = datetime.now()
        camera_id = self.get_camera_id(camera_name)

        snapshot_url = (
            f"{self.base_url}entry.cgi?api=SYNO.SurveillanceStation.Camera&method=GetSnapshot"
            f"&version=1&cameraId={camera_id}&_sid={self.global_sid}"
        )

        try:
            response = requests.get(snapshot_url, stream=True)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Failed to get snapshot from camera {camera_name}: {e}")
            return None

        directory = os.path.join("images", camera_name, today.strftime("%Y"), today.strftime("%B"),
                                 today.strftime("%d"))
        os.makedirs(directory, exist_ok=True)
        filename = os.path.join(directory, f"{today.strftime('%H-%M-%S')}.jpg")

        try:
            with open(filename, 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            logging.info(f"Snapshot saved as {filename}")
            self.last_image_name = filename
        except Exception as e:
            logging.error(f"Failed to save snapshot to {filename}: {e}")
            return None

        return filename

    def perform_record_action(self, action, camera_id):
        """Perform a recording action (start/stop) for a given camera ID"""
        url = (
            f"{self.base_url}entry.cgi?api=SYNO.SurveillanceStation.ExternalRecording&method=Record&version=2"
            f"&cameraId={camera_id}&action={action}&_sid={self.global_sid}"
        )
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if not data['success']:
                raise Exception(f"{action.capitalize()} action failed")
        except requests.RequestException as e:
            logging.error(f"Failed to perform recording action '{action}' for camera {camera_id}: {e}")
            raise

    def record_thread(self, seconds, camera_id, stop_event):
        """Create a recording thread"""
        try:
            self.perform_record_action("start", camera_id)
            start_time = time.time()
            while not stop_event.is_set() and time.time() - start_time < seconds:
                time.sleep(0.1)  # Allow for a quick check of the stop event

            if stop_event.is_set():
                raise StopRecordingException("Stop event set, stopping function")

            self.perform_record_action("stop", camera_id)
            logging.info(f"Recording on camera {camera_id} stopped normally")
        except StopRecordingException as e:
            self.perform_record_action("stop", camera_id)
            logging.info(f"Recording on camera {camera_id} stopped due to stop event: {e}")

    def set_record_thread(self, seconds, camera_name):
        """Create a thread to start camera recording"""
        camera_id = self.get_camera_id(camera_name)

        if camera_name not in self.thread_locks:
            self.thread_locks[camera_name] = threading.Lock()

        with self.thread_locks[camera_name]:
            if camera_name in self.camera_threads and self.camera_threads[camera_name].is_alive():
                logging.info(f"Stopping existing recording thread for camera {camera_name}")
                self.stop_events[camera_name].set()  # Signal the current thread to stop
                self.camera_threads[camera_name].join()  # Wait for the existing thread to finish

            self.stop_events[camera_name] = threading.Event()  # Create a new stop event for the new thread
            self.camera_threads[camera_name] = threading.Thread(
                target=self.record_thread, args=(seconds, camera_id, self.stop_events[camera_name])
            )
            self.camera_threads[camera_name].start()
            logging.info(f"New recording thread started for camera {camera_name}")


class StopRecordingException(Exception):
    """Custom exception to stop recording"""
    pass
