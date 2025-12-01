FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY agents ./agents
COPY migrations ./migrations

# Install dependencies
RUN uv pip install --system -e . google-cloud-firestore google-cloud-aiplatform

# Create logs directory
RUN mkdir -p logs data

# Copy initialization scripts


# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "🚀 Starting DesiYatra Agent System"\n\
echo "✅ Starting API server..."\n\
exec uvicorn agents.main:app --host 0.0.0.0 --port 8000' > /app/entrypoint.sh && \
chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

