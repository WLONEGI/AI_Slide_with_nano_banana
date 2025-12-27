
from .vertex_wrapper import get_gemini
import logging
import random
from typing import List

logger = logging.getLogger(__name__)

async def generate_thought(phase: str, context: str) -> str:
    """
    Generates a short, natural language 'thought' or status update for the AI.

    Args:
        phase (str): The current phase (e.g., 'analysis', 'planning').
        context (str): The context of the operation (e.g., 'analyzing user intent').

    Returns:
        str: A short thought sentence.
    """
    model = get_gemini()
    
    # Fallback if model fails or strictly for speed/cost if needed (though we want AI generation)
    # For now, we always try to generate.
    
    prompt = f"""
    You are the internal monologue of an advanced AI presentation designer.
    Generate a SINGLE, short sentence (max 10 words) that describes what you are thinking or doing right now.
    It should sound professional yet creative. 
    
    Current Phase: {phase}
    Context: {context}
    
    Examples:
    - Analying the semantic structure of your request...
    - Selecting a color palette that conveys trust and growth...
    - Optimizing the visual hierarchy for the title slide...
    - Calibrating the layout to maximize readability...
    
    Output ONLY the sentence. No quotes, no preamble.
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Cleanup quotes if any
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        return text
    except Exception as e:
        logger.warning(f"Error generating thought: {e}")
        # Fallback messages
        backups: List[str] = [
            "Optimizing the design matrix...",
            "Calibrating visual weights...",
            "Synthesizing layout structures...",
            "Refining the aesthetic parameters...",
        ]
        return random.choice(backups)
