
from langgraph.graph import StateGraph, END
from typing import Dict, Any, TypedDict, Literal, Optional, List, Union

from logic.models import ProjectState, SlidePlan, Slide, StyleDef
from logic.director import create_slide_plan
from logic.refiner import refine_slide_plan
from logic.image_generator import generate_slide_image
from logic.code_worker import execute_code_worker
from logic.quality_gate import check_quality
import logging

logger = logging.getLogger(__name__)

MAX_RETRIES: int = 2

# --- Node Wrappers ---

async def director_node(state: ProjectState) -> Dict[str, Any]:
    """
    Orchestrates the creation of the initial slide plan.

    Args:
        state (ProjectState): The current state of the project.

    Returns:
        Dict[str, Any]: Updates to the state, including the new 'slide_plan' and 'refinement_log'.
    """
    logger.info("--- Director Node ---")
    text: str = state["user_topic"]
    style_def_dict: Optional[Dict[str, Any]] = state.get("style_guideline")
    style_def: Optional[StyleDef] = StyleDef(**style_def_dict) if style_def_dict else None
    
    plan: SlidePlan = await create_slide_plan(text, style_def)
    return {"slide_plan": plan, "refinement_log": state.get("refinement_log", []) + ["Director: Created initial plan."]}

async def refiner_node(state: ProjectState) -> Dict[str, Any]:
    """
    Refines the existing slide plan to improve quality and coherence.

    Args:
        state (ProjectState): The current state of the project.

    Returns:
        Dict[str, Any]: Updates to the state, including the refined 'slide_plan' and log entries.
    """
    logger.info("--- Refiner Node ---")
    # We can assert plan exists here as it's passed from director
    plan: Optional[SlidePlan] = state["slide_plan"]
    if not plan:
        raise ValueError("Slide plan missing in Refiner Node")

    topic: str = state["user_topic"]
    
    refined_plan: SlidePlan = await refine_slide_plan(topic, plan)
    
    log_entry: str = f"Refiner: {refined_plan.reasoning}"
    return {"slide_plan": refined_plan, "refinement_log": state.get("refinement_log", []) + [log_entry]}

# --- Planning Graph ---

planning_workflow = StateGraph(ProjectState)
planning_workflow.add_node("director", director_node)
planning_workflow.add_node("refiner", refiner_node)

planning_workflow.set_entry_point("director")
planning_workflow.add_edge("director", "refiner")
planning_workflow.add_edge("refiner", END)

planning_app = planning_workflow.compile()


# --- Execution Node Wrappers ---

async def visual_router_node(state: ProjectState) -> Dict[str, Any]:
    """
    Routing node that logs the decision for the next visual generation step.
    The actual routing logic happens in `route_visual_worker`.

    Args:
        state (ProjectState): The current state.

    Returns:
        Dict[str, Any]: Empty dict as no state update is needed here.
    """
    # Pass-through node to decide next step based on tool
    idx: int = state["current_slide_idx"]
    plan: Optional[SlidePlan] = state["slide_plan"]
    if not plan:
        raise ValueError("Slide plan missing in Visual Router")
        
    slide: Slide = plan.slides[idx]
    logger.info(f"--- Visual Router: Slide {slide.slide_id} -> Tool: {slide.tool} ---")
    return {} # No state update, just routing logic in edge

def route_visual_worker(state: ProjectState) -> Literal["imagen_worker", "code_worker"]:
    """
    Determines which worker to use based on the slide's tool preference.

    Args:
        state (ProjectState): The current state.

    Returns:
        Literal["imagen_worker", "code_worker"]: The name of the next node.
    """
    idx: int = state["current_slide_idx"]
    plan: Optional[SlidePlan] = state["slide_plan"]
    if not plan:
        # Should not happen in valid flow
        return "imagen_worker" 
        
    slide: Slide = plan.slides[idx]
    
    if slide.tool == "code_interpreter":
        return "code_worker"
    return "imagen_worker"

