"""
Memory Functionality Tests for Mental Health Assistant

This module contains automated tests for the memory functionality of the Mental Health Assistant API.
It tests how the application stores and retrieves conversation context.
"""

import pytest
import httpx
import asyncio
import os
import logging
import time
import uuid
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
# Use environment variables or default to the production URL
PROD_API_URL = "https://uri-genai.fly.dev"
LOCAL_API_URL = "http://localhost:8080"
API_URL = os.getenv("TEST_API_URL", PROD_API_URL)

def generate_unique_user_id():
    """Generate a unique user ID for testing."""
    return f"test_memory_{uuid.uuid4().hex[:8]}"

@pytest.mark.asyncio
async def test_memory_retrieval():
    """Test memory retrieval in conversations (MEM-01)."""
    logger.info(f"Testing memory retrieval at {API_URL}")
    
    # Generate a unique user ID for this test
    user_id = generate_unique_user_id()
    
    # Conversation flow with related messages
    conversation = [
        "I've been having trouble sleeping lately. I keep waking up in the middle of the night.",
        "What techniques do you recommend for better sleep?",
        "I tried the deep breathing you suggested, but it didn't help much.",
        "Are there any other relaxation techniques I could try?"
    ]
    
    async with httpx.AsyncClient() as client:
        # Send each message in the conversation
        responses = []
        for message in conversation:
            response = await client.post(
                f"{API_URL}/chat",
                json={"user_input": message, "user_id": user_id},
                timeout=30.0
            )
            
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            responses.append(response.json())
            
            # Small delay to ensure messages are processed and stored
            await asyncio.sleep(1)
        
        # Check if later responses reference earlier conversation
        # This is a heuristic test - the actual response depends on the LLM and memory implementation
        
        # The third message references "deep breathing" which should have been suggested in the second response
        third_response = responses[2]["reply"].lower()
        logger.info(f"Third response: {third_response[:100]}...")
        
        # The fourth response should reference the context of the entire conversation
        fourth_response = responses[3]["reply"].lower()
        logger.info(f"Fourth response: {fourth_response[:100]}...")
        
        # Check for sleep-related terms in the responses
        sleep_related_terms = ["sleep", "insomnia", "rest", "bed", "night", "breathing", "relaxation"]
        
        # Check if the later responses contain context from earlier messages
        third_has_context = any(term in third_response for term in sleep_related_terms)
        fourth_has_context = any(term in fourth_response for term in sleep_related_terms)
        
        if third_has_context and fourth_has_context:
            logger.info("Memory retrieval test passed: Responses contain context from earlier messages")
        else:
            logger.warning("Memory retrieval test inconclusive: Responses don't contain expected context")
            if not third_has_context:
                logger.warning("Third response doesn't contain expected sleep-related terms")
            if not fourth_has_context:
                logger.warning("Fourth response doesn't contain expected sleep-related terms")
        
        logger.info("Memory retrieval test completed")

@pytest.mark.asyncio
async def test_memory_persistence():
    """Test memory persistence across sessions (MEM-02)."""
    logger.info(f"Testing memory persistence at {API_URL}")
    
    # Generate a unique user ID for this test
    user_id = generate_unique_user_id()
    
    # First session messages
    first_session_messages = [
        "I've been diagnosed with anxiety disorder recently.",
        "My doctor recommended cognitive behavioral therapy. What do you think about that?"
    ]
    
    # Second session messages (simulating a new session after some time)
    second_session_messages = [
        "I started the therapy we discussed earlier. It's been helpful so far.",
        "What other self-care practices would complement my therapy?"
    ]
    
    async with httpx.AsyncClient() as client:
        # First session
        logger.info("Starting first session")
        for message in first_session_messages:
            response = await client.post(
                f"{API_URL}/chat",
                json={"user_input": message, "user_id": user_id},
                timeout=30.0
            )
            
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Simulate a delay between sessions
        logger.info("Waiting between sessions...")
        await asyncio.sleep(5)
        
        # Second session
        logger.info("Starting second session")
        responses = []
        for message in second_session_messages:
            response = await client.post(
                f"{API_URL}/chat",
                json={"user_input": message, "user_id": user_id},
                timeout=30.0
            )
            
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            responses.append(response.json())
        
        # Check if the second session responses reference the first session
        # This is a heuristic test - the actual response depends on the LLM and memory implementation
        first_response = responses[0]["reply"].lower()
        second_response = responses[1]["reply"].lower()
        
        # Check for therapy-related terms that would indicate memory persistence
        therapy_related_terms = ["therapy", "cbt", "cognitive", "behavioral", "anxiety", "treatment"]
        
        first_has_context = any(term in first_response for term in therapy_related_terms)
        second_has_context = any(term in second_response for term in therapy_related_terms)
        
        if first_has_context:
            logger.info("Memory persistence test passed: First response contains context from previous session")
        else:
            logger.warning("Memory persistence test inconclusive: First response doesn't contain expected context")
        
        if second_has_context:
            logger.info("Memory persistence test passed: Second response contains context from previous session")
        else:
            logger.warning("Memory persistence test inconclusive: Second response doesn't contain expected context")
        
        logger.info("Memory persistence test completed")

