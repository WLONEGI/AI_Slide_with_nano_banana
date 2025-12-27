
from .vertex_wrapper import get_gemini
from .models import Slide, SlidePlan, StyleDef
import json
import logging
from typing import Optional, Set

logger = logging.getLogger(__name__)

def _style_context(style_def: Optional[StyleDef]) -> str:
    """
    Generates a text description of the style context.

    Args:
        style_def (Optional[StyleDef]): The style definition object.

    Returns:
        str: A string describing the style.
    """
    if not style_def:
        return "Standard Professional Style"
    layout_desc = [
        f"{layout.layout_id}: {layout.visual_description}"
        for layout in style_def.layouts
    ]
    return f"Global Prompt: {style_def.global_prompt}. Layouts: {layout_desc}"

async def edit_slide(
    instruction: str,
    slide: Optional[Slide] = None,
    plan: Optional[SlidePlan] = None,
    style_def: Optional[StyleDef] = None,
) -> Slide:
    """
    Edits a slide based on user instruction.

    Args:
        instruction (str): The editing instruction from the user.
        slide (Optional[Slide]): The specific slide to edit.
        plan (Optional[SlidePlan]): The slide plan (required if slide is not provided).
        style_def (Optional[StyleDef]): The style context.

    Returns:
        Slide: The updated slide object.

    Raises:
        ValueError: If neither slide nor plan is provided, or if the LLM output is missing fields.
    """
    model = get_gemini()
    style_desc: str = _style_context(style_def)

    prompt: str
    if slide:
        prompt = f"""
        You are an expert presentation editor.
        Update the slide based on the user's instruction.
        Instruction: {instruction}

        Current Slide:
        {slide.model_dump()}

        Style Context:
        {style_desc}

        Requirements:
        - Keep slide_id the same.
        - Keep layout_id unless the instruction clearly requires a different layout.
        - Do not contradict user input. Only refine or clarify.
        - Output STRICTLY VALID JSON for a Slide with fields:
          slide_id, text_expected, layout_id, visual_prompt, content_text.
        """
    else:
        if not plan:
            raise ValueError("plan is required when slide is not provided.")
        prompt = f"""
        You are an expert presentation editor.
        Choose the most relevant slide to update based on the user's instruction,
        then update that slide. Only one slide should be updated.

        Instruction: {instruction}

        Slides:
        {plan.model_dump()}

        Style Context:
        {style_desc}

        Requirements:
        - Select an existing slide_id from the list.
        - Output STRICTLY VALID JSON for a Slide with fields:
          slide_id, text_expected, layout_id, visual_prompt, content_text.
        """

    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        data = json.loads(response.text)
        required_fields: Set[str] = {"slide_id", "text_expected", "layout_id", "visual_prompt", "content_text"}
        missing: Set[str] = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Edited slide missing fields: {missing}")
        return Slide(**data)
    except Exception as e:
        logger.error(f"Error editing slide: {e}")
        raise
