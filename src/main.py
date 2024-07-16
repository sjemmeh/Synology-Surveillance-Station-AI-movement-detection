from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import notifier
import syno_handler
import json

SETTINGS = json.load(open("settings.json"))


class Main(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Override to suppress logging - don't want to spam terminal.
        return

    def do_GET(self):
        # Parse the URL
        parsed_path = urlparse(self.path)

        # Extract the path
        path = parsed_path.path

        # Default message
        html_header = """<html><head><title>Syno Image parser</title><meta name="viewport" content="width=device-width, 
        initial-scale=1.0"></head><body>"""
        html_footer = """</body></html>"""
        message = """<p> Nothing to do. </p>"""

        # Remove slash from url
        camera_name = path[1:]

        # Check if the camera is present in settings
        if camera_name in SETTINGS["CAMERAS"]:
            if syno_handler.detect(camera_name):
                message = f"""<p> Request for {camera_name} successful. Conditions are true </p>"""
                for idx, method in enumerate(SETTINGS["NOTIFY_METHODS"]):  # Loop through notifiers
                    if camera_name in SETTINGS["NOTIFY_CAMERAS"][idx]: # Check if we want to notify for camera name
                        notifier.notify(method, SETTINGS["NOTIFY_DATA"][idx], syno_handler.last_image_name, camera_name)
                if SETTINGS["RECORD"]:
                    syno_handler.set_record_thread(SETTINGS["RECORD_TIME"], camera_name)
            else:
                message = f"""<p> Request for {camera_name} successful. Conditions are false </p>"""

        # Want to keep it more readable
        full_message = html_header + message + html_footer

        # Send response status code
        self.send_response(200)

        # Send headers
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        # Write message content
        self.wfile.write(bytes(full_message, "utf8"))

        return


def run(server_class=HTTPServer, handler_class=Main, port=SETTINGS["SERVER_PORT"]):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Creating synology session')
    syno_handler.create_syno_session()
    print(f'Starting httpd server on port {port}...')
    httpd.serve_forever()


if __name__ == "__main__":
    run()
