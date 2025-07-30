"""
Memory Manager Module

This module implements a memory manager for storing and retrieving chat memories.
It uses SQLite for vector storage and retrieval.

Performance optimizations implemented:
1. LRU cache for embeddings generation to avoid redundant encoding
2. Cache for search results to avoid redundant searches
3. Reduced logging overhead by changing most log messages to DEBUG level
4. Performance measurement for tracking operation times
5. Cache invalidation when new memories are added to ensure consistency
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import os
import numpy as np
import time
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from db import (
    get_db, 
    add_vector_memory, 
    search_vector_memories, 
    clear_user_vector_memories,
    SessionLocal
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryManager:
    """Manager for SQLite-based vector memory store."""
    
    def __init__(self, cache_size: int = 128):
        """
        Initialize the memory manager with SQLite.
        
        Args:
            cache_size: Size of the LRU cache for embeddings and search results
        """
        # Initialize sentence transformer model for embeddings
        self.model = SentenceTransformer("all-MiniLM-L6-v2")  # Lightweight but effective model
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        self.cache_size = cache_size
        
        # Cache for search results (user_id, query) -> results
        self.search_cache = {}
        
        # Setup LRU cache for embeddings
        self.get_embedding = lru_cache(maxsize=cache_size)(self._get_embedding)
        
        logger.info("Initialized SQLite-based memory manager")
    
    def add_to_memory(self, user_id: str, prompt: str, reply: str) -> bool:
        """
        Add a chat interaction to the memory.
        
        Args:
            user_id: User identifier
            prompt: User's message
            reply: AI's response
            
        Returns:
            bool: True if successful, False otherwise
        """
        start_time = time.time()
        try:
            # Create a combined text for embedding
            combined_text = f"User: {prompt}\nAI: {reply}"
            
            # Generate embedding for the combined text using cached method
            embedding = self.get_embedding(combined_text)
            
            # Clear search cache for this user as new memory is added
            # This ensures future searches will include this new memory
            self.search_cache = {k: v for k, v in self.search_cache.items() if k[0] != user_id}
            
            # Get a database session
            db = SessionLocal()
            try:
                # Add the memory to the database
                add_vector_memory(db, user_id, prompt, reply, embedding)
                logger.debug(f"Added memory for user {user_id}")
                return True
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error adding to memory: {str(e)}")
            elapsed = time.time() - start_time
            logger.debug(f"Memory addition failed in {elapsed:.4f}s")
            return False
            
        finally:
            # Log operation time at debug level if not already logged in except block
            if 'elapsed' not in locals():
                elapsed = time.time() - start_time
                logger.debug(f"Memory addition completed in {elapsed:.4f}s")
    
    def search_memory(self, user_id: str, query: str, limit: int = 2) -> List[Dict[str, Any]]:
        """
        Search for relevant memories based on semantic similarity.
        
        Args:
            user_id: User identifier
            query: The query text to search for
            limit: Maximum number of results to return
            
        Returns:
            List of relevant memories with their metadata
        """
        # Check cache first
        cache_key = (user_id, query, limit)
        if cache_key in self.search_cache:
            logger.debug(f"Cache hit for search: user={user_id}, query={query[:20]}...")
            return self.search_cache[cache_key]
        
        start_time = time.time()
        try:
            # Generate embedding for the query using cached method
            query_embedding = self.get_embedding(query)
            
            # Get a database session
            db = SessionLocal()
            try:
                # Search for similar memories in the database
                memory_results = search_vector_memories(db, user_id, query_embedding, limit)
                
                # Format the results
                memories = []
                for memory, similarity in memory_results:
                    memories.append({
                        "text": f"User: {memory.prompt}\nAI: {memory.reply}",
                        "prompt": memory.prompt,
                        "reply": memory.reply,
                        "distance": similarity
                    })
                
                # Only log at debug level to reduce overhead
                logger.debug(f"Retrieved {len(memories)} memories for user {user_id}")
                
                # Cache the results
                self.search_cache[cache_key] = memories
                return memories
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error searching memory: {str(e)}")
            elapsed = time.time() - start_time
            logger.debug(f"Memory search failed in {elapsed:.4f}s")
            return []
            
        finally:
            # Log search time at debug level if not already logged in except block
            if 'elapsed' not in locals():
                elapsed = time.time() - start_time
                logger.debug(f"Memory search completed in {elapsed:.4f}s")
            
    def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for the given text.
        This method is wrapped with lru_cache in __init__ to provide caching.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of embedding values
        """
        return self.model.encode(text).tolist()
    
    def _cosine_similarity(self, vec1, vec2):
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (higher is more similar)
        """
        # Convert to numpy arrays if they aren't already
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm_vec1 = np.linalg.norm(vec1)
        norm_vec2 = np.linalg.norm(vec2)
        
        # Avoid division by zero
        if norm_vec1 == 0 or norm_vec2 == 0:
            return 0
            
        similarity = dot_product / (norm_vec1 * norm_vec2)
        return similarity
    
    def format_context(self, memories: List[Dict[str, Any]]) -> str:
        """
        Format memories into a context string for the LLM.
        
        Args:
            memories: List of memory objects
            
        Returns:
            Formatted context string
        """
        if not memories:
            return ""
        
        context = "Here are some relevant previous interactions:\n\n"
        for i, memory in enumerate(memories):
            context += f"Memory {i+1}:\n"
            context += f"User: {memory.get('prompt', '')}\n"
            context += f"AI: {memory.get('reply', '')}\n\n"
        
        return context
    
    def clear_user_memories(self, user_id: str) -> bool:
        """
        Clear all memories for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get a database session
            db = SessionLocal()
            try:
                # Clear memories for this user
                count = clear_user_vector_memories(db, user_id)
                
                # Clear search cache for this user
                self.search_cache = {k: v for k, v in self.search_cache.items() if k[0] != user_id}
                
                logger.info(f"Cleared {count} memories for user {user_id}")
                return True
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error clearing user memories: {str(e)}")
            return False