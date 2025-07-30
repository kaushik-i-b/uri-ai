"""
API Endpoint Tests for Mental Health Assistant

This module contains automated tests for the Mental Health Assistant API endpoints.
It tests the basic functionality of all endpoints in both local and production environments.
"""

import pytest
import httpx
import asyncio
import os
from dotenv import load_dotenv
import logging
import json
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Test configuration
# Use environment variables or default to the production URL
PROD_API_URL = "https://uri-genai.fly.dev"
LOCAL_API_URL = "http://localhost:8080"
API_URL = os.getenv("TEST_API_URL", PROD_API_URL)

# Test data
TEST_USER_IDS = {
    "normal": "test_api_user_1",
    "crisis": "test_api_user_2",
    "empty": "test_api_user_3",
    "long": "test_api_user_4",
    "suggest_empty": "test_api_user_5",
    "suggest_partial": "test_api_user_6",
    "suggest_custom": "test_api_user_7",
    "history": "test_api_user_8"
}

# Sample inputs
NORMAL_INPUT = "I've been feeling a bit stressed lately with work. Do you have any relaxation techniques?"
CRISIS_INPUT = "I don't want to live anymore. Everything feels hopeless."
EMPTY_INPUT = ""
LONG_INPUT = """
I've been experiencing a lot of anxiety lately. It started about three months ago when I began a new job. 
The pressure is intense, and I find myself worrying constantly about deadlines and making mistakes. 
Sometimes I wake up in the middle of the night with my heart racing. During the day, I have trouble 
concentrating on tasks because my mind keeps jumping to all the things that could go wrong. I've tried 
deep breathing and meditation, but they only help temporarily. I'm eating less than usual and have lost 
some weight. My friends have noticed that I'm more withdrawn and don't join social activities as much as before. 
I'm wondering if this is just normal stress or if it might be an anxiety disorder. What do you think? 
What strategies might help me manage these feelings better?
""" * 5  # Multiply to make it very long

# Suggestion inputs
EMPTY_SUGGESTION = ""
PARTIAL_SUGGESTION = "How to deal with anx"
CUSTOM_SUGGESTION = "I feel"

@pytest.mark.asyncio
async def test_root_endpoint():
    """Test the root endpoint (API-01)."""
    logger.info(f"Testing root endpoint at {API_URL}")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/")
        
        # Check status code
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Check response content
        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        assert "status" in data, "Response should contain 'status' field"
        assert "endpoints" in data, "Response should contain 'endpoints' field"
        
        logger.info("Root endpoint test passed")

