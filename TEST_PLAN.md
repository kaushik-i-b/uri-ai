# Test Plan for Deployed Mental Health Assistant API

## 1. Test Objectives

This test plan outlines comprehensive testing scenarios for the Mental Health Assistant API deployed on Fly.io. The objectives are to:

- Verify that all API endpoints function correctly in the production environment
- Ensure the application handles errors gracefully and falls back appropriately when services are unavailable
- Validate performance under various load conditions
- Confirm that security measures are properly implemented
- Test data persistence and memory functionality

## 2. Test Environments

### Production Environment
- **URL**: https://uri-genai.fly.dev
- **Infrastructure**: Fly.io hosting
- **Configuration**: As defined in fly.toml

### Local Testing Environment
- **URL**: http://localhost:8080
- **Infrastructure**: Local development machine
- **Configuration**: As defined in .env file

## 3. Test Data Requirements

- Test user IDs for different scenarios
- Sample user inputs of varying lengths and content
- Crisis-indicating text samples
- Non-crisis text samples
- Partial input samples for suggestion testing

## 4. Test Scenarios

### 4.1 Basic Functionality Tests

#### 4.1.1 API Endpoint Tests

| Test ID | Endpoint | Description | Test Data | Expected Result |
|---------|----------|-------------|-----------|----------------|
| API-01 | GET / | Test root endpoint | N/A | 200 OK with API information |
| API-02 | POST /chat | Test with normal input | {"user_input": "I've been feeling stressed", "user_id": "test_user_1"} | 200 OK with appropriate response and follow-up suggestions |
| API-03 | POST /chat | Test with crisis indicators | {"user_input": "I don't want to live anymore", "user_id": "test_user_2"} | 200 OK with crisis resources included |
| API-04 | POST /chat | Test with empty input | {"user_input": "", "user_id": "test_user_3"} | 400 Bad Request or appropriate error message |
| API-05 | POST /chat | Test with very long input | {"user_input": "[5000 character text]", "user_id": "test_user_4"} | 200 OK with appropriate response |
| API-06 | POST /suggest | Test with empty input | {"partial_input": "", "user_id": "test_user_5"} | 200 OK with default suggestions |
| API-07 | POST /suggest | Test with partial input | {"partial_input": "How to deal with anx", "user_id": "test_user_6"} | 200 OK with relevant suggestions |
| API-08 | POST /suggest | Test with custom max_suggestions | {"partial_input": "I feel", "user_id": "test_user_7", "max_suggestions": 5} | 200 OK with 5 suggestions |
| API-09 | GET /history/{user_id} | Test history retrieval | user_id=test_user_8 | 200 OK with chat history |

#### 4.1.2 Memory Functionality Tests

| Test ID | Description | Test Data | Expected Result |
|---------|-------------|-----------|----------------|
| MEM-01 | Test memory retrieval | Multiple chat messages with same user_id | Context from previous messages included in responses |
| MEM-02 | Test memory persistence | Chat messages, server restart, more chat messages | Context maintained across restarts (if using external Milvus) |
| MEM-03 | Test fallback to in-memory storage | Configure with invalid Milvus host | Application uses in-memory storage without errors |

### 4.2 Error Handling and Fallback Tests

| Test ID | Description | Test Data | Expected Result |
|---------|-------------|-----------|----------------|
| ERR-01 | Test Ollama connection failure | Configure with invalid Ollama URL | Fallback responses provided |
| ERR-02 | Test Milvus connection failure | Configure with invalid Milvus host | Fallback to in-memory storage |
| ERR-03 | Test with malformed JSON | Send invalid JSON to /chat endpoint | 400 Bad Request with clear error message |
| ERR-04 | Test with missing required fields | {"user_id": "test_user_9"} to /chat endpoint | 422 Unprocessable Entity with clear error message |
| ERR-05 | Test with invalid user_id format | {"user_input": "Hello", "user_id": ""} | Appropriate error response |

### 4.3 Performance Tests

