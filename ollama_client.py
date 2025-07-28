import httpx
import logging
import os
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaClient:
    """Client for interacting with Ollama's LLaMA2 model."""
    
    def __init__(self, base_url: str = None):
        """
        Initialize the Ollama client.
        
        Args:
            base_url: The base URL for the Ollama API
        """
        # Get base_url from environment variable or use default
        self.base_url = base_url or os.getenv("OLLAMA_API_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama2-uncensored")  # Get model from env or use default
        self.generate_endpoint = f"{self.base_url}/api/generate"
        logger.info(f"Initialized OllamaClient with base_url: {self.base_url}, model: {self.model}")
        
    async def generate_response(self, user_input: str, user_id: str) -> str:
        """
        Generate a response from the Ollama LLaMA2 model.
        
        Args:
            user_input: The user's message
            user_id: The unique identifier for the user
            
        Returns:
            The model's response as a string
        """
        try:
            # Prepare the request payload
            payload = {
                "model": self.model,
                "prompt": user_input,
                "stream": False,
                # Optional: Add system prompt for mental health context
                "system": "You are Oppuna, a compassionate mental health assistant. Provide supportive, empathetic responses. Never encourage harmful behavior."
            }
            
            # Add user context if needed
            # This could be expanded to include conversation history
            metadata = {"user_id": user_id}
            
            logger.info(f"Sending request to Ollama API for user {user_id}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.generate_endpoint,
                    json=payload,
                    timeout=60.0  # Longer timeout for LLM generation
                )
                
                if response.status_code != 200:
                    logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                    return "I'm sorry, I'm having trouble processing your request right now."
                
                result = response.json()
                return result.get("response", "")
                
        except httpx.ConnectError as e:
            logger.error(f"Connection error to Ollama API: {str(e)}")
            logger.error(f"Attempted to connect to: {self.generate_endpoint}")
            logger.error("Please check if Ollama is running and accessible at the configured URL.")
            logger.error("Run 'python test_ollama_connection.py' to diagnose connection issues.")
            return (
                "I apologize, but I'm currently unable to connect to my language model service. "
                "This could be because the service is not running or is experiencing issues. "
                "Please check the following:\n"
                "1. Ensure Ollama is installed and running\n"
                "2. Verify the correct URL is configured in the .env file\n"
                "3. Check network connectivity between this service and Ollama\n"
                "For more help, please refer to the README.md file or contact support."
            )
        except httpx.TimeoutError:
            logger.error(f"Timeout connecting to Ollama API at {self.generate_endpoint}")
            return (
                "I apologize, but the request to the language model timed out. "
                "This might be due to high load or the complexity of your query. "
                "Please try again with a shorter message or try again later."
            )
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            logger.error(f"Request was sent to: {self.generate_endpoint}")
            return "I apologize, but I encountered an error processing your request. Please try again later."
            
    async def generate_follow_up_suggestions(self, user_input: str, ai_response: str, user_id: str, max_suggestions: int = 3) -> List[str]:
        """
        Generate follow-up suggestions for the user to continue the conversation after an AI response.
        
        Args:
            user_input: The user's original message
            ai_response: The AI's response to the user
            user_id: The unique identifier for the user
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            A list of suggested follow-up messages for the user
        """
        try:
            # Prepare the request payload with a prompt specifically for generating follow-up suggestions
            payload = {
                "model": self.model,
                "prompt": f"Based on this conversation:\nUser: {user_input}\nAI: {ai_response}\n\nGenerate {max_suggestions} natural follow-up questions or statements that the user might want to ask or say next. These should be complete sentences that continue the conversation naturally. Return only the suggestions, one per line, without numbering or additional text.",
                "stream": False,
                "system": "You are helping to generate follow-up suggestions for a mental health assistant conversation. Provide concise, helpful follow-up messages that a user might want to send next."
            }
            
            logger.info(f"Generating follow-up suggestions for user {user_id}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.generate_endpoint,
                    json=payload,
                    timeout=30.0  # Shorter timeout for suggestions
                )
                
                if response.status_code != 200:
                    logger.error(f"Ollama API error for follow-up suggestions: {response.status_code} - {response.text}")
                    return ["Can you tell me more about that?", 
                            "How can I implement these suggestions in my daily life?", 
                            "What if that doesn't work for me?"]
                
                result = response.json()
                suggestions_text = result.get("response", "")
                
                # Parse the response into individual suggestions
                suggestions = [s.strip() for s in suggestions_text.split('\n') if s.strip()]
                
                # Limit to max_suggestions
                filtered_suggestions = suggestions[:max_suggestions]
                
                # If we don't have enough suggestions, add some defaults
                if len(filtered_suggestions) < max_suggestions:
                    defaults = [
                        "Can you tell me more about that?",
                        "How can I implement these suggestions in my daily life?",
                        "What if that doesn't work for me?"
                    ]
                    filtered_suggestions.extend(defaults[:max_suggestions - len(filtered_suggestions)])
                
                return filtered_suggestions[:max_suggestions]
                
        except Exception as e:
            logger.error(f"Error generating follow-up suggestions: {str(e)}")
            # Return default suggestions in case of error
            return ["Can you tell me more about that?", 
                    "How can I implement these suggestions in my daily life?", 
                    "What if that doesn't work for me?"]
    
    async def generate_suggestions(self, partial_input: str, user_id: str, max_suggestions: int = 3) -> List[str]:
        """
        Generate autocomplete suggestions based on partial user input.
        
        Args:
            partial_input: The partial text input from the user
            user_id: The unique identifier for the user
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            A list of suggested completions for the partial input
        """
        try:
            if not partial_input.strip():
                return ["How are you feeling today?", 
                        "Can you tell me about your day?", 
                        "What's on your mind?"]
            
            # Prepare the request payload with a prompt specifically for generating suggestions
            payload = {
                "model": self.model,
                "prompt": f"Based on the partial input: '{partial_input}', suggest {max_suggestions} possible completions that a user might be typing when asking a mental health assistant for help. Return only the completions, one per line, without numbering or additional text.",
                "stream": False,
                "system": "You are helping to generate autocomplete suggestions for a mental health assistant. Provide concise, helpful completions that a user might be typing."
            }
            
            logger.info(f"Generating autocomplete suggestions for user {user_id}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.generate_endpoint,
                    json=payload,
                    timeout=30.0  # Shorter timeout for suggestions
                )
                
                if response.status_code != 200:
                    logger.error(f"Ollama API error for suggestions: {response.status_code} - {response.text}")
                    return ["How are you feeling today?", 
                            "Can you tell me about your day?", 
                            "What's on your mind?"]
                
                result = response.json()
                suggestions_text = result.get("response", "")
                
                # Parse the response into individual suggestions
                suggestions = [s.strip() for s in suggestions_text.split('\n') if s.strip()]
                
                # Limit to max_suggestions and ensure they start with the partial input
                filtered_suggestions = []
                for suggestion in suggestions[:max_suggestions]:
                    if not suggestion.lower().startswith(partial_input.lower()):
                        suggestion = partial_input + suggestion
                    filtered_suggestions.append(suggestion)
                
                # If we don't have enough suggestions, add some defaults
                if len(filtered_suggestions) < max_suggestions:
                    defaults = [
                        f"{partial_input} and how to cope with it",
                        f"{partial_input} symptoms and treatment",
                        f"How to manage {partial_input}"
                    ]
                    filtered_suggestions.extend(defaults[:max_suggestions - len(filtered_suggestions)])
                
                return filtered_suggestions[:max_suggestions]
                
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            # Return default suggestions in case of error
            return ["How are you feeling today?", 
                    "Can you tell me about your day?", 
                    "What's on your mind?"]