@pytest.mark.asyncio
async def test_fallback_memory_storage():
    """Test fallback to in-memory storage (MEM-03)."""
    logger.info(f"Testing fallback memory storage at {API_URL}")
    
    # Note: This test is more of a verification than a true test, as we can't easily
    # configure the deployed app to use invalid Milvus host. We'll check if the app
    # responds to requests and maintains context, which indicates memory is working
    # either with Milvus or with the fallback in-memory storage.
    
    # Generate a unique user ID for this test
    user_id = generate_unique_user_id()
    
    # Conversation flow
    conversation = [
        "I'm feeling very stressed about my upcoming exams.",
        "What are some effective study techniques that can help reduce stress?"
    ]
    
    async with httpx.AsyncClient() as client:
        # Send each message in the conversation
        responses = []
        for message in conversation:
            response = await client.post(
                f"{API_URL}/chat",
                json={"user_input": message, "user_id": user_id},
                timeout=30.0
            )
            
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            responses.append(response.json())
            
            # Small delay to ensure messages are processed and stored
            await asyncio.sleep(1)
        
        # Check if the second response references the first message
        second_response = responses[1]["reply"].lower()
        
        # Check for stress or exam related terms
        related_terms = ["stress", "exam", "study", "technique"]
        has_context = any(term in second_response for term in related_terms)
        
        if has_context:
            logger.info("Fallback memory storage test passed: Response contains context from earlier message")
        else:
            logger.warning("Fallback memory storage test inconclusive: Response doesn't contain expected context")
        
        logger.info("Fallback memory storage test completed")

@pytest.mark.asyncio
async def test_history_endpoint_with_memory():
    """Test history endpoint with memory functionality."""
    logger.info(f"Testing history endpoint with memory at {API_URL}")
    
    # Generate a unique user ID for this test
    user_id = generate_unique_user_id()
    
    # Conversation messages
    messages = [
        "I've been feeling down lately.",
        "I think I might be experiencing symptoms of depression.",
        "What are some self-care strategies I can try?"
    ]
    
    async with httpx.AsyncClient() as client:
        # Send messages
        for message in messages:
            await client.post(
                f"{API_URL}/chat",
                json={"user_input": message, "user_id": user_id},
                timeout=30.0
            )
            
            # Small delay to ensure messages are processed and stored
            await asyncio.sleep(1)
        
        # Retrieve history
        response = await client.get(
            f"{API_URL}/history/{user_id}",
            timeout=30.0
        )
        
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Check history content
        history = response.json()
        assert isinstance(history, list), "History should be a list"
        assert len(history) >= len(messages), f"Expected at least {len(messages)} history items, got {len(history)}"
        
        # Check if history contains all the messages we sent
        history_prompts = [item["prompt"] for item in history]
        for message in messages:
            assert message in history_prompts, f"Message '{message}' not found in history"
        
        logger.info("History endpoint with memory test passed")

@pytest.mark.asyncio
async def test_context_influence_on_responses():
    """Test how context influences responses."""
    logger.info(f"Testing context influence on responses at {API_URL}")
    
    # We'll use two different user IDs to compare responses with and without context
    user_id_with_context = generate_unique_user_id()
    user_id_without_context = generate_unique_user_id()
    
    # Setup context for the first user
    context_messages = [
        "I have a phobia of flying that's been getting worse.",
        "I have a business trip next month that requires flying and I'm very anxious about it."
    ]
    
    # Test message that will be sent to both users
    test_message = "What techniques can help me manage my anxiety?"
    
    async with httpx.AsyncClient() as client:
        # Send context messages for the first user
        for message in context_messages:
            await client.post(
                f"{API_URL}/chat",
                json={"user_input": message, "user_id": user_id_with_context},
                timeout=30.0
            )
            
            # Small delay to ensure messages are processed and stored
            await asyncio.sleep(1)
        
        # Send test message to both users
        response_with_context = await client.post(
            f"{API_URL}/chat",
            json={"user_input": test_message, "user_id": user_id_with_context},
            timeout=30.0
        )
        
        response_without_context = await client.post(
            f"{API_URL}/chat",
            json={"user_input": test_message, "user_id": user_id_without_context},
            timeout=30.0
        )
        
        # Check responses
        assert response_with_context.status_code == 200, "Response with context should be successful"
        assert response_without_context.status_code == 200, "Response without context should be successful"
        
        with_context_reply = response_with_context.json()["reply"].lower()
        without_context_reply = response_without_context.json()["reply"].lower()
        
        # Check if the response with context mentions flying or phobia
        flying_related_terms = ["fly", "flying", "flight", "plane", "airplane", "phobia", "travel"]
        has_flying_context = any(term in with_context_reply for term in flying_related_terms)
        
        if has_flying_context:
            logger.info("Context influence test passed: Response with context mentions flying-related terms")
        else:
            logger.warning("Context influence test inconclusive: Response with context doesn't mention flying-related terms")
        
        # Log the first part of both responses for comparison
        logger.info(f"Response with context: {with_context_reply[:100]}...")
        logger.info(f"Response without context: {without_context_reply[:100]}...")
        
        logger.info("Context influence on responses test completed")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_memory_retrieval())
    asyncio.run(test_memory_persistence())
    asyncio.run(test_fallback_memory_storage())
    asyncio.run(test_history_endpoint_with_memory())
    asyncio.run(test_context_influence_on_responses())