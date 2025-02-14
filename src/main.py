from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import json
from notifier import Notifier
import logging
from syno_handler import Synology

SETTINGS_FILE = "settings.json"
# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load settings
with open(SETTINGS_FILE) as file:
    SETTINGS = json.load(file)

synology = Synology(SETTINGS_FILE)
notifier = Notifier(SETTINGS_FILE)


class MainHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Override to suppress logging
        pass

    def do_GET(self):
        # Parse the URL and extract the path
        parsed_path = urlparse(self.path)
        camera_name = parsed_path.path.lstrip('/')

        # Default HTML response
        html_header = (
            "<html><head><title>Syno Image parser</title>"
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'></head><body>"
        )
        html_footer = "</body></html>"
        message = "<p> Nothing to do. </p>"

        # Check if the camera is present in settings
        if camera_name in SETTINGS["CAMERAS"]:
            if synology.detect(camera_name):
                message = f"<p> Request for {camera_name} successful. Conditions are true </p>"
                for idx, method in enumerate(SETTINGS["NOTIFY_METHODS"]):
                    if camera_name in SETTINGS["NOTIFY_CAMERAS"][idx]:
                        notifier.notify(
                            method,
                            SETTINGS["NOTIFY_DATA"][idx],
                            synology.last_image_name,
                            camera_name, synology.found_objects,
                        )
                if SETTINGS["RECORD"]:
                    synology.set_record_thread(SETTINGS["RECORD_TIME"], camera_name)
            else:
                message = f"<p> Request for {camera_name} successful. Conditions are false </p>"
        full_message = html_header + message + html_footer

        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(full_message.encode("utf8"))


def run(server_class=HTTPServer, handler_class=MainHandler, port=SETTINGS["SERVER_PORT"]):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Creating synology session')
    synology.create_syno_session()
    logging.info(f'Starting HTTP server on port {port}...')
    httpd.serve_forever()


if __name__ == "__main__":
    run()