async def imagen_worker_node(state: ProjectState) -> Dict[str, Any]:
    """
    Generates a slide image using the Imagen model.

    Args:
        state (ProjectState): The current state.

    Returns:
        Dict[str, Any]: Updates to 'generated_images'.
    """
    logger.info("--- Imagen Worker Node ---")
    idx: int = state["current_slide_idx"]
    plan: Optional[SlidePlan] = state["slide_plan"]
    if not plan:
        raise ValueError("Slide plan missing in Imagen Worker")

    slide: Slide = plan.slides[idx]
    style_def_dict: Optional[Dict[str, Any]] = state.get("style_guideline")
    style_def: Optional[StyleDef] = StyleDef(**style_def_dict) if style_def_dict else None
    
    # Get retry count for enhanced prompt if retrying
    retry_counts: Dict[int, int] = state.get("retry_counts", {})
    retry_count: int = retry_counts.get(slide.slide_id, 0)
    
    # Modify slide for retry with enhanced legibility
    if retry_count > 0:
        logger.info(f"Retry #{retry_count} for slide {slide.slide_id} - enhancing prompt for legibility")
        # Create modified slide with enhanced prompt
        enhanced_prompt: str = f"{slide.visual_prompt}. IMPORTANT: Use high contrast text, simple clean background, large readable fonts. Ensure all text is clearly legible."
        slide = Slide(
            slide_id=slide.slide_id,
            text_expected=slide.text_expected,
            layout_id=slide.layout_id,
            visual_prompt=enhanced_prompt,
            content_text=slide.content_text,
            tool=slide.tool,
            reasoning=slide.reasoning
        )
    
    image_bytes: bytes = await generate_slide_image(slide, style_def)
    
    import uuid
    import os
    filename: str = f"{uuid.uuid4()}.png"
    filepath: str = f"static/images/{filename}"
    with open(filepath, "wb") as f:
        f.write(image_bytes)
        
    url: str = f"http://localhost:8000/static/images/{filename}"
    
    generated_updates: Dict[int, str] = state.get("generated_images", {}).copy()
    generated_updates[slide.slide_id] = url
    
    return {"generated_images": generated_updates}

async def code_worker_node(state: ProjectState) -> Dict[str, Any]:
    """
    Generates a slide image using a code execution worker (e.g., Matplotlib).

    Args:
        state (ProjectState): The current state.

    Returns:
        Dict[str, Any]: Updates to 'generated_images'.
    """
    logger.info("--- Code Worker Node ---")
    idx: int = state["current_slide_idx"]
    plan: Optional[SlidePlan] = state["slide_plan"]
    if not plan:
         raise ValueError("Slide plan missing in Code Worker")

    slide: Slide = plan.slides[idx]
    
    # Execute code worker (writes file and returns URL)
    url: Optional[str] = await execute_code_worker(slide.slide_id, slide.visual_prompt)
    
    if not url:
        logger.error("Code Worker produced no URL.")
    
    generated_updates: Dict[int, str] = state.get("generated_images", {}).copy()
    if url:
        generated_updates[slide.slide_id] = url
    return {"generated_images": generated_updates}

