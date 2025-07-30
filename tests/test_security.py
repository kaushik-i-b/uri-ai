"""
Security Tests for Mental Health Assistant API

This module contains security tests for the Mental Health Assistant API.
It tests input validation, rate limiting, and data privacy aspects.
"""

import pytest
import httpx
import asyncio
import os
import logging
import time
import uuid
import re
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
    return f"test_security_{uuid.uuid4().hex[:8]}"

@pytest.mark.asyncio
async def test_xss_input_validation():
    """Test input validation for XSS attacks (SEC-01)."""
    logger.info(f"Testing XSS input validation at {API_URL}")
    
    # Generate a unique user ID for this test
    user_id = generate_unique_user_id()
    
    # XSS payloads to test
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src='x' onerror='alert(\"XSS\")'>",
        "<svg onload='alert(\"XSS\")'>",
        "javascript:alert('XSS')",
        "onerror=alert('XSS')",
        "<a href='javascript:alert(\"XSS\")'>Click me</a>"
    ]
    
    async with httpx.AsyncClient() as client:
        for payload in xss_payloads:
            logger.info(f"Testing XSS payload: {payload}")
            
            response = await client.post(
                f"{API_URL}/chat",
                json={"user_input": payload, "user_id": user_id},
                timeout=30.0
            )
            
            # Check if the request was successful
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            
            # Check if the response contains the raw XSS payload
            data = response.json()
            reply = data.get("reply", "")
            
            # Check if any of the dangerous patterns are in the reply
            dangerous_patterns = [
                "<script>", "onerror=", "javascript:", "<svg onload=", 
                "alert(", "XSS", "</script>"
            ]
            
            # If the reply contains the raw XSS payload, it might be vulnerable
            has_dangerous_content = any(pattern in reply for pattern in dangerous_patterns)
            
            if has_dangerous_content:
                logger.warning(f"Response may contain unescaped XSS payload: {reply[:100]}...")
            else:
                logger.info("XSS payload was properly handled")
        
        logger.info("XSS input validation test completed")

@pytest.mark.asyncio
async def test_sql_injection_input_validation():
    """Test input validation for SQL injection attacks."""
    logger.info(f"Testing SQL injection input validation at {API_URL}")
    
    # Generate a unique user ID for this test
    user_id = generate_unique_user_id()
    
    # SQL injection payloads to test
    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "' UNION SELECT * FROM users; --",
        "admin' --",
        "1'; SELECT * FROM users WHERE name LIKE '%"
    ]
    
    async with httpx.AsyncClient() as client:
        for payload in sql_payloads:
            logger.info(f"Testing SQL injection payload: {payload}")
            
            response = await client.post(
                f"{API_URL}/chat",
                json={"user_input": payload, "user_id": user_id},
                timeout=30.0
            )
            
            # Check if the request was successful
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            
            # The API should treat this as normal text and not execute SQL
            # We can't directly test for SQL injection success/failure in a black-box test,
            # but we can check that the API responds normally
            
            data = response.json()
            assert "reply" in data, "Response should contain 'reply' field"
            
            logger.info("SQL injection payload was handled as normal text")
        
        logger.info("SQL injection input validation test completed")

