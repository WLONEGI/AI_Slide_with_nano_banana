
from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import uuid
import logging
from typing import List, Optional, Dict, AsyncGenerator, Any
import time
import asyncio
import json
import base64
import anyio

# Logic Imports
from logic.models import (
    GeneratePlanRequest, SlidePlan, GenerateImageRequest, StyleDef, 
    EditSlideRequest, Slide, ProjectState
)
from logic.director import create_slide_plan
from logic.style_extractor import extract_style_from_text
from logic.image_generator import generate_slide_image, generate_inpainted_image
from logic.assembler import assemble_pdf
from logic.editor import edit_slide
from logic.quality_gate import check_style_consistency
from logic.thinking import generate_thought
from logic.workflow import planning_app, execution_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- Helper Functions ---

def _is_enabled_env(env_name: str, default: bool = True) -> bool:
    """
    Checks if an environment variable enables a feature.

    Args:
        env_name (str): The name of the environment variable.
        default (bool): The default value if the variable is not set.

    Returns:
        bool: True if enabled, False otherwise.
    """
    env_value = os.getenv(env_name)
    if env_value is None:
        return default
    
    normalized_value = env_value.strip().lower()
    if normalized_value in {"1", "true", "on", "enabled", "yes"}:
        return True
    if normalized_value in {"0", "false", "off", "disabled", "no"}:
        return False
    
    logger.warning("Invalid %s value '%s'. Falling back to default=%s.", env_name, env_value, default)
    return default


def _extract_filename_from_url(image_url: str) -> Optional[str]:
    """
    Extracts the filename from a static image URL.

    Args:
        image_url (str): The image URL.

    Returns:
        Optional[str]: The extracted filename or None if invalid.
    """
    if "static/images/" not in image_url:
        return None
    return image_url.split("static/images/")[-1].split("?")[0]


def _load_image_bytes_from_urls(image_urls: List[str]) -> List[bytes]:
    """
    Loads image bytes from a list of URLs.

    Args:
        image_urls (List[str]): URLs to load.

    Returns:
        List[bytes]: List of image bytes.
    """
    image_bytes_list: List[bytes] = []
    for url in image_urls:
        filename = _extract_filename_from_url(url)
        if not filename:
            continue
        
        filepath = f"static/images/{filename}"
        if not os.path.exists(filepath):
            continue
        
        with open(filepath, "rb") as f:
            image_bytes_list.append(f.read())
    
    return image_bytes_list


def _find_original_image_path(image_filename: str) -> str:
    """
    Finds the path to an original image, checking multiple locations.

    Args:
        image_filename (str): The image filename.

    Returns:
        str: The resolved file path.

    Raises:
        HTTPException: If the image is not found.
    """
    primary_path = f"static/images/{image_filename}"
    if os.path.exists(primary_path):
        return primary_path
    
    basename_path = f"static/images/{os.path.basename(image_filename)}"
    if os.path.exists(basename_path):
        return basename_path
    
    raise HTTPException(status_code=404, detail="Original image not found")


def _decode_base64_mask(mask_base64: str) -> bytes:
    """
    Decodes a base64-encoded mask image.

    Args:
        mask_base64 (str): The base64 string (with or without data URI header).

    Returns:
        bytes: The decoded mask bytes.
    """
    if "," in mask_base64:
        _, encoded_data = mask_base64.split(",", 1)
    else:
        encoded_data = mask_base64
    return base64.b64decode(encoded_data)


def _create_initial_project_state(user_topic: str, style_guideline: Dict[str, Any]) -> ProjectState:
    """
    Creates an initial ProjectState for workflow execution.

    Args:
        user_topic (str): The user's topic.
        style_guideline (Dict[str, Any]): The style guideline dict.

    Returns:
        ProjectState: The initialized state.
    """
    return {
        "user_topic": user_topic,
        "uploaded_assets": [],
        "style_guideline": style_guideline,
        "slide_plan": None,
        "refinement_log": [],
        "current_slide_idx": 0,
        "generated_images": {},
        "validation_results": {},
        "retry_counts": {},
        "ui_stream_events": [],
        "user_feedback": None,
        "edit_mask": None
    }


