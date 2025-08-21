FROM python:3.13-slim

WORKDIR /src

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port the app runs on
EXPOSE 80

CMD ["fastapi", "dev", "./src/main.py", "--no-access-log", "--log-level", "info", "--port", "80", "--proxy-headers"]