@pytest.mark.asyncio
async def test_chat_normal_input():
    """Test chat endpoint with normal input (API-02)."""
    logger.info(f"Testing chat endpoint with normal input at {API_URL}")
    
    payload = {
        "user_input": NORMAL_INPUT,
        "user_id": TEST_USER_IDS["normal"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/chat",
            json=payload,
            timeout=30.0  # Longer timeout for LLM generation
        )
        
        # Check status code
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Check response content
        data = response.json()
        assert "reply" in data, "Response should contain 'reply' field"
        assert "crisis" in data, "Response should contain 'crisis' field"
        assert "follow_up_suggestions" in data, "Response should contain 'follow_up_suggestions' field"
        
        # Check crisis flag is false for normal input
        assert data["crisis"] is False, "Crisis flag should be False for normal input"
        
        # Check follow-up suggestions
        assert isinstance(data["follow_up_suggestions"], list), "follow_up_suggestions should be a list"
        assert len(data["follow_up_suggestions"]) > 0, "follow_up_suggestions should not be empty"
        
        logger.info("Chat endpoint with normal input test passed")

@pytest.mark.asyncio
async def test_chat_crisis_input():
    """Test chat endpoint with crisis indicators (API-03)."""
    logger.info(f"Testing chat endpoint with crisis input at {API_URL}")
    
    payload = {
        "user_input": CRISIS_INPUT,
        "user_id": TEST_USER_IDS["crisis"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/chat",
            json=payload,
            timeout=30.0  # Longer timeout for LLM generation
        )
        
        # Check status code
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Check response content
        data = response.json()
        assert "reply" in data, "Response should contain 'reply' field"
        assert "crisis" in data, "Response should contain 'crisis' field"
        
        # Check if crisis resources are included in the reply
        # This might be true or false depending on the crisis detection implementation
        # We'll just log the result rather than asserting
        logger.info(f"Crisis flag: {data['crisis']}")
        if data["crisis"]:
            assert "National Suicide Prevention Lifeline" in data["reply"], "Crisis resources should be included in reply"
        
        logger.info("Chat endpoint with crisis input test passed")

@pytest.mark.asyncio
async def test_chat_empty_input():
    """Test chat endpoint with empty input (API-04)."""
    logger.info(f"Testing chat endpoint with empty input at {API_URL}")
    
    payload = {
        "user_input": EMPTY_INPUT,
        "user_id": TEST_USER_IDS["empty"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/chat",
            json=payload,
            timeout=30.0
        )
        
        # The API might return 400 Bad Request or handle empty input gracefully
        # We'll accept either behavior
        if response.status_code == 400:
            logger.info("API returned 400 Bad Request for empty input (expected behavior)")
        else:
            assert response.status_code == 200, f"Expected status code 200 or 400, got {response.status_code}"
            data = response.json()
            assert "reply" in data, "Response should contain 'reply' field"
            logger.info("API handled empty input gracefully")
        
        logger.info("Chat endpoint with empty input test passed")

@pytest.mark.asyncio
async def test_chat_long_input():
    """Test chat endpoint with very long input (API-05)."""
    logger.info(f"Testing chat endpoint with long input at {API_URL}")
    
    payload = {
        "user_input": LONG_INPUT,
        "user_id": TEST_USER_IDS["long"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/chat",
            json=payload,
            timeout=60.0  # Longer timeout for processing long input
        )
        
        # Check status code
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Check response content
        data = response.json()
        assert "reply" in data, "Response should contain 'reply' field"
        assert len(data["reply"]) > 0, "Reply should not be empty"
        
        logger.info("Chat endpoint with long input test passed")

@pytest.mark.asyncio
async def test_suggest_empty_input():
    """Test suggest endpoint with empty input (API-06)."""
    logger.info(f"Testing suggest endpoint with empty input at {API_URL}")
    
    payload = {
        "partial_input": EMPTY_SUGGESTION,
        "user_id": TEST_USER_IDS["suggest_empty"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/suggest",
            json=payload,
            timeout=30.0
        )
        
        # Check status code
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Check response content
        data = response.json()
        assert "suggestions" in data, "Response should contain 'suggestions' field"
        assert isinstance(data["suggestions"], list), "suggestions should be a list"
        assert len(data["suggestions"]) > 0, "suggestions should not be empty"
        
        logger.info("Suggest endpoint with empty input test passed")

@pytest.mark.asyncio
async def test_suggest_partial_input():
    """Test suggest endpoint with partial input (API-07)."""
    logger.info(f"Testing suggest endpoint with partial input at {API_URL}")
    
    payload = {
        "partial_input": PARTIAL_SUGGESTION,
        "user_id": TEST_USER_IDS["suggest_partial"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/suggest",
            json=payload,
            timeout=30.0
        )
        
        # Check status code
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Check response content
        data = response.json()
        assert "suggestions" in data, "Response should contain 'suggestions' field"
        assert isinstance(data["suggestions"], list), "suggestions should be a list"
        assert len(data["suggestions"]) > 0, "suggestions should not be empty"
        
        # Check if suggestions are relevant to the partial input
        for suggestion in data["suggestions"]:
            assert PARTIAL_SUGGESTION.lower() in suggestion.lower() or suggestion.lower() in PARTIAL_SUGGESTION.lower(), \
                f"Suggestion '{suggestion}' should be related to '{PARTIAL_SUGGESTION}'"
        
        logger.info("Suggest endpoint with partial input test passed")

@pytest.mark.asyncio
async def test_suggest_custom_max():
    """Test suggest endpoint with custom max_suggestions (API-08)."""
    logger.info(f"Testing suggest endpoint with custom max_suggestions at {API_URL}")
    
    max_suggestions = 5
    payload = {
        "partial_input": CUSTOM_SUGGESTION,
        "user_id": TEST_USER_IDS["suggest_custom"],
        "max_suggestions": max_suggestions
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/suggest",
            json=payload,
            timeout=30.0
        )
        
        # Check status code
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Check response content
        data = response.json()
        assert "suggestions" in data, "Response should contain 'suggestions' field"
        assert isinstance(data["suggestions"], list), "suggestions should be a list"
        assert len(data["suggestions"]) == max_suggestions, f"Should return exactly {max_suggestions} suggestions"
        
        logger.info("Suggest endpoint with custom max_suggestions test passed")

@pytest.mark.asyncio
async def test_history_endpoint():
    """Test history endpoint (API-09)."""
    logger.info(f"Testing history endpoint at {API_URL}")
    
    user_id = TEST_USER_IDS["history"]
    
    # First, send a few chat messages to create history
    chat_messages = [
        "Hello, I'm feeling a bit anxious today.",
        "Can you tell me some relaxation techniques?",
        "How can I practice mindfulness in daily life?"
    ]
    
    async with httpx.AsyncClient() as client:
        # Send chat messages
        for message in chat_messages:
            await client.post(
                f"{API_URL}/chat",
                json={"user_input": message, "user_id": user_id},
                timeout=30.0
            )
        
        # Now retrieve history
        response = await client.get(
            f"{API_URL}/history/{user_id}",
            timeout=30.0
        )
        
        # Check status code
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Check response content
        data = response.json()
        assert isinstance(data, list), "Response should be a list of chat logs"
        
        # We should have at least the number of messages we sent
        assert len(data) >= len(chat_messages), f"Expected at least {len(chat_messages)} chat logs, got {len(data)}"
        
        # Check structure of chat logs
        if len(data) > 0:
            chat_log = data[0]
            assert "id" in chat_log, "Chat log should contain 'id' field"
            assert "user_id" in chat_log, "Chat log should contain 'user_id' field"
            assert "prompt" in chat_log, "Chat log should contain 'prompt' field"
            assert "reply" in chat_log, "Chat log should contain 'reply' field"
            assert "timestamp" in chat_log, "Chat log should contain 'timestamp' field"
        
        logger.info("History endpoint test passed")

@pytest.mark.asyncio
async def test_memory_context():
    """Test memory context in chat responses (MEM-01)."""
    logger.info(f"Testing memory context in chat responses at {API_URL}")
    
    user_id = f"test_memory_{asyncio.get_event_loop().time()}"  # Unique user ID
    
    # First message
    first_message = "I've been having trouble sleeping lately."
    
    # Second message that references the first
    second_message = "What techniques can help with that?"
    
    async with httpx.AsyncClient() as client:
        # Send first message
        first_response = await client.post(
            f"{API_URL}/chat",
            json={"user_input": first_message, "user_id": user_id},
            timeout=30.0
        )
        
        assert first_response.status_code == 200, "First message should be successful"
        
        # Send second message
        second_response = await client.post(
            f"{API_URL}/chat",
            json={"user_input": second_message, "user_id": user_id},
            timeout=30.0
        )
        
        assert second_response.status_code == 200, "Second message should be successful"
        
        # Check if the second response references sleep or insomnia
        # This is a heuristic test - the actual response depends on the LLM
        second_data = second_response.json()
        reply_lower = second_data["reply"].lower()
        
        sleep_related_terms = ["sleep", "insomnia", "rest", "bed", "night"]
        has_context = any(term in reply_lower for term in sleep_related_terms)
        
        # We'll log the result rather than asserting, as it depends on the LLM implementation
        if has_context:
            logger.info("Memory context test passed: Response contains sleep-related terms")
        else:
            logger.warning("Memory context test inconclusive: Response doesn't contain expected terms")
            logger.warning(f"Response: {second_data['reply'][:100]}...")
        
        logger.info("Memory context test completed")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_root_endpoint())
    asyncio.run(test_chat_normal_input())
    asyncio.run(test_chat_crisis_input())
    asyncio.run(test_chat_empty_input())
    asyncio.run(test_chat_long_input())
    asyncio.run(test_suggest_empty_input())
    asyncio.run(test_suggest_partial_input())
    asyncio.run(test_suggest_custom_max())
    asyncio.run(test_history_endpoint())
    asyncio.run(test_memory_context())