| Test ID | Description | Test Parameters | Expected Result |
|---------|-------------|-----------------|----------------|
| PERF-01 | Response time test | 100 sequential requests | Average response time < 2 seconds |
| PERF-02 | Concurrent users test | 10 concurrent users, 10 requests each | All requests successful, response time < 5 seconds |
| PERF-03 | Memory usage test | Monitor during high load | Memory usage remains stable |
| PERF-04 | Cache effectiveness test | Repeated identical requests | Significant improvement in response time for cached requests |
| PERF-05 | Long-running stability test | 1000 requests over 1 hour | No degradation in performance, no memory leaks |

### 4.4 Security Tests

| Test ID | Description | Test Data | Expected Result |
|---------|-------------|-----------|----------------|
| SEC-01 | Input validation | {"user_input": "<script>alert('XSS')</script>", "user_id": "test_user_10"} | Input sanitized, no XSS vulnerability |
| SEC-02 | Rate limiting | 100 requests in 10 seconds from same IP | Rate limiting applied after threshold |
| SEC-03 | Data privacy | Monitor network traffic | Sensitive data not exposed in logs or responses |
| SEC-04 | Authorization | Access protected endpoints without credentials | Appropriate authentication errors |

## 5. Test Implementation

### 5.1 Automated API Tests

We have implemented automated API tests using Python with the `pytest` and `httpx` libraries. The tests are organized in the following files:

- `tests/test_api_endpoints.py`: Tests for all API endpoints
- `tests/test_error_handling.py`: Tests for error handling and fallback mechanisms
- `tests/test_memory_functionality.py`: Tests for memory and context functionality

### 5.2 Performance Tests

Performance tests are implemented using `locust`, a Python-based load testing tool. The tests are defined in:

- `tests/locustfile.py`: Defines user behavior and load testing scenarios

### 5.3 Security Tests

Security tests are implemented using automated scripts:

- `tests/test_security.py`: Tests for input validation, rate limiting, and data privacy

## 6. Test Execution

### 6.1 Prerequisites

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

### 6.2 Running the Tests

#### API Tests
```bash
cd tests
pytest test_api_endpoints.py -v
pytest test_error_handling.py -v
pytest test_memory_functionality.py -v
```

#### Performance Tests
```bash
cd tests
locust -f locustfile.py --host=https://uri-genai.fly.dev
```

Then open http://localhost:8089 in your browser to access the Locust web interface.

#### Security Tests
```bash
cd tests
pytest test_security.py -v
```

#### Running All Tests
```bash
cd tests
pytest test_api_endpoints.py test_error_handling.py test_memory_functionality.py test_security.py -v
```

#### Test Configuration

By default, the tests run against the production API at https://uri-genai.fly.dev. To run the tests against a local instance:

```bash
export TEST_API_URL=http://localhost:8080
pytest test_api_endpoints.py -v
```

### 6.3 Test Reports

Test results can be collected and reported in the following formats:

- HTML reports for human readability:
  ```bash
  pytest test_api_endpoints.py test_error_handling.py test_memory_functionality.py test_security.py --html=report.html
  ```

- JUnit XML for CI/CD integration:
  ```bash
  pytest test_api_endpoints.py test_error_handling.py test_memory_functionality.py test_security.py --junitxml=report.xml
  ```

- Coverage reports:
  ```bash
  pytest test_api_endpoints.py test_error_handling.py test_memory_functionality.py test_security.py --cov=../
  ```

For more detailed information on running the tests and interpreting the results, please refer to the `tests/README.md` file.

## 7. Test Maintenance

The test suite should be maintained and updated when:

- New features are added to the application
- Bugs are fixed
- API endpoints are modified
- Dependencies are updated

## 8. Conclusion

This test plan provides a comprehensive approach to testing the Mental Health Assistant API deployed on Fly.io. By executing these tests, we can ensure that the application functions correctly, performs well under load, handles errors gracefully, and maintains security in the production environment.