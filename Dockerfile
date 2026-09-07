FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend and frontend source files
COPY backend ./backend
COPY frontend ./frontend

# Expose server port
EXPOSE 8000

# Set environment variable for port
ENV PORT=8000

# Start command
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}
