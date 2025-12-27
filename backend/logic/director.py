
from .vertex_wrapper import get_gemini
from .models import SlidePlan, StyleDef, Slide, ThinkingStep
import json
import logging
from typing import List, Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

from .grounding import perform_grounding


def parse_json_safe(text: str) -> Dict[str, Any]:
    """
    Parses a JSON string properly, handling markdown code blocks.

    Args:
        text (str): The JSON string to parse, potentially wrapped in markdown.

    Returns:
        Dict[str, Any]: The parsed JSON data.

    Raises:
        json.JSONDecodeError: If the string is not valid JSON.
    """
    cleaned_text = text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:]
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]
    return json.loads(cleaned_text, strict=False)


def _build_style_description(style_def: Optional[StyleDef]) -> str:
    """
    Builds a style description string from a StyleDef.

    Args:
        style_def (Optional[StyleDef]): The style definition.

    Returns:
        str: Human-readable style description.
    """
    if not style_def:
        return "Standard Professional Style"
    
    layout_ids = [layout.layout_id for layout in style_def.layouts]
    return f"Global Prompt: {style_def.global_prompt}. Layouts: {layout_ids}"


def _create_sources_slide(slides: List[Slide], grounding_info: str) -> Slide:
    """
    Creates a sources/references slide.

    Args:
        slides (List[Slide]): Existing slides to determine the next slide_id.
        grounding_info (str): Grounding information to display.

    Returns:
        Slide: The sources slide.
    """
    return Slide(
        slide_id=len(slides) + 1,
        text_expected=True,
        layout_id="content_left",
        visual_prompt="A professional bibliography or references page. Clean list design, balanced typography, minimalist research aesthetic with a faint intellectual watermark.",
        content_text=f"Sources & References:\n{grounding_info[:400]}..."
    )


def _find_marker(content: str, primary: str, fallback: str) -> Optional[str]:
    """
    Finds which marker exists in content.

    Args:
        content (str): The content to search.
        primary (str): Primary marker to look for.
        fallback (str): Fallback marker if primary not found.

    Returns:
        Optional[str]: The found marker or None.
    """
    if primary in content:
        return primary
    if fallback in content:
        return fallback
    return None


def _strip_leading_colon(text: str) -> str:
    """Removes leading colon and whitespace from text."""
    if text.startswith(":"):
        return text[1:].strip()
    return text


def _parse_reasoning_to_thinking_steps(reasoning: str) -> List[ThinkingStep]:
    """
    Parses monolithic reasoning into structured ThinkingStep list.

    Args:
        reasoning (str): The raw reasoning string.

    Returns:
        List[ThinkingStep]: Parsed thinking steps.
    """
    thinking_steps: List[ThinkingStep] = []
    remaining_content = reasoning

    analysis_marker = _find_marker(reasoning, "**Analysis**", "Analysis:")
    planning_marker = _find_marker(reasoning, "**Planning**", "Planning:")

    # Parse Analysis section
    if analysis_marker:
        if planning_marker:
            parts = remaining_content.split(planning_marker)
            analysis_content = parts[0].replace(analysis_marker, "").strip()
            analysis_content = _strip_leading_colon(analysis_content)
            thinking_steps.append(ThinkingStep(phase="Analysis", content=analysis_content))
            
            if len(parts) > 1:
                remaining_content = planning_marker + parts[1]
        else:
            analysis_content = remaining_content.replace(analysis_marker, "").strip()
            analysis_content = _strip_leading_colon(analysis_content)
            thinking_steps.append(ThinkingStep(phase="Analysis", content=analysis_content))

    # Parse Planning section
    if planning_marker and planning_marker in remaining_content:
        planning_content = remaining_content.replace(planning_marker, "").strip()
        planning_content = _strip_leading_colon(planning_content)
        thinking_steps.append(ThinkingStep(phase="Planning & Layout", content=planning_content))

    # Fallback if no sections were parsed
    if not thinking_steps:
        thinking_steps.append(ThinkingStep(phase="Initial Planning", content=reasoning))

    return thinking_steps


def _extract_refinement_content(new_reasoning: str) -> str:
    """
    Extracts the refinement portion from reasoning.

    Args:
        new_reasoning (str): The full reasoning string.

    Returns:
        str: The refinement content.
    """
    if "**Refinement**" not in new_reasoning:
        return new_reasoning
    
    parts = new_reasoning.split("**Refinement**")
    if len(parts) <= 1:
        return new_reasoning
    
    return "**Refinement**" + parts[-1]


async def create_slide_plan(user_text: str, style_def: Optional[StyleDef] = None) -> SlidePlan:
    """
    Generates a slide plan based on the user's text and style definition.

    Args:
        user_text (str): The user's input topic or description.
        style_def (Optional[StyleDef]): The style definition to apply.

    Returns:
        SlidePlan: The generated slide plan.
    """
    model = get_gemini()
    
    grounding_info: str = await perform_grounding(user_text)
    style_description = _build_style_description(style_def)

    prompt = _build_director_prompt(user_text, grounding_info, style_description)
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        parsed_response: Dict[str, Any] = parse_json_safe(response.text)
        slides: List[Slide] = [Slide(**slide_data) for slide_data in parsed_response.get("slides", [])]
        reasoning: str = parsed_response.get("reasoning", "")
        
        if grounding_info:
            slides.append(_create_sources_slide(slides, grounding_info))

        thinking_steps = _parse_reasoning_to_thinking_steps(reasoning)
        
        initial_plan = SlidePlan(
            slides=slides, 
            reasoning=reasoning,
            thinking_steps=thinking_steps
        )
        
        return await _try_refine_plan(initial_plan, user_text)

    except Exception as e:
        logger.error(f"Error generating slide plan: {e}")
        raise e