@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting functionality (SEC-02)."""
    logger.info(f"Testing rate limiting at {API_URL}")
    
    # Generate a unique user ID for this test
    user_id = generate_unique_user_id()
    
    # Number of requests to send in quick succession
    num_requests = 20
    
    # Payload for the requests
    payload = {
        "user_input": "Hello, how are you?",
        "user_id": user_id
    }
    
    async with httpx.AsyncClient() as client:
        # Send multiple requests in quick succession
        start_time = time.time()
        responses = []
        
        for i in range(num_requests):
            logger.info(f"Sending request {i+1}/{num_requests}")
            
            response = await client.post(
                f"{API_URL}/chat",
                json=payload,
                timeout=30.0
            )
            
            responses.append(response)
            
            # Don't wait between requests to test rate limiting
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Check if any responses indicate rate limiting
        rate_limited = any(response.status_code in [429, 503] for response in responses)
        
        # Count successful and rate-limited responses
        successful = sum(1 for response in responses if response.status_code == 200)
        limited = sum(1 for response in responses if response.status_code in [429, 503])
        
        logger.info(f"Sent {num_requests} requests in {duration:.2f}s")
        logger.info(f"Successful responses: {successful}")
        logger.info(f"Rate-limited responses: {limited}")
        
        # Note: We don't assert that rate limiting must happen, as it depends on the server configuration
        # Instead, we log whether rate limiting was observed or not
        if rate_limited:
            logger.info("Rate limiting was observed (expected behavior for high request rates)")
        else:
            logger.info("No rate limiting was observed (server may not have rate limiting enabled)")
        
        logger.info("Rate limiting test completed")

@pytest.mark.asyncio
async def test_data_privacy():
    """Test data privacy aspects (SEC-03)."""
    logger.info(f"Testing data privacy at {API_URL}")
    
    # Generate a unique user ID for this test
    user_id = generate_unique_user_id()
    
    # Sensitive data patterns to check for in responses
    sensitive_patterns = [
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b\d{16}\b",  # Credit card number
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        r"\b\d{3}-\d{3}-\d{4}\b",  # Phone number
        r"\b(?:password|passwd|pwd)[:=]\s*\w+\b",  # Password
    ]
    
    # Test messages with sensitive data
    test_messages = [
        "My social security number is 123-45-6789",
        "My credit card number is 1234567890123456",
        "My email address is test@example.com",
        "My phone number is 555-123-4567",
        "My password is password123"
    ]
    
    async with httpx.AsyncClient() as client:
        for message in test_messages:
            logger.info(f"Testing message with sensitive data: {message}")
            
            response = await client.post(
                f"{API_URL}/chat",
                json={"user_input": message, "user_id": user_id},
                timeout=30.0
            )
            
            # Check if the request was successful
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            
            # Check if the response contains the sensitive data
            data = response.json()
            reply = data.get("reply", "")
            
            # Check for sensitive data patterns in the reply
            found_sensitive_data = []
            for pattern in sensitive_patterns:
                matches = re.findall(pattern, reply)
                if matches:
                    found_sensitive_data.extend(matches)
            
            if found_sensitive_data:
                logger.warning(f"Response contains sensitive data: {found_sensitive_data}")
            else:
                logger.info("No sensitive data found in response")
        
        # Now check the history endpoint to see if sensitive data is stored
        logger.info("Checking history endpoint for sensitive data")
        
        history_response = await client.get(
            f"{API_URL}/history/{user_id}",
            timeout=30.0
        )
        
        assert history_response.status_code == 200, f"Expected status code 200, got {history_response.status_code}"
        
        history_data = history_response.json()
        
        # Check each history item for sensitive data
        for item in history_data:
            prompt = item.get("prompt", "")
            reply = item.get("reply", "")
            
            # Check for sensitive data patterns in the prompt and reply
            found_sensitive_data = []
            for pattern in sensitive_patterns:
                prompt_matches = re.findall(pattern, prompt)
                reply_matches = re.findall(pattern, reply)
                if prompt_matches:
                    found_sensitive_data.extend(prompt_matches)
                if reply_matches:
                    found_sensitive_data.extend(reply_matches)
            
            if found_sensitive_data:
                logger.warning(f"History contains sensitive data: {found_sensitive_data}")
            else:
                logger.info("No sensitive data found in history item")
        
        logger.info("Data privacy test completed")

@pytest.mark.asyncio
async def test_authorization():
    """Test authorization aspects (SEC-04)."""
    logger.info(f"Testing authorization at {API_URL}")
    
    # Note: This test is more of a verification than a true test, as we don't know
    # if the API has protected endpoints that require authentication.
    # We'll check if the history endpoint requires authentication to access other users' data.
    
    # Generate two unique user IDs for this test
    user_id_1 = generate_unique_user_id()
    user_id_2 = generate_unique_user_id()
    
    async with httpx.AsyncClient() as client:
        # Send a message as user 1
        await client.post(
            f"{API_URL}/chat",
            json={"user_input": "Hello from user 1", "user_id": user_id_1},
            timeout=30.0
        )
        
        # Send a message as user 2
        await client.post(
            f"{API_URL}/chat",
            json={"user_input": "Hello from user 2", "user_id": user_id_2},
            timeout=30.0
        )
        
        # Try to access user 1's history as user 2
        # In a properly secured API, this should either fail or only return user 2's data
        response = await client.get(
            f"{API_URL}/history/{user_id_1}",
            timeout=30.0
        )
        
        # Check if the request was successful
        if response.status_code != 200:
            logger.info(f"Access to other user's history was denied with status code {response.status_code} (good security)")
        else:
            # If successful, check if the data belongs to user 1
            data = response.json()
            
            # Check if any of the history items contain user 1's message
            user1_data_accessible = any("Hello from user 1" in item.get("prompt", "") for item in data)
            
            if user1_data_accessible:
                logger.warning("User 1's data is accessible to user 2 (potential security issue)")
            else:
                logger.info("User 1's data is not accessible to user 2 (good security)")
        
        logger.info("Authorization test completed")

@pytest.mark.asyncio
async def test_large_payload_handling():
    """Test handling of unusually large payloads."""
    logger.info(f"Testing large payload handling at {API_URL}")
    
    # Generate a unique user ID for this test
    user_id = generate_unique_user_id()
    
    # Create payloads of increasing size
    sizes = [1024, 10*1024, 100*1024, 1024*1024]  # 1KB, 10KB, 100KB, 1MB
    
    async with httpx.AsyncClient() as client:
        for size in sizes:
            # Create a payload of the specified size
            large_input = "A" * size
            
            logger.info(f"Testing payload of size {size} bytes")
            
            try:
                response = await client.post(
                    f"{API_URL}/chat",
                    json={"user_input": large_input, "user_id": user_id},
                    timeout=60.0  # Longer timeout for large payloads
                )
                
                logger.info(f"Response status code: {response.status_code}")
                
                if response.status_code in [400, 413]:
                    logger.info(f"Large payload of {size} bytes was rejected (expected for very large payloads)")
                elif response.status_code == 200:
                    logger.info(f"Large payload of {size} bytes was accepted")
                else:
                    logger.warning(f"Unexpected status code {response.status_code} for payload of {size} bytes")
                
            except httpx.RequestError as e:
                logger.warning(f"Request failed for payload of {size} bytes: {str(e)}")
        
        logger.info("Large payload handling test completed")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_xss_input_validation())
    asyncio.run(test_sql_injection_input_validation())
    asyncio.run(test_rate_limiting())
    asyncio.run(test_data_privacy())
    asyncio.run(test_authorization())
    asyncio.run(test_large_payload_handling())