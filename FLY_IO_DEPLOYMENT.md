# Fly.io Deployment Guide

## Issue Resolution: 503 Service Unavailable

This document explains the changes made to fix the 503 Service Unavailable error on Fly.io and provides recommendations for future deployments.

### Root Cause

The application was failing to start on Fly.io due to connectivity issues with external services:

1. **Milvus Vector Database**: The application was configured to connect to a Milvus instance at "milvus-host:19530", which was a placeholder value and not a valid hostname.

2. **Ollama API**: The application was configured to connect to an Ollama API at "ollama-host:11434", which was also a placeholder value and not a valid hostname.

While the application has a fallback mechanism for Milvus (using in-memory storage), it did not have a similar fallback for the Ollama API, causing the application to fail to start when deployed to Fly.io.

### Changes Made

1. **Updated fly.toml Configuration**:
   - Set MILVUS_HOST to an empty string to trigger the in-memory fallback mechanism
   - Added ENABLE_FALLBACK_MODE flag to indicate that the application should gracefully degrade when services are unavailable

2. **Enhanced OllamaClient with Fallback Mode**:
   - Added fallback mode detection based on the ENABLE_FALLBACK_MODE environment variable
   - Implemented fallback response generation for all three methods:
     - generate_response: Returns predefined supportive responses
     - generate_follow_up_suggestions: Returns default follow-up questions
     - generate_suggestions: Returns input-specific default suggestions

3. **Improved Error Handling**:
   - Added specific handling for connection errors
   - Added more detailed logging for different error scenarios
   - Ensured the application can start and serve basic functionality even when external services are unavailable

### Deployment Recommendations

For production deployments on Fly.io, consider the following options:

#### Option 1: Use External Services (Recommended for Production)

1. **Deploy Milvus**:
   - Deploy Milvus on a separate service (e.g., Zilliz Cloud, AWS, GCP)
   - Update the MILVUS_HOST, MILVUS_PORT, and MILVUS_COLLECTION environment variables in fly.toml

2. **Deploy Ollama**:
   - Deploy Ollama on a separate service or use a managed LLM API service
   - Update the OLLAMA_API_URL and OLLAMA_MODEL environment variables in fly.toml
   - Ensure the API endpoint is accessible from the Fly.io application

3. **Disable Fallback Mode**:
   - Set ENABLE_FALLBACK_MODE to "false" in fly.toml

#### Option 2: Use Fallback Mode (Recommended for Testing/Development)

1. **Enable Fallback Mode**:
   - Set ENABLE_FALLBACK_MODE to "true" in fly.toml
   - Set MILVUS_HOST to an empty string to use in-memory storage

2. **Limitations**:
   - In-memory storage will not persist between restarts
   - Responses will be limited to predefined fallback messages
   - Autocomplete suggestions will be generic

### Monitoring and Maintenance

1. **Monitor Logs**:
   - Check application logs for connectivity issues with external services
   - Look for log messages indicating fallback mode is active

2. **Health Checks**:
   - Implement a health check endpoint that reports the status of external services
   - Configure Fly.io to use this endpoint for health checks

3. **Scaling Considerations**:
   - When using in-memory storage, be aware that each instance will have its own separate memory store
   - Consider using a shared cache service (e.g., Redis) for better scalability

### Conclusion

The changes made allow the application to start and function on Fly.io even when external services are unavailable, resolving the 503 Service Unavailable error. For optimal performance and functionality, it is recommended to deploy and configure the required external services (Milvus and Ollama) and update the environment variables accordingly.

## Issue Resolution: Connection Refused Error

This section explains the changes made to fix the connection refused error on Fly.io.

### Root Cause

The application was failing to accept connections on Fly.io with the following error:

```
instance refused connection. is your app listening on 0.0.0.0:8080? make sure it is not only listening on 127.0.0.1
```

This error occurs when the application is only listening on localhost (127.0.0.1) instead of all available network interfaces (0.0.0.0), or when there's a port mismatch between what Fly.io expects (8080) and what the application is using.

### Changes Made

1. **Updated .dockerignore**:
   - Removed fly.toml from the excluded files to ensure the application has access to the correct PORT setting when deployed

2. **Updated .env File**:
   - Changed PORT from 8000 to 8080 to be consistent with the Dockerfile and fly.toml

3. **Enhanced main.py**:
   - Added a main block that explicitly starts the server on 0.0.0.0:8080 when the application is run directly
   - This ensures the application listens on all network interfaces and the correct port, regardless of how it's started

### Deployment Recommendations

When deploying to Fly.io, ensure that:

1. **Consistent Port Configuration**:
   - The PORT environment variable is set to 8080 in all configuration files (Dockerfile, fly.toml, .env)
   - The application is configured to listen on 0.0.0.0:8080

2. **Proper File Inclusion**:
   - The .dockerignore file does not exclude important configuration files like fly.toml

3. **Explicit Host Binding**:
   - The application explicitly binds to 0.0.0.0 (all network interfaces) rather than the default 127.0.0.1 (localhost only)

These changes ensure that the application is accessible from outside the container, which is essential for Fly.io deployments.