async def _run_style_consistency_check(image_bytes_list: List[bytes]) -> None:
    """
    Runs style consistency check if enabled.

    Args:
        image_bytes_list (List[bytes]): Images to check.
    """
    if not image_bytes_list:
        return
    
    if not _is_enabled_env("STYLE_CONSISTENCY_MODE", True):
        logger.info("Style consistency check disabled via STYLE_CONSISTENCY_MODE.")
        return
    
    try:
        logger.info("Running Style Consistency Check...")
        consistency_result = await check_style_consistency(image_bytes_list, "Professional presentation")
        
        if not consistency_result.get("is_consistent"):
            logger.warning(f"Style Consistency Issue Detected: {consistency_result.get('feedback')}")
        else:
            logger.info(f"Style Consistency Verified (Score: {consistency_result.get('consistency_score')})")
    except Exception as e:
        logger.warning(f"Skipping consistency check error: {e}")


# --- Request Models ---

class StyleRequest(BaseModel):
    description: str

class AssembleRequest(BaseModel):
    image_urls: List[str]

class ThinkingRequest(BaseModel):
    phase: str
    context: str

class InpaintRequest(BaseModel):
    slide_id: int
    image_filename: str
    mask_base64: str
    instruction: str
    style_def: Optional[StyleDef] = None


