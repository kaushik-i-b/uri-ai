FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    # Configure Ollama API - adjust these values for your deployment
    # For Docker Compose, use the service name: http://ollama:11434
    # For external Ollama service, use the appropriate URL
    OLLAMA_API_URL=http://host.docker.internal:11434 \
    OLLAMA_MODEL=llama2-uncensored \
    # Configure Milvus - adjust these values for your deployment
    # For Docker Compose, use the service name: milvus
    # For external Milvus service, use the appropriate host
    MILVUS_HOST=host.docker.internal \
    MILVUS_PORT=19530 \
    MILVUS_COLLECTION=chat_memories

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
CMD uvicorn main:app --host 0.0.0.0 --port $PORT