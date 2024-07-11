FROM python:latest

# Set work dir
WORKDIR /src

# Copy requirements
COPY requirements.txt /requirements.txt

# Install requirements
RUN pip install -r /requirements.txt

CMD [ "python", "./main.py"]
