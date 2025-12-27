
from logic.vertex_wrapper import call_gemini_flash
from logic.models import SlidePlan, Slide
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

REFINER_PROMPT: str = """
You are a world-class Presentation Creative Director.
Review the "Draft Slide Plan" created by an assistant and dramatically improve it.

## Criteria (Refinement Logic)
1. **Less is More:** Ensure each slide focuses on ONE key message. Split slides if text is too dense.
2. **Visual Impact:** Avoid clichés (e.g., "business handshake"). Use artistic, metaphorical, or cinematic descriptions.
3. **Tool Optimization:** 
   - Use `tool: code_interpreter` for slides involving data, charts, numbers, or graphs.
   - Use `tool: imagen` for conceptual, abstract, or photographic visuals.

## Input Context
Topic: {topic}

## Draft Plan
{draft_plan_json}

## Output Format (JSON)
Return a single JSON object with this structure:
{{
  "thoughts": "Critique of the plan and explanation of changes...",
  "refined_slides": [
    {{
      "slide_id": 1,
      "tool": "imagen", // or "code_interpreter"
      "layout_id": "visual_centric", // keep or change
      "text_expected": true,
      "visual_prompt": "Refined visual description...",
      "content_text": "Refined content text...",
      "reasoning": "Reason for changes..."
    }},
    ...
  ]
}}
"""

async def refine_slide_plan(topic: str, draft_plan: SlidePlan) -> SlidePlan:
    """
    Refines the given slide plan using the Refiner Agent logic.

    Args:
        topic (str): The user's input topic.
        draft_plan (SlidePlan): The initial slide plan to refine.

    Returns:
        SlidePlan: The refined slide plan. Returns the original plan if refinement fails.
    """
    logger.info("Refiner Agent: Reviewing draft plan...")
    
    draft_json: str = draft_plan.model_dump_json()
    prompt: str = REFINER_PROMPT.format(topic=topic, draft_plan_json=draft_json)
    
    response_text: str = await call_gemini_flash(prompt)
    
    # Simple JSON parsing (in production, use robust parser or Function Calling)
    try:
        # cleanup markdown code blocks if present
        cleaned_text: str = response_text.replace("```json", "").replace("```", "").strip()
        data: Dict[str, Any] = json.loads(cleaned_text)
        
        refined_slides_data: List[Dict[str, Any]] = data.get("refined_slides", [])
        
        # Convert back to partial Slide objects, merging with basics if needed.
        # But here we likely want to replace the slides.
        # Note: slide_id might need re-indexing if split, but for v1 we assume 1:1 or N:N replacement.
        
        refined_slides: List[Slide] = []
        for s_data in refined_slides_data:
            # We need to map the fields correctly to our Slide model
            slide = Slide(
                slide_id=s_data.get("slide_id"),
                text_expected=s_data.get("text_expected", True),
                layout_id=s_data.get("layout_id", "title"),
                visual_prompt=s_data.get("visual_prompt", ""),
                content_text=s_data.get("content_text", ""),
                tool=s_data.get("tool", "imagen"),
                reasoning=s_data.get("reasoning", "")
            )
            refined_slides.append(slide)
            
        thoughts: str = data.get("thoughts", "")
        logger.info(f"Refiner Output Thoughts: {thoughts}")
        
        return SlidePlan(slides=refined_slides, reasoning=thoughts)

    except Exception as e:
        logger.error(f"Refiner failed to parse JSON or execute: {e}. Returning original plan.")
        return draft_plan # Fallback