# --- App Configuration ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static/images", exist_ok=True)
os.makedirs("static/pdfs", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")


# --- SSE Streaming ---

_stream_logs: Dict[str, Dict[str, Any]] = {}

async def stream_refinement_log(session_id: str) -> AsyncGenerator[str, None]:
    """Generator that yields SSE events for refinement_log updates."""
    seen_count = 0
    timeout_seconds = 120
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        if session_id not in _stream_logs:
            await asyncio.sleep(0.3)
            continue
        
        session_data = _stream_logs[session_id]
        log_entries = session_data.get("logs", [])
        
        # Send new logs
        for log_entry in log_entries[seen_count:]:
            yield f"data: {json.dumps({'type': 'log', 'content': log_entry})}\n\n"
        seen_count = len(log_entries)
        
        # Check if done
        if session_data.get("done", False):
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            del _stream_logs[session_id]
            return
        
        await asyncio.sleep(0.3)
    
    yield f"data: {json.dumps({'type': 'timeout'})}\n\n"


# --- API Endpoints ---

@app.get("/api/plan/stream/{session_id}")
async def stream_plan_logs(session_id: str) -> StreamingResponse:
    """SSE endpoint for streaming refinement logs."""
    return StreamingResponse(
        stream_refinement_log(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/api/plan", response_model=SlidePlan)
async def generate_plan_endpoint(request: GeneratePlanRequest, session_id: Optional[str] = None) -> SlidePlan:
    """Generates a slide plan based on the user's request."""
    logger.info(f"Generating plan for text: {request.text[:50]}... (session: {session_id})")
    
    if session_id:
        _stream_logs[session_id] = {"logs": [], "done": False}
    
    def push_log(message: str) -> None:
        if session_id and session_id in _stream_logs:
            _stream_logs[session_id]["logs"].append(message)
    
    try:
        push_log("Analyzing requirements...")
        
        style: Optional[StyleDef] = request.style_def
        if not style:
            push_log("Extracting style from topic...")
            style = await extract_style_from_text(request.text)
            push_log(f"Style extracted: {style.global_prompt[:50]}...")
        
        initial_state = _create_initial_project_state(request.text, style.model_dump())
        push_log("Director is creating initial plan...")
        
        final_state = await planning_app.ainvoke(initial_state)
        
        for log_entry in final_state.get("refinement_log", []):
            push_log(log_entry)
        push_log("Refiner completed review")
        
        generated_plan: Optional[SlidePlan] = final_state.get("slide_plan")
        if not generated_plan:
            raise ValueError("Failed to generate slide plan")

        generated_plan.refinement_log = final_state.get("refinement_log", [])
        push_log(f"Plan complete: {len(generated_plan.slides)} slides created")
        
        if session_id and session_id in _stream_logs:
            _stream_logs[session_id]["done"] = True
        
        return generated_plan
    
    except Exception as e:
        logger.error(f"Error in generate_plan: {e}")
        if session_id and session_id in _stream_logs:
            _stream_logs[session_id]["logs"].append(f"Error: {str(e)}")
            _stream_logs[session_id]["done"] = True
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/style", response_model=StyleDef)
async def generate_style_endpoint(
    description: str = Form(""),
    file: Optional[UploadFile] = File(None)
) -> StyleDef:
    """Generates a style definition based on description and/or uploaded file."""
    logger.info(f"Generating style for description: {description}")
    try:
        file_bytes = None
        mime_type = None
        if file:
            file_bytes = await file.read()
            mime_type = file.content_type
            
        return await extract_style_from_text(description, file_bytes, mime_type)
    except Exception as e:
        logger.error(f"Error in generate_style: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-slide")
async def generate_slide_endpoint(request: GenerateImageRequest) -> Dict[str, Any]:
    """Generates an image for a single slide."""
    logger.info(f"Generating image for slide {request.slide.slide_id}")
    try:
        mock_plan = SlidePlan(slides=[request.slide])
        style_guideline = request.style_def.model_dump() if request.style_def else {}
        
        exec_state: ProjectState = _create_initial_project_state("", style_guideline)
        exec_state["slide_plan"] = mock_plan
        
        final_state = await execution_app.invoke(exec_state)
        
        generated_images = final_state.get("generated_images", {})
        image_url = generated_images.get(request.slide.slide_id)
        
        if not image_url:
            raise HTTPException(status_code=500, detail="Image generation failed in workflow.")
            
        return {"url": image_url, "slide_id": request.slide.slide_id}

    except Exception as e:
        logger.error(f"Error in generate_slide: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/edit-slide", response_model=Slide)
async def edit_slide_endpoint(request: EditSlideRequest) -> Slide:
    """Edits a slide plan based on instructions."""
    if not request.instruction:
        raise HTTPException(status_code=400, detail="instruction is required.")
    if not request.slide and not request.plan:
        raise HTTPException(status_code=400, detail="slide or plan is required.")
    
    try:
        updated_slide = await edit_slide(
            instruction=request.instruction,
            slide=request.slide,
            plan=request.plan,
            style_def=request.style_def,
        )
        return updated_slide
    except Exception as e:
        logger.error(f"Error in edit_slide: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/assemble")
async def assemble_endpoint(request: AssembleRequest) -> Dict[str, str]:
    """Assembles generated images into a PDF."""
    logger.info(f"Assembling PDF from {len(request.image_urls)} images")
    try:
        image_bytes_list = _load_image_bytes_from_urls(request.image_urls)
        
        await _run_style_consistency_check(image_bytes_list)
        
        if not image_bytes_list:
            raise HTTPException(status_code=400, detail="No valid images found")

        pdf_bytes = assemble_pdf(image_bytes_list)
        
        pdf_filename = f"{uuid.uuid4()}.pdf"
        pdf_filepath = f"static/pdfs/{pdf_filename}"
        with open(pdf_filepath, "wb") as f:
            f.write(pdf_bytes)
            
        return {"url": f"http://localhost:8000/static/pdfs/{pdf_filename}"}
    except Exception as e:
        logger.error(f"Error in assemble: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/think")
async def think_endpoint(request: ThinkingRequest) -> Dict[str, str]:
    """Generates a thought for the AI agent."""
    try:
        thought = await generate_thought(request.phase, request.context)
        return {"thought": thought}
    except Exception as e:
        logger.error(f"Error in think: {e}")
        return {"thought": "Processing..."}


@app.post("/api/inpaint-slide")
async def inpaint_slide_endpoint(request: InpaintRequest) -> Dict[str, Any]:
    """Inpaints (edits) a slide based on an instruction and mask."""
    logger.info(f"Inpainting slide {request.slide_id} with instruction: {request.instruction}")
    try:
        original_image_path = _find_original_image_path(request.image_filename)
        with open(original_image_path, "rb") as f:
            base_image_bytes = f.read()

        mask_bytes = _decode_base64_mask(request.mask_base64)
        
        new_image_bytes = await anyio.to_thread.run_sync(
            generate_inpainted_image,
            base_image_bytes,
            mask_bytes,
            request.instruction,
            request.style_def
        )
        
        new_filename = f"{uuid.uuid4()}.png"
        new_filepath = f"static/images/{new_filename}"
        with open(new_filepath, "wb") as f:
            f.write(new_image_bytes)
            
        return {
            "url": f"http://localhost:8000/static/images/{new_filename}", 
            "slide_id": request.slide_id
        }
        
    except Exception as e:
        logger.error(f"Error in inpaint_slide: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
