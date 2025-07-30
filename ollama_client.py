import httpx
import logging
import os
import random
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
        
        # Check if fallback mode is enabled
        self.fallback_mode = os.getenv("ENABLE_FALLBACK_MODE", "false").lower() == "true"
        
        if self.fallback_mode:
            logger.info(f"Initialized OllamaClient with fallback mode enabled. Will use predefined responses if Ollama is unavailable.")
        else:
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
        # Predefined fallback responses for when Ollama is unavailable
        fallback_responses = [
            "I understand you're reaching out about your mental health. While I'm currently operating in a limited capacity, I want you to know that your well-being matters. Consider speaking with a mental health professional who can provide personalized support.",
            
            "Thank you for sharing your thoughts with me. I'm currently running in fallback mode with limited capabilities, but I'm here to acknowledge your message. For more comprehensive support, please consider reaching out to a mental health professional.",
            
            "I appreciate you trusting me with your thoughts. While I'm operating with limited functionality at the moment, I want to encourage you to practice self-care and reach out to supportive people in your life.",
            
            "I'm currently operating in a simplified mode, but I want to acknowledge your message. Remember that taking care of your mental health is important, and professional resources are available to provide the support you need.",
            
            "While I'm running with limited capabilities right now, I want you to know that your mental health matters. Consider practicing mindfulness, reaching out to supportive friends or family, or consulting with a mental health professional.",
            
            "I'm currently in fallback mode with limited functionality, but I want to acknowledge your message. Remember that it's okay to ask for help, and there are resources available to support your mental health journey."
        ]
        
        # If fallback mode is enabled, return a predefined response
        if self.fallback_mode:
            logger.info(f"Using fallback response for user {user_id} (fallback mode enabled)")
            return random.choice(fallback_responses)
            
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
            
            # Use fallback responses for connection errors
            logger.info(f"Using fallback response for user {user_id} (connection error)")
            return random.choice(fallback_responses)
            
        except httpx.TimeoutError:
            logger.error(f"Timeout connecting to Ollama API at {self.generate_endpoint}")
            
            # Use fallback responses for timeout errors
            logger.info(f"Using fallback response for user {user_id} (timeout error)")
            return random.choice(fallback_responses)
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            logger.error(f"Request was sent to: {self.generate_endpoint}")
            
            # Use fallback responses for general errors
            logger.info(f"Using fallback response for user {user_id} (general error)")
            return random.choice(fallback_responses)
            
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
        # Default suggestions to use in fallback mode or in case of errors
        default_suggestions = [
            "Can you tell me more about that?",
            "How can I implement these suggestions in my daily life?",
            "What if that doesn't work for me?",
            "Could you explain that in a different way?",
            "How might this affect my mental health?",
            "What are some resources I could look into?"
        ]
        
        # If fallback mode is enabled, return default suggestions immediately
        if self.fallback_mode:
            logger.info(f"Using default follow-up suggestions for user {user_id} (fallback mode enabled)")
            return default_suggestions[:max_suggestions]
            
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
                    return default_suggestions[:max_suggestions]
                
                result = response.json()
                suggestions_text = result.get("response", "")
                
                # Parse the response into individual suggestions
                suggestions = [s.strip() for s in suggestions_text.split('\n') if s.strip()]
                
                # Limit to max_suggestions
                filtered_suggestions = suggestions[:max_suggestions]
                
                # If we don't have enough suggestions, add some defaults
                if len(filtered_suggestions) < max_suggestions:
                    filtered_suggestions.extend(default_suggestions[:max_suggestions - len(filtered_suggestions)])
                
                return filtered_suggestions[:max_suggestions]
                
        except httpx.ConnectError as e:
            logger.error(f"Connection error to Ollama API: {str(e)}")
            logger.info(f"Using default follow-up suggestions for user {user_id} (connection error)")
            return default_suggestions[:max_suggestions]
            
        except Exception as e:
            logger.error(f"Error generating follow-up suggestions: {str(e)}")
            logger.info(f"Using default follow-up suggestions for user {user_id} (general error)")
            return default_suggestions[:max_suggestions]
    
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
        # Default suggestions for empty input or fallback mode
        empty_input_suggestions = [
            "How are you feeling today?", 
            "Can you tell me about your day?", 
            "What's on your mind?",
            "I've been feeling anxious lately",
            "Can you help me with stress management?",
            "I'm having trouble sleeping"
        ]
        
        # If input is empty, return default suggestions
        if not partial_input.strip():
            return empty_input_suggestions[:max_suggestions]
            
        # If fallback mode is enabled, return input-specific default suggestions
        if self.fallback_mode:
            logger.info(f"Using default suggestions for user {user_id} (fallback mode enabled)")
            
            # Create input-specific suggestions
            defaults = [
                f"{partial_input} and how to cope with it",
                f"{partial_input} symptoms and treatment",
                f"How to manage {partial_input}",
                f"{partial_input} techniques for mental health",
                f"Ways to improve {partial_input}",
                f"{partial_input} and its impact on wellbeing"
            ]
            
            return defaults[:max_suggestions]
            
        try:
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
                    
                    # Create input-specific suggestions for error case
                    defaults = [
                        f"{partial_input} and how to cope with it",
                        f"{partial_input} symptoms and treatment",
                        f"How to manage {partial_input}"
                    ]
                    return defaults[:max_suggestions]
                
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
                
        except httpx.ConnectError as e:
            logger.error(f"Connection error to Ollama API: {str(e)}")
            logger.info(f"Using default suggestions for user {user_id} (connection error)")
            
            # Create input-specific suggestions for connection error
            defaults = [
                f"{partial_input} and how to cope with it",
                f"{partial_input} symptoms and treatment",
                f"How to manage {partial_input}",
                f"{partial_input} techniques for mental health"
            ]
            return defaults[:max_suggestions]
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            logger.info(f"Using default suggestions for user {user_id} (general error)")
            
            # Create input-specific suggestions for general error
            defaults = [
                f"{partial_input} and how to cope with it",
                f"{partial_input} symptoms and treatment",
                f"How to manage {partial_input}"
            ]
            return defaults[:max_suggestions]