async def quality_gate_node(state: ProjectState) -> Dict[str, Any]:
    """
    Evaluates the quality of the generated image.

    Args:
        state (ProjectState): The current state.

    Returns:
        Dict[str, Any]: Updates to 'validation_results' and potentially 'retry_counts'.
    """
    logger.info("--- Quality Gate Node ---")
    idx: int = state["current_slide_idx"]
    plan: Optional[SlidePlan] = state["slide_plan"]
    if not plan:
         raise ValueError("Slide plan missing in Quality Gate")
         
    slide: Slide = plan.slides[idx]
    
    if not slide.text_expected:
        logger.info("Skipping Quality Gate (Text Not Expected)")
        res: Dict[str, Any] = {"overall_judgement": "OK (Skipped)", "passed": True}
        val_updates: Dict[int, Dict[str, Any]] = state.get("validation_results", {}).copy()
        val_updates[slide.slide_id] = res
        return {"validation_results": val_updates}

    images: Dict[int, str] = state.get("generated_images", {})
    url: Optional[str] = images.get(slide.slide_id)
    if not url:
        return {}

    # Load bytes
    filename: str = url.split("static/images/")[-1]
    filepath: str = f"static/images/{filename}"
    
    with open(filepath, "rb") as f:
        image_bytes: bytes = f.read()

    is_ok: bool
    result: Dict[str, Any]
    is_ok, result = await check_quality(image_bytes)
    
    # Add pass/fail flag to result
    result["passed"] = is_ok
    
    val_updates: Dict[int, Dict[str, Any]] = state.get("validation_results", {}).copy()
    val_updates[slide.slide_id] = result
    
    # Update retry count if failed
    if not is_ok:
        retry_counts: Dict[int, int] = state.get("retry_counts", {}).copy()
        current_retries: int = retry_counts.get(slide.slide_id, 0)
        retry_counts[slide.slide_id] = current_retries + 1
        logger.warning(f"Quality Gate FAILED for slide {slide.slide_id}. Retry count: {retry_counts[slide.slide_id]}/{MAX_RETRIES}")
        return {"validation_results": val_updates, "retry_counts": retry_counts}
    
    logger.info(f"Quality Gate PASSED for slide {slide.slide_id}")
    return {"validation_results": val_updates}

def route_after_quality_gate(state: ProjectState) -> Literal["retry_worker", "end"]:
    """
    Decides whether to retry the generation or finish the process based on Quality Gate results.

    Args:
        state (ProjectState): The current state.

    Returns:
        Literal["retry_worker", "end"]: The next edge or end.
    """
    idx: int = state["current_slide_idx"]
    plan: Optional[SlidePlan] = state["slide_plan"]
    if not plan:
        return "end" # Should not happen
        
    slide: Slide = plan.slides[idx]
    
    val_results: Dict[int, Dict[str, Any]] = state.get("validation_results", {})
    result: Dict[str, Any] = val_results.get(slide.slide_id, {})
    
    if result.get("passed", True):
        return "end"
    
    # Check retry count
    retry_counts: Dict[int, int] = state.get("retry_counts", {})
    current_retries: int = retry_counts.get(slide.slide_id, 0)
    
    if current_retries >= MAX_RETRIES:
        logger.warning(f"Max retries ({MAX_RETRIES}) reached for slide {slide.slide_id}. Accepting as-is.")
        return "end"
    
    logger.info(f"Retrying slide {slide.slide_id} (attempt {current_retries + 1}/{MAX_RETRIES})")
    return "retry_worker"

async def retry_router_node(state: ProjectState) -> Dict[str, Any]:
    """
    Routes back to the appropriate worker for retry.
    Actual routing logic is in the edge conditional.

    Args:
        state (ProjectState): The current state.

    Returns:
        Dict[str, Any]: Empty dict.
    """
    return {}  # No state change, just routing


# --- Execution Graph with Retry Loop ---

exec_workflow = StateGraph(ProjectState)
exec_workflow.add_node("visual_router", visual_router_node)
exec_workflow.add_node("imagen_worker", imagen_worker_node)
exec_workflow.add_node("code_worker", code_worker_node)
exec_workflow.add_node("quality_gate", quality_gate_node)
exec_workflow.add_node("retry_router", retry_router_node)

exec_workflow.set_entry_point("visual_router")

exec_workflow.add_conditional_edges(
    "visual_router",
    route_visual_worker,
    {
        "imagen_worker": "imagen_worker",
        "code_worker": "code_worker"
    }
)

exec_workflow.add_edge("imagen_worker", "quality_gate")
exec_workflow.add_edge("code_worker", "quality_gate")

# Quality Gate -> Retry or End
exec_workflow.add_conditional_edges(
    "quality_gate",
    route_after_quality_gate,
    {
        "retry_worker": "retry_router",
        "end": END
    }
)

# Retry Router -> Back to Visual Router (which will route to correct worker)
exec_workflow.add_conditional_edges(
    "retry_router",
    route_visual_worker,
    {
        "imagen_worker": "imagen_worker",
        "code_worker": "code_worker"
    }
)

execution_app = exec_workflow.compile()
