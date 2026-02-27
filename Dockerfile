FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y stockfish libcairo2 libpangocairo-1.0-0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=10000

CMD ["python", "main.py"]
