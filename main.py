"""
Oppuna Mental Health Assistant API

This module implements a FastAPI backend for the Oppuna mental health GenAI assistant.
Performance optimizations implemented:
1. Caching for embeddings generation using LRU cache
2. Caching for search results to avoid redundant searches
3. Parallelized operations in the /chat endpoint using asyncio.gather()
4. Reduced logging overhead by changing most log messages to DEBUG level
5. Performance measurement for tracking operation times
"""

from fastapi import FastAPI, HTTPException, Depends, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from ollama_client import OllamaClient
from crisis_check import CrisisDetector
from db import get_db, log_chat, get_user_chat_history, ChatLog
from memory import MemoryManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Oppuna Mental Health Assistant API",
    description="A FastAPI backend for the Oppuna mental health GenAI assistant",
    version="1.0.1"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
ollama_client = OllamaClient()
crisis_detector = CrisisDetector()

# Initialize memory manager with Milvus configuration
# Get Milvus configuration from environment variables or use defaults
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Milvus configuration
milvus_host = os.getenv("MILVUS_HOST", "localhost")
milvus_port = os.getenv("MILVUS_PORT", "19530")
milvus_collection = os.getenv("MILVUS_COLLECTION", "chat_memories")

# Initialize memory manager
memory_manager = MemoryManager(
    host=milvus_host,
    port=milvus_port,
    collection_name=milvus_collection
)

logger.info(f"Initialized Milvus memory manager with host={milvus_host}, port={milvus_port}, collection={milvus_collection}")

# Define request and response models
class ChatRequest(BaseModel):
    user_input: str
    user_id: str

class ChatResponse(BaseModel):
    reply: str
    crisis: bool
    follow_up_suggestions: Optional[List[str]] = None
    
class SuggestRequest(BaseModel):
    partial_input: str
    user_id: str
    max_suggestions: Optional[int] = 3
    
class SuggestResponse(BaseModel):
    suggestions: List[str]
    
class ChatLogResponse(BaseModel):
    id: int
    user_id: str
    prompt: str
    reply: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

@app.get("/")
async def root():
    return {
        "message": "Welcome to Oppuna Mental Health Assistant API",
        "status": "online",
        "endpoints": {
            "chat": "/chat - POST request with user_input and user_id. Response includes AI reply, crisis flag, and follow-up suggestions for continuing the conversation.",
            "suggest": "/suggest - POST request with partial_input and user_id for autocomplete suggestions"
        },
        "features": {
            "auto_suggestions": "The chat endpoint now provides follow-up suggestions to help users continue the conversation after receiving an AI response."
        }
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Process a chat request from the user and provide an AI response with follow-up suggestions.
    
    Args:
        request: ChatRequest containing user_input and user_id
        db: Database session
        
    Returns:
        ChatResponse with the AI reply, crisis flag, and follow-up suggestions for continuing the conversation
    """
    start_time = time.time()
    try:
        logger.info(f"Received chat request from user {request.user_id}")
        
        # Run crisis detection and memory retrieval in parallel
        crisis_task, memory_task = await asyncio.gather(
            # Task 1: Check for crisis indicators
            asyncio.create_task(_check_crisis(request.user_input)),
            # Task 2: Retrieve relevant memories
            asyncio.create_task(_get_memories(request.user_id, request.user_input))
        )
        
        # Unpack results
        is_crisis, toxicity_scores = crisis_task
        memories, context = memory_task
        
        # Prepare prompt with context if available
        prompt = request.user_input
        if context:
            prompt = f"{context}\nCurrent message: {request.user_input}"
            logger.debug(f"Added context from {len(memories)} previous interactions")
        
        # Generate response from LLM with context
        llm_response = await ollama_client.generate_response(
            prompt, 
            request.user_id
        )
        
        # If crisis is detected, append resources to the response
        if is_crisis:
            resources = crisis_detector.get_crisis_resources()
            resource_text = "\n\nI notice you may be going through a difficult time. " \
                           "Here are some resources that might help:\n" \
                           f"• National Suicide Prevention Lifeline: {resources['national_suicide_prevention_lifeline']}\n" \
                           f"• Crisis Text Line: {resources['crisis_text_line']}\n" \
                           f"{resources['message']}"
            
            llm_response += resource_text
        
        # Start generating follow-up suggestions in parallel with logging and storing
        suggestions_task = asyncio.create_task(
            ollama_client.generate_follow_up_suggestions(
                request.user_input,
                llm_response,
                request.user_id
            )
        )
        
        # Run logging and storing operations in parallel
        await asyncio.gather(
            # Task 1: Log the conversation to SQLite
            asyncio.create_task(_log_conversation(db, request.user_id, request.user_input, llm_response)),
            # Task 2: Store in memory for future context
            asyncio.create_task(_store_memory(request.user_id, request.user_input, llm_response))
        )
        
        # Wait for follow-up suggestions to complete
        follow_up_suggestions = await suggestions_task
        
        elapsed = time.time() - start_time
        logger.info(f"Chat request processed in {elapsed:.4f}s")
        
        return ChatResponse(
            reply=llm_response,
            crisis=is_crisis,
            follow_up_suggestions=follow_up_suggestions
        )
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error processing chat request in {elapsed:.4f}s: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request"
        )
        
@app.post("/suggest", response_model=SuggestResponse)
async def suggest(request: SuggestRequest):
    """
    Generate autocomplete suggestions based on partial user input.
    
    Args:
        request: SuggestRequest containing partial_input, user_id, and optional max_suggestions
        
    Returns:
        SuggestResponse with a list of suggestions
    """
    try:
        logger.info(f"Received suggestion request from user {request.user_id}")
        
        # Generate suggestions using the OllamaClient
        suggestions = await ollama_client.generate_suggestions(
            request.partial_input,
            request.user_id,
            request.max_suggestions
        )
        
        return SuggestResponse(
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"Error processing suggestion request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your suggestion request"
        )
        
# Helper functions for parallelized operations
async def _check_crisis(text: str) -> Tuple[bool, Dict[str, float]]:
    """Check for crisis indicators in text."""
    return crisis_detector.check_text(text)

async def _get_memories(user_id: str, query: str) -> Tuple[List[Dict[str, Any]], str]:
    """Retrieve and format relevant memories."""
    memories = memory_manager.search_memory(user_id, query)
    context = memory_manager.format_context(memories)
    return memories, context

async def _log_conversation(db: Session, user_id: str, prompt: str, reply: str) -> None:
    """Log conversation to database."""
    log_chat(db, user_id, prompt, reply)
    logger.debug(f"Logged conversation for user {user_id}")

async def _store_memory(user_id: str, prompt: str, reply: str) -> None:
    """Store conversation in memory manager."""
    memory_manager.add_to_memory(user_id, prompt, reply)
    logger.debug(f"Stored conversation in memory for user {user_id}")

@app.get("/history/{user_id}", response_model=List[ChatLogResponse])
async def get_history(user_id: str = Path(..., description="The user ID to retrieve history for"), 
                     limit: int = 50, 
                     db: Session = Depends(get_db)):
    """
    Retrieve chat history for a specific user.
    
    Args:
        user_id: The user ID to retrieve history for
        limit: Maximum number of records to return (default: 50)
        db: Database session
        
    Returns:
        List of chat log entries
    """
    try:
        logger.info(f"Retrieving chat history for user {user_id}")
        chat_logs = get_user_chat_history(db, user_id, limit)
        return chat_logs
        
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving chat history"
        )
