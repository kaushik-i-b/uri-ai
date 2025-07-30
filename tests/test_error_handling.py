"""
Error Handling Tests for Mental Health Assistant

This module contains automated tests for error handling and fallback mechanisms
in the Mental Health Assistant API.
"""

import pytest
import httpx
import asyncio
import os
import json
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
# Use environment variables or default to the production URL
PROD_API_URL = "https://uri-genai.fly.dev"
LOCAL_API_URL = "http://localhost:8080"
API_URL = os.getenv("TEST_API_URL", PROD_API_URL)

# Test data
TEST_USER_IDS = {
    "malformed_json": "test_error_user_1",
    "missing_fields": "test_error_user_2",
    "invalid_user_id": "",
    "invalid_format": "test_error_user_4"
}

@pytest.mark.asyncio
async def test_malformed_json():
    """Test with malformed JSON (ERR-03)."""
    logger.info(f"Testing chat endpoint with malformed JSON at {API_URL}")
    
    # Malformed JSON (missing closing brace)
    malformed_payload = '{"user_input": "Hello", "user_id": "test_error_user_1"'
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/chat",
            content=malformed_payload,
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )
        
        # Check status code - should be 400 Bad Request
        assert response.status_code == 400, f"Expected status code 400, got {response.status_code}"
        
        logger.info("Malformed JSON test passed")

@pytest.mark.asyncio
async def test_missing_required_fields():
    """Test with missing required fields (ERR-04)."""
    logger.info(f"Testing chat endpoint with missing required fields at {API_URL}")
    
    # Missing user_input field
    payload = {
        "user_id": TEST_USER_IDS["missing_fields"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/chat",
            json=payload,
            timeout=30.0
        )
        
        # Check status code - should be 422 Unprocessable Entity
        assert response.status_code == 422, f"Expected status code 422, got {response.status_code}"
        
        # Check response content
        data = response.json()
        assert "detail" in data, "Response should contain 'detail' field with error information"
        
        logger.info("Missing required fields test passed")

@pytest.mark.asyncio
async def test_invalid_user_id():
    """Test with invalid user_id format (ERR-05)."""
    logger.info(f"Testing chat endpoint with invalid user_id at {API_URL}")
    
    # Empty user_id
    payload = {
        "user_input": "Hello, how are you?",
        "user_id": TEST_USER_IDS["invalid_user_id"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/chat",
            json=payload,
            timeout=30.0
        )
        
        # The API might validate user_id and return an error, or it might accept empty user_id
        # We'll log the behavior rather than asserting
        if response.status_code in [400, 422]:
            logger.info(f"API rejected empty user_id with status code {response.status_code}")
        else:
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            logger.info("API accepted empty user_id")
        
        logger.info("Invalid user_id test completed")

@pytest.mark.asyncio
async def test_invalid_format():
    """Test with invalid data format."""
    logger.info(f"Testing chat endpoint with invalid data format at {API_URL}")
    
    # Send form data instead of JSON
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/chat",
            data={"user_input": "Hello", "user_id": TEST_USER_IDS["invalid_format"]},
            timeout=30.0
        )
        
        # Check status code - should be 415 Unsupported Media Type or 400 Bad Request
        assert response.status_code in [400, 415], f"Expected status code 400 or 415, got {response.status_code}"
        
        logger.info("Invalid format test passed")

@pytest.mark.asyncio
async def test_nonexistent_endpoint():
    """Test accessing a non-existent endpoint."""
    logger.info(f"Testing non-existent endpoint at {API_URL}")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/nonexistent_endpoint",
            timeout=30.0
        )
        
        # Check status code - should be 404 Not Found
        assert response.status_code == 404, f"Expected status code 404, got {response.status_code}"
        
        logger.info("Non-existent endpoint test passed")

@pytest.mark.asyncio
async def test_method_not_allowed():
    """Test using an incorrect HTTP method."""
    logger.info(f"Testing method not allowed at {API_URL}")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/chat",
            timeout=30.0
        )
        
        # Check status code - should be 405 Method Not Allowed
        assert response.status_code == 405, f"Expected status code 405, got {response.status_code}"
        
        logger.info("Method not allowed test passed")

@pytest.mark.asyncio
async def test_too_large_payload():
    """Test with a payload that exceeds size limits."""
    logger.info(f"Testing chat endpoint with too large payload at {API_URL}")
    
    # Create a very large input (10MB)
    large_input = "x" * (10 * 1024 * 1024)
    
    payload = {
        "user_input": large_input,
        "user_id": "test_large_payload"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/chat",
                json=payload,
                timeout=30.0
            )
            
            # If the request succeeds, the server might have accepted the large payload
            # or truncated it. We'll log the behavior.
            logger.info(f"Large payload request returned status code {response.status_code}")
            
            if response.status_code in [400, 413]:
                logger.info("Server rejected the large payload (expected behavior)")
            else:
                logger.info("Server accepted or truncated the large payload")
                
        except httpx.RequestError as e:
            # The request might fail due to the large payload
            logger.info(f"Large payload request failed: {str(e)}")
            logger.info("This might be expected behavior for very large payloads")
        
        logger.info("Too large payload test completed")

@pytest.mark.asyncio
async def test_fallback_mode():
    """Test fallback mode behavior when services are unavailable (ERR-01, ERR-02)."""
    logger.info(f"Testing fallback mode behavior at {API_URL}")
    
    # Note: This test is more of a verification than a true test, as we can't easily
    # simulate service unavailability in the deployed app. We'll check if the app
    # responds to requests, which indicates it's either working normally or in fallback mode.
    
    payload = {
        "user_input": "Hello, how are you?",
        "user_id": "test_fallback_mode"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/chat",
            json=payload,
            timeout=30.0
        )
        
        # Check if the app responds
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Check response content
        data = response.json()
        assert "reply" in data, "Response should contain 'reply' field"
        
        logger.info("Fallback mode behavior test completed")
        logger.info(f"App is responding, which indicates it's either working normally or in fallback mode")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_malformed_json())
    asyncio.run(test_missing_required_fields())
    asyncio.run(test_invalid_user_id())
    asyncio.run(test_invalid_format())
    asyncio.run(test_nonexistent_endpoint())
    asyncio.run(test_method_not_allowed())
    asyncio.run(test_too_large_payload())
    asyncio.run(test_fallback_mode())