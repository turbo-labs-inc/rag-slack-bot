FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY README.md .

# Install uv for fast Python package management
RUN pip install uv

# Install dependencies
RUN uv pip install --system -e .

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Create necessary directories
RUN mkdir -p /app/credentials /app/logs

# Set Python path
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "-m", "app.main"]