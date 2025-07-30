"""
Performance and Load Testing for Mental Health Assistant API

This module contains load tests for the Mental Health Assistant API using Locust.
It simulates user behavior and measures response times under various load conditions.

To run:
    locust -f locustfile.py --host=https://uri-genai.fly.dev
    Then open http://localhost:8089 in your browser
"""

import time
import random
import uuid
import json
from locust import HttpUser, task, between, events

# Sample user inputs for testing
NORMAL_INPUTS = [
    "I've been feeling stressed lately with work. Do you have any relaxation techniques?",
    "I'm having trouble sleeping at night. What can I do to improve my sleep?",
    "I feel anxious when I have to speak in public. How can I manage this anxiety?",
    "I've been feeling down for the past few weeks. What are some ways to improve my mood?",
    "I'm struggling with work-life balance. Any suggestions?",
    "I find it hard to concentrate on my tasks. How can I improve my focus?",
    "I'm worried about my upcoming exams. How can I manage exam stress?",
    "I've been feeling overwhelmed with my responsibilities. How can I cope?",
    "I'm having relationship problems with my partner. How can we communicate better?",
    "I'm trying to build healthier habits. What's a good approach?"
]

PARTIAL_INPUTS = [
    "How to deal with anx",
    "I feel",
    "What are some techniques for",
    "Can you recommend",
    "How do I cope with",
    "What should I do when",
    "Is it normal to feel",
    "How can I improve my",
    "What are the symptoms of",
    "How to talk to someone about"
]

