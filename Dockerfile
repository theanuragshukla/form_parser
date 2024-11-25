FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
RUN pip install opencv-python-headless
COPY . .
EXPOSE 5000
CMD ["python3", "server.py"]
