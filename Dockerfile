FROM python:latest

# Set work dir
WORKDIR /src

# Install requirements
RUN pip install requests

CMD [ "python", "./main.py"]
