import asyncio
import os
from dotenv import load_dotenv
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_ollama_connection():
    """Test the connection to the Ollama API."""
    # Get the Ollama API URL from environment variable
    base_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama2-uncensored")
    
    logger.info(f"Testing connection to Ollama API at {base_url} using model {model}")
    
    # Endpoint for model info
    models_endpoint = f"{base_url}/api/tags"
    
    try:
        async with httpx.AsyncClient() as client:
            # Test connection to models endpoint
            logger.info(f"Sending request to {models_endpoint}")
            response = await client.get(models_endpoint, timeout=10.0)
            
            if response.status_code == 200:
                logger.info("Successfully connected to Ollama API!")
                models = response.json()
                logger.info(f"Available models: {models}")
                
                # Check if our model is available
                model_names = [model_info.get('name') for model_info in models.get('models', [])]
                if model in model_names:
                    logger.info(f"Model '{model}' is available!")
                else:
                    logger.warning(f"Model '{model}' is not available. Available models: {model_names}")
            else:
                logger.error(f"Failed to connect to Ollama API. Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
    
    except httpx.ConnectError as e:
        logger.error(f"Connection error to Ollama API: {str(e)}")
        logger.error("Please check if the Ollama service is running and accessible at the configured URL.")
        logger.error("You can update the OLLAMA_API_URL in the .env file to point to the correct URL.")
    
    except Exception as e:
        logger.error(f"Error testing Ollama connection: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_ollama_connection())