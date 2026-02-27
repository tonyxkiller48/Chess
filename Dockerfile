# Use slim Python image
FROM python:3.11-slim

# Install stockfish + system deps
RUN apt-get update && \
    apt-get install -y stockfish && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port for Flask (Render auto assigns $PORT)
ENV PORT=10000

# Run the bot
CMD ["python", "main.py"]
