FROM python:3.14-slim

# Install uv package manager and ffmpeg (for Opus→Vorbis audio re-encoding)
RUN pip install --no-cache-dir uv && \
    apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifests first (layer cache)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application source
COPY *.py ./
COPY templates/ ./templates/
COPY static/ ./static/
COPY data/ ./data/

# Create runtime data directory for card store DB
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "main"]
