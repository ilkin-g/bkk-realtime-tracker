FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN pip install requests gtfs_realtime_bindings python-dotenv

CMD ["python", "-u", "main.py"]