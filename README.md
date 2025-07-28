# Oppuna Mental Health Assistant API

A FastAPI backend for the Oppuna mental health GenAI assistant, powered by Ollama.

## Prerequisites

- Python 3.11 or higher
- [Ollama](https://ollama.ai/) installed and running
- The `llama2-uncensored` model (or another model of your choice) pulled in Ollama
- [Milvus](https://milvus.io/) installed and running (for vector storage and semantic search)

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configure the application by creating or editing the `.env` file:
   ```
   # Ollama API configuration
   OLLAMA_API_URL=http://localhost:11434
   OLLAMA_MODEL=llama2-uncensored
   
   # API server configuration
   PORT=8000
   
   # Milvus configuration
   MILVUS_HOST=localhost
   MILVUS_PORT=19530
   MILVUS_COLLECTION=chat_memories
   ```

4. Start the Ollama service:
   ```bash
   ollama serve
   ```

5. In a separate terminal, pull the required model:
   ```bash
   ollama pull llama2-uncensored
   ```

6. Install and start Milvus:

   **Using Docker (recommended):**
   ```bash
   # Pull and start Milvus standalone
   docker run -d --name milvus_standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:v2.3.3 standalone
   ```

   **For other installation methods**, refer to the [Milvus documentation](https://milvus.io/docs/install_standalone-docker.md).

7. Start the API server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t oppuna-api .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8080 \
     -e OLLAMA_API_URL=http://host.docker.internal:11434 \
     -e MILVUS_HOST=host.docker.internal \
     -e MILVUS_PORT=19530 \
     oppuna-api
   ```

   Note: 
   - `host.docker.internal` is used to access services running on the host machine (both Ollama and Milvus in this case).
   - Adjust these URLs and ports based on your deployment setup.
   - If you're using Docker Compose with a Milvus service, use the service name (e.g., `milvus`) as the host.

## Troubleshooting Ollama Connection Issues

If you encounter errors like:

```
I apologize, but I'm currently unable to connect to my language model service. This could be because the service is not running or is experiencing issues.
```

Follow these steps to troubleshoot:

1. **Verify Ollama is running**:
   ```bash
   curl http://localhost:11434/api/tags
   ```
   This should return a JSON response with available models. If it fails, Ollama is not running or not accessible.

2. **Check if the model is available**:
   Run the test script to verify the connection and available models:
   ```bash
   python test_ollama_connection.py
   ```

3. **Update the Ollama API URL**:
   If Ollama is running on a different host or port, update the `OLLAMA_API_URL` in your `.env` file or set it as an environment variable.

4. **Check network connectivity**:
   - For local development: Ensure localhost connections are not blocked by a firewall
   - For Docker: Ensure the container can access the host network or the Ollama service
   - For remote deployments: Ensure the Ollama service is accessible from the API server

5. **Verify the model is pulled**:
   ```bash
   ollama list
   ```
   If your model is not listed, pull it:
   ```bash
   ollama pull llama2-uncensored  # or your preferred model
   ```

## Troubleshooting Milvus Connection Issues

If you encounter errors related to Milvus connection or vector storage, follow these steps:

1. **Verify Milvus is running**:
   ```bash
   # If using Docker
   docker ps | grep milvus
   
   # Test connection using curl
   curl http://localhost:9091/api/v1/health
   ```
   This should return a health status. If it fails, Milvus is not running or not accessible.

2. **Check Milvus logs**:
   ```bash
   # If using Docker
   docker logs milvus_standalone
   ```
   Look for any error messages that might indicate configuration or startup issues.

3. **Update the Milvus configuration**:
   If Milvus is running on a different host or port, update the environment variables in your `.env` file:
   ```
   MILVUS_HOST=your-milvus-host
   MILVUS_PORT=19530
   MILVUS_COLLECTION=chat_memories
   ```

4. **Check network connectivity**:
   - For local development: Ensure localhost connections are not blocked by a firewall
   - For Docker: Ensure the container can access the Milvus service
   - For remote deployments: Ensure the Milvus service is accessible from the API server

5. **Verify collection creation**:
   The application will automatically create the necessary collection and schema in Milvus on startup. If you need to manually verify or create the collection, you can use the Milvus Python client:
   ```python
   from pymilvus import connections, utility
   
   connections.connect(host="localhost", port="19530")
   print(utility.list_collections())
   ```

## API Endpoints

- `GET /`: Root endpoint, returns API information
- `POST /chat`: Chat endpoint, processes user messages and returns AI responses

### Chat Request Format

```json
{
  "user_input": "Your message here",
  "user_id": "unique_user_id"
}
```

### Chat Response Format

```json
{
  "reply": "AI response text",
  "crisis": false
}
```

The `crisis` field will be `true` if crisis indicators are detected in the user's message.

## License

[License information]