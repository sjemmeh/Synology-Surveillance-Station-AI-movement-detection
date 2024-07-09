import requests


def detect(image, label):
    """Check image for specified object"""
    image_data = open(image, "rb").read()
    response = requests.post("http://192.168.0.5:32168/v1/vision/detection",
                             files={"image": image_data}).json()
    objects_detected = []
    for detected in response["predictions"]:
        objects_detected.append(detected["label"])
    if label in objects_detected:
        return True
    else:
        return False

print(detect("images/kite.jpg", "dog"))
