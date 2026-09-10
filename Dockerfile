# Production Dockerfile for MedIntel Platform
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and data
COPY src/ ./src/
COPY data/ ./data/

ENV PYTHONPATH=/app/src
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn medintel_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
