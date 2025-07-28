"""
Performance Test Script

This script tests the performance of the memory manager with the optimizations implemented.
It measures the time taken to perform common operations and prints the results.
"""

import time
import asyncio
from memory import MemoryManager
import logging

# Configure logging to show only warnings and errors during the test
logging.basicConfig(level=logging.WARNING)

async def test_memory_performance():
    """Test the performance of the memory manager."""
    print("Starting memory manager performance test...")
    
    # Initialize memory manager with fallback mode (since Milvus might not be available)
    memory_manager = MemoryManager(host="localhost", port="19530")
    
    # Test data
    user_id = "test_performance_user"
    prompts = [
        "How can I manage stress at work?",
        "What are some relaxation techniques?",
        "How does meditation help with anxiety?",
        "What are the symptoms of depression?",
        "How can I improve my sleep quality?",
        "What are some healthy coping mechanisms for stress?",
        "How can I support a friend with mental health issues?",
        "What's the difference between anxiety and stress?",
        "How can I practice mindfulness in daily life?",
        "What are some exercises to improve mental health?"
    ]
    replies = [
        "There are several ways to manage stress at work, including taking regular breaks, practicing deep breathing, and setting boundaries.",
        "Relaxation techniques include deep breathing, progressive muscle relaxation, visualization, and meditation.",
        "Meditation helps with anxiety by calming the mind, reducing stress hormones, and promoting a sense of peace and well-being.",
        "Symptoms of depression include persistent sadness, loss of interest in activities, changes in appetite or sleep, and feelings of worthlessness.",
        "To improve sleep quality, maintain a regular sleep schedule, create a relaxing bedtime routine, limit screen time before bed, and create a comfortable sleep environment.",
        "Healthy coping mechanisms for stress include exercise, talking to friends, practicing mindfulness, and engaging in hobbies.",
        "Support a friend with mental health issues by listening without judgment, encouraging professional help, and being patient and understanding.",
        "Anxiety is a specific reaction to a perceived threat, while stress is a response to demands or pressures.",
        "Practice mindfulness in daily life by focusing on the present moment during routine activities, like eating, walking, or washing dishes.",
        "Exercises to improve mental health include regular physical activity, yoga, tai chi, and even simple walking."
    ]
    
    # Test 1: Add memories and measure time
    print("\nTest 1: Adding memories to storage")
    start_time = time.time()
    
    for i in range(len(prompts)):
        memory_manager.add_to_memory(user_id, prompts[i], replies[i])
    
    add_time = time.time() - start_time
    print(f"Time to add {len(prompts)} memories: {add_time:.4f}s")
    
    # Test 2: Search memories first time (no cache)
    print("\nTest 2: Searching memories (first time, no cache)")
    search_queries = [
        "How can I deal with stress?",
        "Tell me about meditation",
        "What are symptoms of mental health issues?",
        "How can I sleep better?",
        "How to help a friend with depression?"
    ]
    
    start_time = time.time()
    
    for query in search_queries:
        memories = memory_manager.search_memory(user_id, query)
    
    first_search_time = time.time() - start_time
    print(f"Time for first search of {len(search_queries)} queries: {first_search_time:.4f}s")
    
    # Test 3: Search memories second time (with cache)
    print("\nTest 3: Searching memories (second time, with cache)")
    start_time = time.time()
    
    for query in search_queries:
        memories = memory_manager.search_memory(user_id, query)
    
    second_search_time = time.time() - start_time
    print(f"Time for second search of {len(search_queries)} queries: {second_search_time:.4f}s")
    print(f"Cache speedup: {first_search_time / second_search_time:.2f}x faster")
    
    # Test 4: Search with new queries (embedding cache, but no search cache)
    print("\nTest 4: Searching with new but similar queries (embedding cache only)")
    similar_queries = [
        "How can I manage stress at my job?",
        "Tell me about meditation techniques",
        "What are common symptoms of mental health problems?",
        "How can I improve my sleep?",
        "How to support someone with depression?"
    ]
    
    start_time = time.time()
    
    for query in similar_queries:
        memories = memory_manager.search_memory(user_id, query)
    
    similar_search_time = time.time() - start_time
    print(f"Time for search with similar queries: {similar_search_time:.4f}s")
    
    # Test 5: Add a new memory and verify cache invalidation
    print("\nTest 5: Adding new memory and verifying cache invalidation")
    new_prompt = "What is the importance of self-care?"
    new_reply = "Self-care is essential for maintaining good physical and mental health. It includes activities that reduce stress and enhance well-being."
    
    memory_manager.add_to_memory(user_id, new_prompt, new_reply)
    
    # Search again with a previous query to check if cache was invalidated
    test_query = search_queries[0]
    start_time = time.time()
    
    memories = memory_manager.search_memory(user_id, test_query)
    
    invalidation_time = time.time() - start_time
    print(f"Time for search after adding new memory: {invalidation_time:.4f}s")
    print(f"Number of memories found: {len(memories)}")
    
    print("\nPerformance test completed.")

if __name__ == "__main__":
    asyncio.run(test_memory_performance())