FROM python:3.11-slim

WORKDIR /app

# 1. Install system dependencies required for OpenCV and MySQL
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy application code
COPY . .

# 4. Run the application
# We use 'python webcode.py' because your app.run() is inside that file
CMD ["python", "webcode.py"]