class UserBehavior(HttpUser):
    """Simulates user behavior for the Mental Health Assistant API."""
    
    # Wait between 3 and 10 seconds between tasks
    wait_time = between(3, 10)
    
    def on_start(self):
        """Initialize user session."""
        # Generate a unique user ID for this session
        self.user_id = f"locust_test_user_{uuid.uuid4().hex[:8]}"
        self.conversation_history = []
        
        # Log the start of a new user session
        print(f"Starting new user session with ID: {self.user_id}")
    
    @task(3)
    def chat_normal_input(self):
        """Send a normal chat message (most common task)."""
        # Select a random input from the list
        user_input = random.choice(NORMAL_INPUTS)
        
        # Send the request
        start_time = time.time()
        with self.client.post(
            "/chat",
            json={"user_input": user_input, "user_id": self.user_id},
            catch_response=True,
            timeout=30.0
        ) as response:
            duration = time.time() - start_time
            
            if response.status_code == 200:
                # Store the conversation for potential follow-up
                try:
                    data = response.json()
                    self.conversation_history.append({
                        "prompt": user_input,
                        "reply": data["reply"]
                    })
                    
                    # Trim history if it gets too long
                    if len(self.conversation_history) > 5:
                        self.conversation_history = self.conversation_history[-5:]
                    
                    # Log success with response time
                    response.success()
                    print(f"Chat request successful in {duration:.2f}s")
                except json.JSONDecodeError:
                    response.failure("Response could not be decoded as JSON")
            else:
                response.failure(f"Chat request failed with status code: {response.status_code}")
    
    @task(1)
    def chat_follow_up(self):
        """Send a follow-up message based on previous conversation."""
        # Only send follow-up if we have conversation history
        if not self.conversation_history:
            return
        
        # Get the last conversation
        last_conversation = self.conversation_history[-1]
        
        # Create a follow-up message
        follow_up_templates = [
            "Can you tell me more about {}?",
            "How can I implement the {} you mentioned?",
            "What if {} doesn't work for me?",
            "Are there alternatives to {}?",
            "Could you explain {} in more detail?"
        ]
        
        # Extract a keyword from the last reply
        keywords = last_conversation["reply"].split()
        if len(keywords) > 5:
            keyword = " ".join(random.sample(keywords, 3))
        else:
            keyword = random.choice(keywords) if keywords else "that"
        
        # Format the follow-up message
        follow_up = random.choice(follow_up_templates).format(keyword)
        
        # Send the request
        start_time = time.time()
        with self.client.post(
            "/chat",
            json={"user_input": follow_up, "user_id": self.user_id},
            catch_response=True,
            timeout=30.0
        ) as response:
            duration = time.time() - start_time
            
            if response.status_code == 200:
                # Store the conversation for potential future follow-up
                try:
                    data = response.json()
                    self.conversation_history.append({
                        "prompt": follow_up,
                        "reply": data["reply"]
                    })
                    
                    # Trim history if it gets too long
                    if len(self.conversation_history) > 5:
                        self.conversation_history = self.conversation_history[-5:]
                    
                    # Log success with response time
                    response.success()
                    print(f"Follow-up request successful in {duration:.2f}s")
                except json.JSONDecodeError:
                    response.failure("Response could not be decoded as JSON")
            else:
                response.failure(f"Follow-up request failed with status code: {response.status_code}")
    
    @task(2)
    def suggest_completion(self):
        """Test the suggest endpoint for autocomplete."""
        # Select a random partial input
        partial_input = random.choice(PARTIAL_INPUTS)
        
        # Send the request
        start_time = time.time()
        with self.client.post(
            "/suggest",
            json={"partial_input": partial_input, "user_id": self.user_id},
            catch_response=True,
            timeout=10.0
        ) as response:
            duration = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "suggestions" in data and isinstance(data["suggestions"], list):
                        response.success()
                        print(f"Suggest request successful in {duration:.2f}s")
                    else:
                        response.failure("Response does not contain suggestions list")
                except json.JSONDecodeError:
                    response.failure("Response could not be decoded as JSON")
            else:
                response.failure(f"Suggest request failed with status code: {response.status_code}")
    
    @task(1)
    def get_history(self):
        """Test the history endpoint."""
        # Only get history if we have sent at least one message
        if not self.conversation_history:
            return
        
        # Send the request
        start_time = time.time()
        with self.client.get(
            f"/history/{self.user_id}",
            catch_response=True,
            timeout=10.0
        ) as response:
            duration = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        response.success()
                        print(f"History request successful in {duration:.2f}s")
                    else:
                        response.failure("Response is not a list of chat logs")
                except json.JSONDecodeError:
                    response.failure("Response could not be decoded as JSON")
            else:
                response.failure(f"History request failed with status code: {response.status_code}")
    
    @task(0.5)
    def get_root(self):
        """Test the root endpoint."""
        # Send the request
        with self.client.get(
            "/",
            catch_response=True,
            timeout=5.0
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "message" in data and "status" in data:
                        response.success()
                    else:
                        response.failure("Response does not contain expected fields")
                except json.JSONDecodeError:
                    response.failure("Response could not be decoded as JSON")
            else:
                response.failure(f"Root request failed with status code: {response.status_code}")

# Custom event handlers for detailed reporting
@events.request_success.add_listener
def request_success_handler(request_type, name, response_time, response_length, **kwargs):
    """Log successful requests with detailed information."""
    print(f"Success: {request_type} {name} - Response time: {response_time:.2f}ms - Size: {response_length} bytes")

@events.request_failure.add_listener
def request_failure_handler(request_type, name, response_time, exception, **kwargs):
    """Log failed requests with detailed information."""
    print(f"Failure: {request_type} {name} - Response time: {response_time:.2f}ms - Exception: {str(exception)}")

@events.test_start.add_listener
def test_start_handler(environment, **kwargs):
    """Log when the test starts."""
    print(f"Test started with host: {environment.host}")

@events.test_stop.add_listener
def test_stop_handler(environment, **kwargs):
    """Log when the test stops."""
    print(f"Test stopped. Total time: {environment.runner.time():.2f}s")
    
    # Print summary statistics
    stats = environment.runner.stats
    print("\nTest Summary:")
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Median Response Time: {stats.total.median_response_time}ms")
    print(f"95th Percentile Response Time: {stats.total.get_response_time_percentile(0.95)}ms")
    print(f"Requests Per Second: {stats.total.current_rps}")