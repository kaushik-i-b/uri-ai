"""
Memory Manager Module

This module implements a memory manager for storing and retrieving chat memories.
It uses Milvus for vector similarity search with a fallback to in-memory storage.

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
from pymilvus import (
    connections,
    utility,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType
)
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryManager:
    """Manager for Milvus-based vector memory store with fallback to in-memory storage."""
    
    def __init__(self, host: str = "localhost", port: str = "19530", collection_name: str = "chat_memories", 
                 cache_size: int = 128):
        """
        Initialize the memory manager with Milvus.
        If Milvus is not available, falls back to in-memory storage.
        
        Args:
            host: Milvus server host
            port: Milvus server port
            collection_name: Name of the collection to store chat memories
            cache_size: Size of the LRU cache for embeddings and search results
        """
        # Initialize sentence transformer model for embeddings
        self.model = SentenceTransformer("all-MiniLM-L6-v2")  # Lightweight but effective model
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        self.collection_name = collection_name
        self.cache_size = cache_size
        
        # Fallback in-memory storage
        self.fallback_mode = False
        self.memory_store = {}  # Dict to store memories by user_id
        
        # Cache for search results (user_id, query) -> results
        self.search_cache = {}
        
        # Setup LRU cache for embeddings
        self.get_embedding = lru_cache(maxsize=cache_size)(self._get_embedding)
        
        try:
            # Initialize connection to Milvus
            connections.connect(
                alias="default", 
                host=host, 
                port=port
            )
            
            # Create collection if it doesn't exist
            if not utility.has_collection(collection_name):
                self._create_collection()
            
            # Get the collection
            self.collection = Collection(collection_name)
            self.collection.load()
            
            logger.info(f"Initialized Milvus connection to {host}:{port} with collection {collection_name}")
            
        except Exception as e:
            logger.warning(f"Error initializing Milvus: {str(e)}")
            logger.warning("Falling back to in-memory storage. Memory will not persist between restarts.")
            self.fallback_mode = True
    
    def _create_collection(self):
        """Create the Milvus collection with the appropriate schema."""
        # Define fields for the collection
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
            FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="prompt", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="reply", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim)
        ]
        
        # Create collection schema
        schema = CollectionSchema(fields=fields, description="Chat memory collection")
        
        # Create collection
        collection = Collection(name=self.collection_name, schema=schema)
        
        # Create index for vector field
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 8, "efConstruction": 64}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        logger.info(f"Created Milvus collection {self.collection_name} with schema and index")
    
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
            
            if self.fallback_mode:
                # Use in-memory storage in fallback mode
                if user_id not in self.memory_store:
                    self.memory_store[user_id] = []
                
                # Generate a memory ID
                memory_id = f"{user_id}_{len(self.memory_store[user_id]) + 1}"
                
                # Store the memory
                self.memory_store[user_id].append({
                    "id": memory_id,
                    "prompt": prompt,
                    "reply": reply,
                    "embedding": embedding,
                    "combined_text": combined_text
                })
                
                logger.debug(f"Added memory for user {user_id} (fallback mode)")
                return True
            else:
                # Use Milvus in normal mode
                # Generate a unique ID for this memory
                # Query to count existing records for this user
                self.collection.flush()  # Ensure all data is visible
                count_expr = f"user_id == '{user_id}'"
                result = self.collection.query(expr=count_expr, output_fields=["count(*)"])
                count = len(result) if result else 0
                memory_id = f"{user_id}_{count + 1}"
                
                # Prepare data to insert
                data = [
                    [memory_id],                # id
                    [user_id],                  # user_id
                    [prompt],                   # prompt
                    [reply],                    # reply
                    [embedding]                 # embedding
                ]
                
                # Insert data into collection
                self.collection.insert(data)
                self.collection.flush()  # Ensure data is persisted
                
                logger.debug(f"Added memory for user {user_id}")
                return True
            
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
            
            if self.fallback_mode:
                # Use in-memory storage in fallback mode
                memories = []
                
                # Check if user has any memories
                if user_id not in self.memory_store or not self.memory_store[user_id]:
                    logger.debug(f"No memories found for user {user_id} (fallback mode)")
                    return []
                
                # Calculate cosine similarity for each memory
                user_memories = self.memory_store[user_id]
                similarities = []
                
                for memory in user_memories:
                    # Calculate cosine similarity between query and memory embeddings
                    memory_embedding = memory["embedding"]
                    similarity = self._cosine_similarity(query_embedding, memory_embedding)
                    similarities.append((memory, similarity))
                
                # Sort by similarity (highest first) and take top 'limit' results
                similarities.sort(key=lambda x: x[1], reverse=True)
                top_memories = similarities[:limit]
                
                # Format the results
                for memory, distance in top_memories:
                    memories.append({
                        "text": f"User: {memory['prompt']}\nAI: {memory['reply']}",
                        "prompt": memory["prompt"],
                        "reply": memory["reply"],
                        "distance": distance
                    })
                
                # Only log at debug level to reduce overhead
                logger.debug(f"Retrieved {len(memories)} memories for user {user_id} (fallback mode)")
                
                # Cache the results
                self.search_cache[cache_key] = memories
                return memories
            else:
                # Use Milvus in normal mode
                # Search parameters
                search_params = {
                    "metric_type": "COSINE",
                    "params": {"ef": 64}
                }
                
                # Filter expression for user_id
                expr = f"user_id == '{user_id}'"
                
                # Search for similar vectors
                results = self.collection.search(
                    data=[query_embedding],
                    anns_field="embedding",
                    param=search_params,
                    limit=limit,
                    expr=expr,
                    output_fields=["prompt", "reply"]
                )
                
                # Format the results
                memories = []
                if results and len(results) > 0:
                    for hits in results:
                        for hit in hits:
                            memories.append({
                                "text": f"User: {hit.entity.get('prompt')}\nAI: {hit.entity.get('reply')}",
                                "prompt": hit.entity.get("prompt", ""),
                                "reply": hit.entity.get("reply", ""),
                                "distance": hit.distance
                            })
                
                # Only log at debug level to reduce overhead
                logger.debug(f"Retrieved {len(memories)} memories for user {user_id}")
                
                # Cache the results
                self.search_cache[cache_key] = memories
                return memories
            
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
            if self.fallback_mode:
                # Use in-memory storage in fallback mode
                if user_id in self.memory_store:
                    # Clear memories for this user
                    self.memory_store[user_id] = []
                    logger.info(f"Cleared all memories for user {user_id} (fallback mode)")
                else:
                    logger.info(f"No memories found for user {user_id} (fallback mode)")
                return True
            else:
                # Use Milvus in normal mode
                # Delete expression for user_id
                expr = f"user_id == '{user_id}'"
                
                # Delete all memories for this user
                self.collection.delete(expr)
                self.collection.flush()  # Ensure deletion is persisted
                
                logger.info(f"Cleared all memories for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Error clearing user memories: {str(e)}")
            return False