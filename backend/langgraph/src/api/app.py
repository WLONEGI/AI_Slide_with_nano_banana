"""
FastAPI application for Spell.
"""

import json
import logging
import base64
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
import asyncio

from src.graph import build_graph
from src.config import TEAM_MEMBERS
from contextlib import asynccontextmanager
from src.service.workflow_service import run_agent_workflow, initialize_graph, close_graph

# Configure logging
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI app.
    Handles startup and shutdown events.
    """
    logger.info("🚀 Starting Spell API...")
    logger.info("Initializing application resources...")
    try:
        await initialize_graph()
        logger.info("✅ Application initialized successfully.")
    except Exception as e:
        logger.critical(f"❌ Application startup failed: {e}")
        raise e  # Ensure app crashes on startup if initialization fails
    yield
    logger.info("Cleaning up application resources...")
    await close_graph()
    logger.info("👋 Application shutdown complete.")

# Create FastAPI app
app = FastAPI(
    title="Spell API",
    description="API for Spell LangGraph-based agent workflow",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Graph is now managed by service
# graph = build_graph()


class ContentItem(BaseModel):
    type: str = Field(..., description="The type of content (text, image, etc.)")
    text: str | None = Field(None, description="The text content if type is 'text'")
    image_url: str | None = Field(
        None, description="The image URL if type is 'image'"
    )


class ChatMessage(BaseModel):
    role: str = Field(
        ..., description="The role of the message sender (user or assistant)"
    )
    content: str | list[ContentItem] = Field(
        ...,
        description="The content of the message, either a string or a list of content items",
    )


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., description="The conversation history")
    debug: bool = Field(False, description="Whether to enable debug logging")
    deep_thinking_mode: bool = Field(
        False, description="Whether to enable deep thinking mode"
    )
    search_before_planning: bool = Field(
        False, description="Whether to search before planning"
    )
    thread_id: str | None = Field(None, description="The thread ID for persistence")
    pptx_template_base64: str | None = Field(
        None, 
        description="Base64-encoded PPTX template file for design context extraction"
    )


async def _extract_design_context(pptx_base64: str | None):
    """
    PPTXテンプレートからDesignContextを抽出する（AIワークフロー外の事前処理）
    
    Args:
        pptx_base64: Base64エンコードされたPPTXファイル
        
    Returns:
        DesignContext or None
    """
    if not pptx_base64:
        return None
    
    try:
        from src.utils.template_analyzer import analyze_pptx_template
        
        # Base64デコード
        pptx_bytes = base64.b64decode(pptx_base64)
        logger.info(f"Decoding PPTX template: {len(pptx_bytes)} bytes")
        
        # テンプレート解析（事前処理）
        design_context = await analyze_pptx_template(
            pptx_bytes,
            filename="uploaded_template.pptx",
            upload_to_gcs_enabled=True
        )
        
        logger.info(
            f"DesignContext extracted: {len(design_context.layouts)} layouts, "
            f"{len(design_context.layout_image_bytes)} layout images"
        )
        return design_context
        
    except ImportError as e:
        logger.warning(f"PPTX template analysis not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to extract design context: {e}")
        return None


@app.post("/api/chat/stream")
async def chat_endpoint(request: ChatRequest, req: Request):
    """
    Chat endpoint for LangGraph invoke.

    Args:
        request: The chat request
        req: The FastAPI request object for connection state checking

    Returns:
        The streamed response
    """
    try:
        # Convert Pydantic models to dictionaries and normalize content format
        messages = []
        for msg in request.messages:
            message_dict = {"role": msg.role}

            # Handle both string content and list of content items
            if isinstance(msg.content, str):
                message_dict["content"] = msg.content
            else:
                # For content as a list, convert to the format expected by the workflow
                content_items = []
                for item in msg.content:
                    if item.type == "text" and item.text:
                        content_items.append({"type": "text", "text": item.text})
                    elif item.type == "image" and item.image_url:
                        content_items.append(
                            {"type": "image", "image_url": item.image_url}
                        )

                message_dict["content"] = content_items

            messages.append(message_dict)

        # [NEW] PPTXテンプレートからDesignContextを抽出（事前処理）
        design_context = await _extract_design_context(request.pptx_template_base64)

        async def event_generator():
            try:
                async for event in run_agent_workflow(
                    messages,
                    request.debug,
                    request.deep_thinking_mode,
                    request.search_before_planning,
                    request.thread_id,
                    design_context=design_context,  # [NEW] 追加
                ):
                    # Check if client is still connected
                    if await req.is_disconnected():
                        logger.info("Client disconnected, stopping workflow")
                        break
                    yield {
                        "event": event["event"],
                        "data": json.dumps(event["data"], ensure_ascii=False),
                    }
            except asyncio.CancelledError:
                logger.info("Stream processing cancelled")
                raise

        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
            sep="\n",
        )
    except ValueError as e:
        logger.error(f"Invalid request data: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except HTTPException as e:
        raise e  # Re-raise HTTPExceptions (like from helpers)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "ok"}


@app.post("/api/template/analyze")
async def analyze_template_endpoint(file: UploadFile = File(...)):
    """
    PPTXテンプレートを解析してDesignContextを返すエンドポイント
    
    このエンドポイントは、テンプレートの事前解析に使用できます。
    フロントエンドでテンプレートをアップロードし、解析結果を
    キャッシュして後続のchatリクエストで使用できます。
    
    Args:
        file: アップロードされたPPTXファイル
        
    Returns:
        解析結果（JSON形式のDesignContext）
    """
    if not file.filename or not file.filename.endswith(('.pptx', '.PPTX')):
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Please upload a .pptx file."
        )
    
    try:
        from src.utils.template_analyzer import analyze_pptx_template
        
        # ファイル読み込み
        pptx_bytes = await file.read()
        logger.info(f"Received PPTX template: {file.filename} ({len(pptx_bytes)} bytes)")
        
        # テンプレート解析
        design_context = await analyze_pptx_template(
            pptx_bytes,
            filename=file.filename,
            upload_to_gcs_enabled=True
        )
        
        # レスポンス生成（layout_image_bytesは除外される）
        return {
            "success": True,
            "filename": file.filename,
            "design_context": design_context.model_dump(mode="json"),
            "summary": {
                "layouts_count": len(design_context.layouts),
                "layout_types": [l.layout_type for l in design_context.layouts],
                "color_scheme": {
                    "accent1": design_context.color_scheme.accent1,
                    "accent2": design_context.color_scheme.accent2,
                },
                "font_scheme": {
                    "major": design_context.font_scheme.major_latin,
                    "minor": design_context.font_scheme.minor_latin,
                }
            }
        }
        
    except ImportError as e:
        raise HTTPException(
            status_code=501,
            detail=f"PPTX template analysis dependencies not installed: {e}"
        )
    except Exception as e:
        logger.error(f"Error analyzing template: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze template: {str(e)}"
        )

