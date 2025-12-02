FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (ffmpeg for audio conversion)
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN uv pip install --system -r requirements.txt

# Copy project files
COPY agents ./agents
COPY migrations ./migrations
COPY static ./static
COPY scripts ./scripts

# Create required directories
RUN mkdir -p logs data static/audio

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "🚀 Starting DesiYatra Agent System"\n\
echo "✅ Starting API server..."\n\
exec uvicorn agents.main:app --host 0.0.0.0 --port 8000' > /app/entrypoint.sh && \
chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
