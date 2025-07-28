import logging
from typing import Dict, Tuple, List, Union
from detoxify import Detoxify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CrisisDetector:
    """
    Crisis detection layer using the Detoxify model to identify potential self-harm or suicidal content.
    """
    
    def __init__(self):
        """Initialize the crisis detector with the Detoxify model."""
        logger.info("Loading Detoxify model for crisis detection...")
        self.model = Detoxify('original')
        self.crisis_threshold = 0.7  # Threshold for triggering crisis detection
        
        # Keywords that might indicate crisis situations
        self.crisis_keywords = [
            "suicide", "kill myself", "end my life", "don't want to live",
            "self-harm", "hurt myself", "cutting myself", "harming myself",
            "overdose", "take all my pills", "jump off", "hang myself"
        ]
        
    def check_text(self, text: str) -> Tuple[bool, Dict[str, float]]:
        """
        Check if the text contains crisis indicators.
        
        Args:
            text: The text to analyze
            
        Returns:
            A tuple containing:
                - Boolean indicating if a crisis was detected
                - Dictionary with toxicity scores
        """
        try:
            # Run the text through Detoxify model
            results = self.model.predict(text)
            
            # Extract relevant scores
            toxicity_score = results.get('toxicity', 0)
            severe_toxicity_score = results.get('severe_toxicity', 0)
            
            # Check for crisis keywords
            keyword_detected = any(keyword in text.lower() for keyword in self.crisis_keywords)
            
            # Determine if this is a crisis situation
            is_crisis = (
                toxicity_score > self.crisis_threshold or
                severe_toxicity_score > self.crisis_threshold * 0.8 or
                keyword_detected
            )
            
            if is_crisis:
                logger.warning(f"Crisis detected in text: {text[:100]}...")
            
            return is_crisis, results
            
        except Exception as e:
            logger.error(f"Error in crisis detection: {str(e)}")
            # Default to treating as potential crisis when errors occur
            return True, {"error": str(e)}
    
    def get_crisis_resources(self) -> Dict[str, str]:
        """
        Return crisis resources that can be provided to users in crisis.
        
        Returns:
            Dictionary of crisis resources
        """
        return {
            "national_suicide_prevention_lifeline": "1-800-273-8255",
            "crisis_text_line": "Text HOME to 741741",
            "international": "https://findahelpline.com/",
            "message": "If you're in immediate danger, please call emergency services (911 in the US) right away."
        }