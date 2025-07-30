from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime
import json
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define SQLite database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./chat_history.db"

# Create SQLAlchemy engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

class ChatLog(Base):
    """Model for storing chat history."""
    
    __tablename__ = "chat_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    prompt = Column(Text, nullable=False)
    reply = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<ChatLog(id={self.id}, user_id={self.user_id}, timestamp={self.timestamp})>"

class VectorMemory(Base):
    """Model for storing vector embeddings for semantic search."""
    
    __tablename__ = "vector_memories"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    prompt = Column(Text, nullable=False)
    reply = Column(Text, nullable=False)
    embedding = Column(Text, nullable=False)  # JSON serialized vector
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<VectorMemory(id={self.id}, user_id={self.user_id}, timestamp={self.timestamp})>"
    
    @property
    def embedding_vector(self):
        """Deserialize the embedding from JSON to a numpy array."""
        return np.array(json.loads(self.embedding))
    
    @embedding_vector.setter
    def embedding_vector(self, vector):
        """Serialize the embedding from a numpy array or list to JSON."""
        if isinstance(vector, np.ndarray):
            vector = vector.tolist()
        self.embedding = json.dumps(vector)

# Create all tables in the database
Base.metadata.create_all(bind=engine)

def get_db():
    """
    Get a database session.
    
    Yields:
        Session: A SQLAlchemy session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def log_chat(db, user_id: str, prompt: str, reply: str):
    """
    Log a chat interaction to the database.
    
    Args:
        db: SQLAlchemy database session
        user_id: User identifier
        prompt: User's message
        reply: AI's response
        
    Returns:
        ChatLog: The created chat log entry
    """
    try:
        chat_log = ChatLog(
            user_id=user_id,
            prompt=prompt,
            reply=reply
        )
        db.add(chat_log)
        db.commit()
        db.refresh(chat_log)
        logger.info(f"Logged chat for user {user_id}")
        return chat_log
    except Exception as e:
        db.rollback()
        logger.error(f"Error logging chat: {str(e)}")
        raise

def get_user_chat_history(db, user_id: str, limit: int = 50):
    """
    Retrieve chat history for a specific user.
    
    Args:
        db: SQLAlchemy database session
        user_id: User identifier
        limit: Maximum number of records to return
        
    Returns:
        List[ChatLog]: List of chat log entries
    """
    try:
        chat_logs = db.query(ChatLog).filter(
            ChatLog.user_id == user_id
        ).order_by(
            ChatLog.timestamp.desc()
        ).limit(limit).all()
        
        return chat_logs
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        raise

def add_vector_memory(db, user_id: str, prompt: str, reply: str, embedding, memory_id: str = None):
    """
    Add a vector memory to the database.
    
    Args:
        db: SQLAlchemy database session
        user_id: User identifier
        prompt: User's message
        reply: AI's response
        embedding: Vector embedding (numpy array or list)
        memory_id: Optional custom ID for the memory
        
    Returns:
        VectorMemory: The created vector memory entry
    """
    try:
        # Generate a memory ID if not provided
        if memory_id is None:
            # Count existing memories for this user to generate an ID
            count = db.query(VectorMemory).filter(
                VectorMemory.user_id == user_id
            ).count()
            memory_id = f"{user_id}_{count + 1}"
        
        # Create the vector memory
        vector_memory = VectorMemory(
            id=memory_id,
            user_id=user_id,
            prompt=prompt,
            reply=reply
        )
        
        # Set the embedding using the property setter
        vector_memory.embedding_vector = embedding
        
        # Add to database
        db.add(vector_memory)
        db.commit()
        db.refresh(vector_memory)
        
        logger.debug(f"Added vector memory for user {user_id}")
        return vector_memory
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding vector memory: {str(e)}")
        raise

def search_vector_memories(db, user_id: str, query_embedding, limit: int = 2):
    """
    Search for vector memories by similarity.
    
    Args:
        db: SQLAlchemy database session
        user_id: User identifier
        query_embedding: Query vector embedding (numpy array or list)
        limit: Maximum number of results to return
        
    Returns:
        List[Tuple[VectorMemory, float]]: List of (memory, similarity) tuples
    """
    try:
        # Get all memories for this user
        memories = db.query(VectorMemory).filter(
            VectorMemory.user_id == user_id
        ).all()
        
        if not memories:
            return []
        
        # Convert query embedding to numpy array if it's not already
        if not isinstance(query_embedding, np.ndarray):
            query_embedding = np.array(query_embedding)
        
        # Calculate cosine similarity for each memory
        results = []
        for memory in memories:
            # Get the memory embedding
            memory_embedding = memory.embedding_vector
            
            # Calculate cosine similarity
            dot_product = np.dot(query_embedding, memory_embedding)
            norm_query = np.linalg.norm(query_embedding)
            norm_memory = np.linalg.norm(memory_embedding)
            
            # Avoid division by zero
            if norm_query == 0 or norm_memory == 0:
                similarity = 0
            else:
                similarity = dot_product / (norm_query * norm_memory)
            
            results.append((memory, similarity))
        
        # Sort by similarity (highest first) and take top 'limit' results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    except Exception as e:
        logger.error(f"Error searching vector memories: {str(e)}")
        raise

def clear_user_vector_memories(db, user_id: str):
    """
    Clear all vector memories for a specific user.
    
    Args:
        db: SQLAlchemy database session
        user_id: User identifier
        
    Returns:
        int: Number of deleted memories
    """
    try:
        # Delete all memories for this user
        result = db.query(VectorMemory).filter(
            VectorMemory.user_id == user_id
        ).delete()
        
        db.commit()
        logger.info(f"Cleared {result} vector memories for user {user_id}")
        return result
    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing vector memories: {str(e)}")
        raise