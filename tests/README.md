# Mental Health Assistant API Testing

This directory contains tests for the Mental Health Assistant API. The tests are designed to verify the functionality, performance, and security of the API in both local and production environments.

## Test Overview

The test suite includes:

1. **API Endpoint Tests** - Test basic functionality of all API endpoints
2. **Error Handling Tests** - Test how the API handles errors and edge cases
3. **Memory Functionality Tests** - Test the memory and context functionality
4. **Performance Tests** - Test the API's performance under load
5. **Security Tests** - Test the API's security features

## Prerequisites

Before running the tests, make sure you have the following installed:

```bash
pip install -r requirements.txt
```

This will install all the required dependencies, including:

- pytest
- pytest-asyncio
- httpx
- locust
- pytest-cov
- pytest-html

## Running the Tests

### API Endpoint Tests

To run the API endpoint tests:

```bash
pytest test_api_endpoints.py -v
```

These tests verify that all API endpoints are functioning correctly, including:
- Root endpoint (GET /)
- Chat endpoint (POST /chat)
- Suggest endpoint (POST /suggest)
- History endpoint (GET /history/{user_id})

### Error Handling Tests

To run the error handling tests:

```bash
pytest test_error_handling.py -v
```

These tests verify that the API handles errors gracefully, including:
- Malformed JSON
- Missing required fields
- Invalid user_id format
- Invalid data format
- Non-existent endpoints
- Method not allowed
- Too large payloads
- Fallback mode behavior

### Memory Functionality Tests

To run the memory functionality tests:

```bash
pytest test_memory_functionality.py -v
```

These tests verify that the API correctly stores and retrieves conversation context, including:
- Memory retrieval in conversations
- Memory persistence across sessions
- Fallback memory storage
- History endpoint with memory functionality
- Context influence on responses

### Performance Tests

To run the performance tests:

```bash
locust -f locustfile.py --host=https://uri-genai.fly.dev
```

Then open http://localhost:8089 in your browser to access the Locust web interface. From there, you can:
1. Set the number of users to simulate
2. Set the spawn rate (users per second)
3. Start the test and monitor results in real-time

The performance tests simulate realistic user behavior, including:
- Sending chat messages
- Following up on previous conversations
- Using the suggest endpoint
- Retrieving chat history

### Security Tests

To run the security tests:

```bash
pytest test_security.py -v
```

These tests verify that the API is secure, including:
- XSS input validation
- SQL injection input validation
- Rate limiting
- Data privacy
- Authorization
- Large payload handling

## Running All Tests

To run all the API tests (excluding performance tests):

```bash
pytest test_api_endpoints.py test_error_handling.py test_memory_functionality.py test_security.py -v
```

To generate an HTML report of the test results:

```bash
pytest test_api_endpoints.py test_error_handling.py test_memory_functionality.py test_security.py --html=report.html
```

## Test Configuration

By default, the tests run against the production API at https://uri-genai.fly.dev. To run the tests against a local instance:

```bash
export TEST_API_URL=http://localhost:8080
pytest test_api_endpoints.py -v
```

## Interpreting Test Results

### API Endpoint Tests

- All tests should pass with status code 200 for valid requests
- The chat endpoint should return appropriate responses with follow-up suggestions
- The suggest endpoint should return relevant suggestions
- The history endpoint should return the user's chat history

### Error Handling Tests

- The API should return appropriate error codes for invalid requests
- The API should handle edge cases gracefully
- The API should fall back to in-memory storage when Milvus is unavailable
- The API should provide fallback responses when Ollama is unavailable

### Memory Functionality Tests

- The API should maintain context across multiple messages in a conversation
- The API should persist memory across sessions
- The API should fall back to in-memory storage when necessary
- The history endpoint should return all messages for a user

### Performance Tests

- The API should handle multiple concurrent users
- Response times should be reasonable (< 2 seconds for most requests)
- The API should not crash under load
- Cached responses should be significantly faster than uncached responses

### Security Tests

- The API should sanitize user input to prevent XSS attacks
- The API should handle SQL injection attempts as normal text
- The API should implement rate limiting for high request rates
- The API should not echo sensitive data back in responses
- The API should restrict access to user data
- The API should handle unusually large payloads appropriately

## Troubleshooting

If you encounter issues running the tests:

1. Make sure all dependencies are installed
2. Check that the API is running and accessible
3. Check the API URL in the test configuration
4. Increase timeouts for slow connections
5. Run tests with the `-v` flag for more detailed output

## Adding New Tests

To add new tests:

1. Create a new test file or add tests to an existing file
2. Use the pytest framework and httpx for making HTTP requests
3. Follow the existing test patterns
4. Add the new test to the appropriate test category
5. Update this README.md file with information about the new test