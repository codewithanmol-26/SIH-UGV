FROM python:3.12-slim

# OpenCV needs these system libs even in headless environments.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY models/ /app/models/
COPY sample_data/ /app/sample_data/

EXPOSE 8000
CMD ["python", "main.py"]