async def _try_refine_plan(initial_plan: SlidePlan, user_text: str) -> SlidePlan:
    """
    Attempts to refine a plan, returning initial plan on failure.

    Args:
        initial_plan (SlidePlan): The plan to refine.
        user_text (str): The user's original request.

    Returns:
        SlidePlan: Refined or initial plan.
    """
    try:
        from .refiner import refine_slide_plan as refine_func
        return await refine_slide_plan(initial_plan, user_text)
    except Exception as e:
        logger.warning(f"Refinement failed, returning initial plan: {e}")
        return initial_plan


def _build_director_prompt(user_text: str, grounding_info: str, style_description: str) -> str:
    """
    Builds the director prompt for slide planning.

    Args:
        user_text (str): User's input text.
        grounding_info (str): Research/grounding information.
        style_description (str): Style description.

    Returns:
        str: The formatted prompt.
    """
    return f"""
    You are an expert presentation director. Your task is to plan a slide deck based on the user's input text and supplementary research.
    
    User Input:
    {user_text}
    
    Grounding Info (Research):
    {grounding_info}
    
    Design Style Context:
    {style_description}
    
    Instructions:
    1. Break down the user's input into a logical sequence of slides.
    2. Incorporate facts from Grounding Info where relevant.
    3. THINK STEP-BY-STEP. Capture your thought process in the 'reasoning' field.
       - Explain WHY you chose this narrative structure.
       - Explain why specific layouts were selected.
       - IMPORTANT: The 'reasoning' field must be a SINGLE LINE string with newlines escaped as \\n. Do not use actual newlines in the JSON value.
    4. For each slide, determine:
       - slide_id: integer, sequential starting from 1.
       - text_expected: true if the slide should contain legible text.
       - layout_id: choose from the provided layouts if available.
       - visual_prompt: description for Imagen.
       - content_text: actual text on slide.
    
     Output strictly VALID JSON schema:
    {{
      "reasoning": "**Analysis**:\\n1. User intent: ...\\n2. Key themes: ...\\n\\n**Planning**:\\n- Slide 1: Chosen because...",
      "slides": [
          {{ "slide_id": 1, "text_expected": true, "layout_id": "...", "visual_prompt": "...", "content_text": "..." }},
          ...
      ]
    }}
    """


async def refine_slide_plan(plan: SlidePlan, original_request: str) -> SlidePlan:
    """
    Internal refinement function used by Director (different from the logic.refiner one).

    Args:
        plan (SlidePlan): The initial plan.
        original_request (str): The user's request.

    Returns:
        SlidePlan: Refined plan.
    """
    logger.info("Refining slide plan (Self-Correction)...")
    model = get_gemini()
    
    prompt = _build_refiner_prompt(plan, original_request)
    
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    
    parsed_response = parse_json_safe(response.text)
    refined_slides = [Slide(**slide_data) for slide_data in parsed_response.get("slides", [])]
    new_reasoning = parsed_response.get("reasoning", plan.reasoning)
    
    new_steps = list(plan.thinking_steps) if plan.thinking_steps else []
    refinement_content = _extract_refinement_content(new_reasoning)
    new_steps.append(ThinkingStep(phase="Refinement (Self-Correction)", content=refinement_content))
    
    return SlidePlan(slides=refined_slides, reasoning=new_reasoning, thinking_steps=new_steps)


def _build_refiner_prompt(plan: SlidePlan, original_request: str) -> str:
    """
    Builds the refiner prompt for plan critique.

    Args:
        plan (SlidePlan): The current plan.
        original_request (str): The user's original request.

    Returns:
        str: The formatted prompt.
    """
    return f"""
    Act as a strict, award-winning Creative Director. 
    Critique and simple improvements to the following presentation plan based on the user's request.
    
    User Request: {original_request}
    
    Current Plan (JSON):
    {json.dumps([slide.dict() for slide in plan.slides], indent=2)}
    
    Previous Reasoning:
    {plan.reasoning}
    
    Critique Criteria:
    1. **Narrative Flow**: Does the story make sense?
    2. **Visual Variety**: Are layouts varied enough?
    3. **Clarity**: Is the content concise and impactful?
    
    Instructions:
    - If the plan is already excellent, return it as is.
    - If improvements are needed, modify the slides.
    - Ensure `slide_id`s are sequential.
    - Do NOT remove the "Sources" slide.
    - Append your critique to the reasoning.
    - IMPORTANT: Escape all newlines in 'reasoning' as \\n.
    
    Output strictly VALID JSON schema:
    {{
      "reasoning": "... (previous) ... \\n\\n**Refinement**:\\n- Critiqued slide 3...",
      "slides": [ ... ]
    }}
    """
