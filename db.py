from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime

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