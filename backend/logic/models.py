
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, TypedDict, Annotated
import operator

class LayoutDef(BaseModel):
    """
    Definition of a slide layout.

    Attributes:
        layout_id (str): Unique identifier for the layout (e.g., "title", "content_left").
        visual_description (str): Description of the visual structure for the AI.
    """
    layout_id: str
    visual_description: str

class StyleDef(BaseModel):
    """
    Global style definition for the presentation.

    Attributes:
        global_prompt (str): The overall artistic direction and style prompt.
        layouts (List[LayoutDef]): List of available layouts for this style.
    """
    global_prompt: str
    layouts: List[LayoutDef]

class Slide(BaseModel):
    """
    Represents a single slide in the presentation plan.

    Attributes:
        slide_id (int): Unique identifier for the slide.
        text_expected (bool): Whether this slide should contain text content.
        layout_id (str): The ID of the layout to use.
        visual_prompt (str): The prompt used to generate the slide image.
        content_text (Optional[str]): The text content to be displayed on the slide.
        tool (Optional[str]): The tool used to generate the slide image ("imagen" or "code_interpreter"). Defaults to "imagen".
        reasoning (Optional[str]): The reasoning behind the slide's design (from Refiner).
    """
    slide_id: int
    text_expected: bool
    layout_id: str
    visual_prompt: str
    content_text: Optional[str] = None
    tool: Optional[str] = "imagen" # "imagen" or "code_interpreter"
    reasoning: Optional[str] = None # Refiner's reasoning

class ThinkingStep(BaseModel):
    """
    Represents a step in the AI's internal thinking process.

    Attributes:
        phase (str): The phase of thinking (e.g., "Analyzing", "Refining").
        content (str): The content or output of the thinking step.
    """
    phase: str
    content: str
    
class SlidePlan(BaseModel):
    """
    The complete plan for the presentation slides.

    Attributes:
        slides (List[Slide]): List of slide definitions.
        reasoning (Optional[str]): Overall reasoning for the plan structure.
        thinking_steps (Optional[List[ThinkingStep]]): List of internal thinking steps recorded during planning.
        refinement_log (Optional[List[str]]): Log of refinement actions taken.
    """
    slides: List[Slide]
    reasoning: Optional[str] = None 
    thinking_steps: Optional[List[ThinkingStep]] = None
    refinement_log: Optional[List[str]] = None  # Refiner's thought log


# --- LangGraph State ---

class ProjectState(TypedDict):
    """
    State dictionary for the LangGraph workflow.

    Attributes:
        user_topic (str): The user's input topic or request.
        uploaded_assets (List[str]): List of paths/URLs to uploaded assets.
        style_guideline (Optional[Dict[str, Any]]): The style definition (as a dict or StyleDef).
        slide_plan (Optional[SlidePlan]): The generated slide plan.
        refinement_log (List[str]): Log of refinement actions/thoughts.
        current_slide_idx (int): Index of the slide currently being processed.
        generated_images (Dict[int, str]): Map of slide_id to generated image URL/path.
        validation_results (Dict[int, Dict[str, Any]]): Map of slide_id to validation results.
        retry_counts (Dict[int, int]): Map of slide_id to retry counts.
        ui_stream_events (List[str]): List of UI events for streaming.
        user_feedback (Optional[str]): User provided feedback.
        edit_mask (Optional[str]): Mask for editing operations.
    """
    # Input
    user_topic: str
    uploaded_assets: List[str]
    style_guideline: Optional[Dict[str, Any]] # as dict for now or StyleDef
    
    # Planning
    slide_plan: Optional[SlidePlan]
    refinement_log: List[str]
    
    # Execution
    current_slide_idx: int
    generated_images: Dict[int, str] # slide_id -> filepath/url
    validation_results: Dict[int, Dict[str, Any]]
    retry_counts: Dict[int, int]  # slide_id -> retry count for Quality Gate loop
    
    # Output/UX
    ui_stream_events: List[str]
    user_feedback: Optional[str]
    edit_mask: Optional[str]

class GeneratePlanRequest(BaseModel):
    """
    Request model for generating a slide plan.

    Attributes:
        text (str): The user's input text describing the presentation.
        style_def (Optional[StyleDef]): Optional explicit style definition.
    """
    text: str
    style_def: Optional[StyleDef] = None

class GenerateImageRequest(BaseModel):
    """
    Request model for generating a single slide image.

    Attributes:
        slide (Slide): The slide definition.
        style_def (Optional[StyleDef]): Optional style definition to use.
    """
    slide: Slide
    style_def: Optional[StyleDef] = None

class EditSlideRequest(BaseModel):
    """
    Request model for editing a slide.

    Attributes:
        instruction (str): The user's instruction for editing.
        slide (Optional[Slide]): The slide to edit.
        plan (Optional[SlidePlan]): The complete plan (context for editing).
        style_def (Optional[StyleDef]): Optional style definition.
    """
    instruction: str
    slide: Optional[Slide] = None
    plan: Optional[SlidePlan] = None
    style_def: Optional[StyleDef] = None
