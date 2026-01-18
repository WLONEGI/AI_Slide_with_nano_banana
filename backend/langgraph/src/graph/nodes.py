import asyncio
import logging
import json
import random
from copy import deepcopy
from typing import Literal, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command, Send

from src.agents import research_agent, storywriter_agent, visualizer_agent
from src.agents.llm import get_llm_by_type
from src.config import TEAM_MEMBERS
from src.config.agents import AGENT_LLM_MAP
from src.config.settings import settings

from src.prompts.template import apply_prompt_template
from src.tools.search import google_search_tool
from src.schemas import (
    PlannerOutput,
    StorywriterOutput,
    VisualizerOutput,
    DataAnalystOutput,
    ReviewOutput,
    ThoughtSignature,
    ImagePrompt,
    StructuredImagePrompt,
    ResearchTask,     # NEW
    ResearchResult,   # NEW
)
from src.utils.image_generation import generate_image
from src.utils.storage import upload_to_gcs, download_blob_as_bytes

from .graph_types import State, TaskStep

logger = logging.getLogger(__name__)


def compile_structured_prompt(
    structured: StructuredImagePrompt,
    slide_number: int = 1
) -> str:
    """
    構造化プロンプトをMarkdownスライド形式の最終プロンプトに変換。
    
    出力形式:
    ```
    # Slide1: Title Slide
    ## The Evolution of Japan's Economy
    ### From Post-War Recovery to Future Innovation
    
    [Contents]
    
    Visual style: [English description]
    ```
    
    Args:
        structured: StructuredImagePrompt オブジェクト
        slide_number: スライド番号
        
    Returns:
        str: Geminiに送信する最終的なテキストプロンプト
    """
    prompt_lines = []
    
    # Slide Header: # Slide1: Title Slide
    prompt_lines.append(f"# Slide{slide_number}: {structured.slide_type}")
    
    # Main Title: ## The Evolution of Japan's Economy
    prompt_lines.append(f"## {structured.main_title}")
    
    # Sub Title (optional): ### From Post-War Recovery...
    if structured.sub_title:
        prompt_lines.append(f"### {structured.sub_title}")
    
    # Empty line before contents
    prompt_lines.append("")
    
    # Contents (optional)
    if structured.contents:
        prompt_lines.append(structured.contents)
        prompt_lines.append("")
    
    # Visual style
    prompt_lines.append(f"Visual style: {structured.visual_style}")
    
    # 最終プロンプト生成
    final_prompt = "\n".join(prompt_lines)
    logger.debug(f"Compiled slide prompt ({len(final_prompt)} chars)")
    
    return final_prompt


def _update_artifact(state: State, key: str, value: Any) -> dict[str, Any]:
    """Helper to update artifacts dictionary."""
    artifacts = state.get("artifacts", {})
    artifacts[key] = value
    return artifacts


def research_node(state: State) -> Command[Literal["supervisor"]]:
    """Node for the researcher agent (ReAct agent with google_search_tool)."""
    logger.info("Research agent starting task")
    # Inject specific instruction from plan if available
    current_step = state["plan"][state["current_step_index"]]
    instruction_msg = HumanMessage(content=f"Requirement: {current_step['instruction']}", name="supervisor")
    
    # Temporarily append instruction to messages for this invoke
    invoke_state = deepcopy(state)
    invoke_state["messages"].append(instruction_msg)
    
    result = research_agent.invoke(invoke_state, {"recursion_limit": settings.RECURSION_LIMIT_RESEARCHER})  # max tool calls
    content = result["messages"][-1].content
    
    return Command(
        update={
            "messages": [
                HumanMessage(content=settings.RESPONSE_FORMAT.format(role="researcher", content=content), name="researcher")
            ],
            "artifacts": _update_artifact(state, f"step_{current_step['id']}_research", content)
        },
        goto="reviewer",
    )




def storywriter_node(state: State) -> Command[Literal["supervisor"]]:
    """Node for storywriter agent - uses structured output."""
    logger.info("Storywriter starting task")
    current_step = state["plan"][state["current_step_index"]]
    
    # Provide context including artifacts
    context = f"Instruction: {current_step['instruction']}\n\nAvailable Artifacts: {json.dumps(state.get('artifacts', {}), default=str)}"
    
    # Build messages with prompt template
    messages = apply_prompt_template("storywriter", state)
    messages.append(HumanMessage(content=context, name="supervisor"))
    
    # Use structured output with Pydantic schema
    llm = get_llm_by_type(AGENT_LLM_MAP["storywriter"])
    structured_llm = llm.with_structured_output(StorywriterOutput)
    
    try:
        result: StorywriterOutput = structured_llm.invoke(messages)
        content_json = result.model_dump_json(ensure_ascii=False, indent=2)
        logger.info(f"Storywriter generated {len(result.slides)} slides")
    except Exception as e:
        logger.error(f"Storywriter structured output failed: {e}")
        content_json = json.dumps({"error": str(e)}, ensure_ascii=False)

    return Command(
        update={
            "messages": [HumanMessage(content=settings.RESPONSE_FORMAT.format(role="storywriter", content=content_json), name="storywriter")],
            "artifacts": _update_artifact(state, f"step_{current_step['id']}_story", content_json)
        },
        goto="reviewer",
    )

# Helper for single slide processing
async def process_single_slide(
    prompt_item: ImagePrompt, 
    previous_generations: list[dict] | None = None, 
    override_reference_bytes: bytes | None = None,
    design_context: Any = None,  # DesignContext | None (型ヒントは循環参照を避けるためAny)
) -> ImagePrompt:
    """
    Helper function to process a single slide: generation or edit.

    Handles the core image generation logic, including:
    1. Template reference image selection (based on layout_type in design_context).
    2. Seed management for determinism (reusing seed from ThoughtSignature).
    3. Reference image handling for Deep Edit / Visual Consistency.
    4. **Structured Prompt Compilation**: Converts StructuredImagePrompt to final text.
    5. Image generation via Vertex AI.
    6. Uploading to GCS.

    Args:
        prompt_item (ImagePrompt): The prompt object containing the image generation instruction.
        previous_generations (list[dict] | None): List of previous generation data for "Deep Edit" logic.
        override_reference_bytes (bytes | None): Optional image bytes to force as a reference (e.g., Anchor Image).
                                                 If provided, this takes precedence over previous generations.
        design_context: DesignContext with layout-based template images (optional).

    Returns:
        ImagePrompt: Updated prompt item with `generated_image_url` and `thought_signature` populated.

    Raises:
        Exception: Captures and logs generation failures, returning the item with None URL to allow partial batch success.
    """

    try:
        layout_type = getattr(prompt_item, 'layout_type', 'title_and_content')
        logger.info(f"Processing slide {prompt_item.slide_number} (layout: {layout_type})...")
        
        # === Compile Structured Prompt (v2) ===
        # 優先度: structured_prompt > image_generation_prompt
        if prompt_item.structured_prompt is not None:
            final_prompt = compile_structured_prompt(
                prompt_item.structured_prompt,
                slide_number=prompt_item.slide_number
            )
            logger.info(f"Using structured prompt for slide {prompt_item.slide_number}")
        elif prompt_item.image_generation_prompt:
            final_prompt = prompt_item.image_generation_prompt
            logger.info(f"Using legacy prompt for slide {prompt_item.slide_number}")
        else:
            raise ValueError(f"Slide {prompt_item.slide_number} has neither structured_prompt nor image_generation_prompt")
        
        # === Reference Image Selection ===
        seed = None
        reference_image_bytes = None
        reference_url = None
        previous_thought_signature_token = None # [NEW] Unknown opaque token from Gemini 3.0 API
        
        # 1. Use Override (Anchor Image) if provided - highest priority
        if override_reference_bytes:
            logger.info(f"Using explicit override reference for slide {prompt_item.slide_number}")
            reference_image_bytes = override_reference_bytes
        
        # 2. [NEW] Use DesignContext layout-based template image
        elif design_context:
            # design_context.get_template_image_for_layout() returns bytes or None
            layout_ref = design_context.get_template_image_for_layout(layout_type)
            if layout_ref:
                reference_image_bytes = layout_ref
                logger.info(f"Using template image for layout '{layout_type}'")
            else:
                logger.warning(f"No template image found for layout '{layout_type}'")
        
        # 3. Check for matching previous generation (Deep Edit)
        elif previous_generations:
            for prev in previous_generations:
                if prev.get("slide_number") != prompt_item.slide_number:
                    continue
                
                # Reuse Seed and Thought Signature
                prev_sig = prev.get("thought_signature")
                if prev_sig:
                    if "seed" in prev_sig:
                        seed = prev_sig["seed"]
                        logger.info(f"Reusing seed {seed} from ThoughtSignature")
                    
                    # [NEW] Reuse opaque API token for Gemini 3.0 Consistency
                    if "api_thought_signature" in prev_sig and prev_sig["api_thought_signature"]:
                        previous_thought_signature_token = prev_sig["api_thought_signature"]
                        logger.info("Found persistent 'api_thought_signature' for Deep Edit consistency.")

                # Reference Anchor (Visual Consistency)
                if prev.get("generated_image_url"):
                    reference_url = prev["generated_image_url"]
                    logger.info(f"Downloading reference anchor from {reference_url}...")
                    try:
                        reference_image_bytes = await asyncio.to_thread(download_blob_as_bytes, reference_url)
                    except Exception as e:
                        logger.warning(f"Failed to download previous reference image: {e}")
                
                break
        
        if seed is None:
            seed = random.randint(0, 2**32 - 1)

        logger.info(f"Generating image {prompt_item.slide_number} with Seed: {seed}, Ref: {bool(reference_image_bytes)}...")
        
        # 1. Generate Image (Blocking -> Thread)
        # Returns tuple (bytes, thought_signature_str)
        generation_result = await asyncio.to_thread(
            generate_image,
            final_prompt,  # CHANGED: Use compiled prompt
            seed=seed,
            reference_image=reference_image_bytes,
            thought_signature=previous_thought_signature_token
        )
        
        image_bytes, new_api_token = generation_result
        
        # 2. Upload to GCS (Blocking -> Thread)
        logger.info(f"Uploading image {prompt_item.slide_number} to GCS...")
        public_url = await asyncio.to_thread(upload_to_gcs, image_bytes, content_type="image/png")
        
        # 3. Update Result & Signature
        prompt_item.generated_image_url = public_url
        
        # Create ThoughtSignature
        prompt_item.thought_signature = ThoughtSignature(
            seed=seed,
            base_prompt=final_prompt,  # CHANGED: Store compiled prompt
            refined_prompt=None,
            model_version=AGENT_LLM_MAP["visualizer"],
            reference_image_url=reference_url or (prompt_item.thought_signature.reference_image_url if prompt_item.thought_signature else None),
            api_thought_signature=new_api_token # [NEW] Store the opaque token
        )
        
        logger.info(f"Image generated and stored at: {public_url}")
        return prompt_item

    except Exception as image_error:
        logger.error(f"Failed to generate/upload image for prompt {prompt_item.slide_number}: {image_error}")
        # Return item as-is (with None URL) to avoid crashing the whole batch
        return prompt_item


async def visualizer_node(state: State) -> Command[Literal["supervisor"]]:
    """
    Node for the Visualizer agent. Responsible for generating slide images.

    This node executes the following complex logic:
    1. **Context Preparation**: Gathers instructions and previous artifacts.
    2. **Edit Mode Detection**: Identifies if this is a modification of existing slides.
    3. **Prompt Generation**: Uses the LLM to generate image prompts (ImagePrompt schema).
    4. **Anchor Strategy (Visual Consistency)**:
        - **Strategy T (Template)**: Uses PPTX template images per layout_type (NEW - highest priority).
        - **Strategy A (Preferred)**: Generates a dedicated 'Style Anchor' image first, then uses it as a reference for all slides.
        - **Strategy B (Reuse)**: Reuses an existing anchor from a previous run (Deep Edit).
        - **Strategy C (Fallback)**: Uses the first slide as the anchor if no dedicated style is defined.
    5. **Parallel Execution**: Generates images concurrently using `asyncio.gather` with a semaphore.

    Args:
        state (State): Current graph state.

    Returns:
        Command[Literal["supervisor"]]: Route to supervisor (via reviewer) with generated artifacts.
    """
    logger.info("Visualizer starting task")
    current_step = state["plan"][state["current_step_index"]]
    
    # [NEW] Get DesignContext from state
    design_context = state.get("design_context")
    
    context = f"Instruction: {current_step['instruction']}\n\nAvailable Artifacts: {json.dumps(state.get('artifacts', {}), default=str)}"

    # [NEW] Inject Design Direction from Planner
    design_dir = current_step.get('design_direction')
    if design_dir:
        context += f"\n\n[Design Direction from Planner]:\n{design_dir}\n"


    # [NEW] Inject design context information into prompt
    if design_context:
        available_layouts = ", ".join([l.layout_type for l in design_context.layouts])
        color_context = f"""

## Template Design Context
- Primary colors: {design_context.color_scheme.accent1}, {design_context.color_scheme.accent2}
- Background: {design_context.color_scheme.dk1}
- Text: {design_context.color_scheme.lt1}
- Font style: {design_context.font_scheme.major_latin} (headings)
- Available layout types: {available_layouts}

## IMPORTANT: Layout Type Selection
For each slide, you MUST specify the appropriate `layout_type` based on the slide's purpose:
- "title_slide": Opening or closing slides with large centered title
- "section_header": Section dividers
- "comparison": Side-by-side comparison slides
- "title_and_content": Standard content slides with title and bullet points
- "picture_with_caption": Image-focused slides
- "blank": Full-bleed visuals without text areas
- "other": Custom layouts

The template image for each layout will be automatically used as a reference image.
"""
        context = context + color_context

    # === Phase 3: Deep Edit Workflow (Thought Signature) ===
    # Check for previous visualizer outputs to enable "Edit Mode"
    previous_generations: list[dict] = []
    for key, json_str in state.get("artifacts", {}).items():
        if key.endswith("_visual"):
            try:
                data = json.loads(json_str)
                if "prompts" in data:
                    previous_generations.extend(data["prompts"])
            except Exception:
                pass
    
    # Check for previous Anchor URL
    previous_anchor_url = None
    for key, json_str in state.get("artifacts", {}).items():
        if key.endswith("_visual"):
            try:
                data = json.loads(json_str)
                if "anchor_image_url" in data and data["anchor_image_url"]:
                    previous_anchor_url = data["anchor_image_url"]
                    logger.info(f"Found existing Anchor URL in artifacts: {previous_anchor_url}")
                    break # Use the first found anchor
            except Exception:
                pass
    
    if previous_generations:
        context += f"\n\n# PREVIOUS GENERATIONS (EDIT MODE)\nUser wants to modify these. Maintain consistency with seed/style if specified:\n{json.dumps(previous_generations, ensure_ascii=False, indent=2)}"
    
    # Build messages with prompt template
    messages = apply_prompt_template("visualizer", state)
    messages.append(HumanMessage(content=context, name="supervisor"))
    
    # Use structured output with Pydantic schema
    llm = get_llm_by_type(AGENT_LLM_MAP["visualizer"])
    structured_llm = llm.with_structured_output(VisualizerOutput)
    
    try:
        result: VisualizerOutput = structured_llm.invoke(messages)
        
        prompts = result.prompts
        updated_prompts: list[ImagePrompt] = []
        anchor_bytes: bytes | None = None
        
        # === [NEW] STRATEGY T: Template-based (Per-Layout Reference) ===
        # This is the highest priority strategy when design_context is available
        if design_context and design_context.layout_image_bytes:
            logger.info("Using per-layout template images (Strategy T)")
            
            # Parallel processing with layout-based reference images
            semaphore = asyncio.Semaphore(settings.VISUALIZER_CONCURRENCY)
            
            async def constrained_task_template(prompt_item: ImagePrompt) -> ImagePrompt:
                async with semaphore:
                    # Pass design_context to select layout-specific reference image
                    return await process_single_slide(
                        prompt_item, 
                        previous_generations,
                        override_reference_bytes=None,  # Don't override - let design_context handle selection
                        design_context=design_context,
                    )
            
            tasks = [constrained_task_template(item) for item in prompts]
            if tasks:
                logger.info(f"Starting parallel generation for {len(tasks)} slides with per-layout templates...")
                updated_prompts = list(await asyncio.gather(*tasks))
        
        # === Existing Anchor Strategies (when no design_context) ===
        else:
            anchor_prompt_text = result.anchor_image_prompt
            
            if anchor_prompt_text:
                # === STRATEGY A: Separate Style Anchor (Preferred) ===
                logger.info("Found 'anchor_image_prompt'. Generating dedicated Style Anchor Image...")
                
                anchor_item = ImagePrompt(
                    slide_number=0, # 0 for Anchor
                    image_generation_prompt=anchor_prompt_text,
                    rationale="Style Anchor for consistency"
                )
                
                # Process Anchor
                processed_anchor = await process_single_slide(
                    anchor_item, 
                    previous_generations, 
                    override_reference_bytes=None,
                )
                
                if processed_anchor.generated_image_url:
                    try:
                        anchor_bytes = await asyncio.to_thread(download_blob_as_bytes, processed_anchor.generated_image_url)
                        logger.info(f"Style Anchor Image downloaded ({len(anchor_bytes)} bytes).")
                        result.anchor_image_url = processed_anchor.generated_image_url
                    except Exception as e:
                        logger.error(f"Failed to download Style Anchor Image: {e}. Proceeding without anchor.")
                
                target_prompts = prompts

            elif previous_anchor_url:
                # === STRATEGY B: Reuse Existing Style Anchor (Deep Edit) ===
                logger.info(f"Reusing existing Anchor URL: {previous_anchor_url}")
                try:
                    anchor_bytes = await asyncio.to_thread(download_blob_as_bytes, previous_anchor_url)
                    logger.info(f"Existing Style Anchor downloaded ({len(anchor_bytes)} bytes).")
                    result.anchor_image_url = previous_anchor_url
                except Exception as e:
                    logger.error(f"Failed to download existing Style Anchor: {e}. Falling back to Slide 1 strategy.")
                    anchor_bytes = None
                    
                target_prompts = prompts

            elif prompts:
                # === STRATEGY C: First Slide as Anchor (Fallback) ===
                logger.info("No 'anchor_image_prompt' found. Using Slide 1 as Anchor (Fallback Strategy)...")
                
                anchor_prompt = prompts[0]
                processed_anchor = await process_single_slide(
                    anchor_prompt, 
                    previous_generations, 
                    override_reference_bytes=None,
                )
                updated_prompts.append(processed_anchor)
                
                if processed_anchor.generated_image_url:
                    try:
                        anchor_bytes = await asyncio.to_thread(download_blob_as_bytes, processed_anchor.generated_image_url)
                        logger.info("Anchor Image (Slide 1) downloaded.")
                    except Exception as e:
                        logger.error(f"Failed to download Anchor Image: {e}.")
                
                target_prompts = prompts[1:]
            else:
                logger.warning("No prompts generated by Visualizer.")
                target_prompts = []

            # Parallel Processing for Target Prompts (for Strategy A/B/C)
            if target_prompts:
                semaphore = asyncio.Semaphore(settings.VISUALIZER_CONCURRENCY)
                
                async def constrained_task(prompt_item: ImagePrompt, idx: int) -> ImagePrompt:
                    async with semaphore:
                        return await process_single_slide(
                            prompt_item, 
                            previous_generations, 
                            override_reference_bytes=anchor_bytes,
                        )
                
                tasks = [constrained_task(item, i) for i, item in enumerate(target_prompts)]
                
                if tasks:
                    logger.info(f"Starting parallel generation for {len(tasks)} slides using Anchor...")
                    processed_targets = await asyncio.gather(*tasks)
                    updated_prompts.extend(processed_targets)
        
        # Update results
        # Sort by slide number just in case
        updated_prompts.sort(key=lambda x: x.slide_number)
        result.prompts = updated_prompts
        
        content_json = json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
        logger.info(f"Visualizer generated {len(result.prompts)} image prompts with artifacts")
    except Exception as e:
        logger.error(f"Visualizer structured output failed: {e}")
        content_json = json.dumps({"error": str(e)}, ensure_ascii=False)
    
    return Command(
        update={
            "messages": [HumanMessage(content=settings.RESPONSE_FORMAT.format(role="visualizer", content=content_json), name="visualizer")],
            "artifacts": _update_artifact(state, f"step_{current_step['id']}_visual", content_json)
        },
        goto="reviewer",
    )

def data_analyst_node(state: State) -> Command[Literal["supervisor"]]:
    """Node for data analyst agent - uses structured output."""
    logger.info("Data Analyst starting task")
    current_step = state["plan"][state["current_step_index"]]

    context = f"Instruction: {current_step['instruction']}\n\nAvailable Artifacts: {json.dumps(state.get('artifacts', {}), default=str)}"

    # Build messages with prompt template
    messages = apply_prompt_template("data_analyst", state)
    messages.append(HumanMessage(content=context, name="supervisor"))

    # Use structured output with Pydantic schema
    llm = get_llm_by_type(AGENT_LLM_MAP["data_analyst"])
    structured_llm = llm.with_structured_output(DataAnalystOutput)

    try:
        result: DataAnalystOutput = structured_llm.invoke(messages)
        content_json = result.model_dump_json(ensure_ascii=False, indent=2)
        logger.info(f"Data Analyst generated {len(result.blueprints)} blueprints")
    except Exception as e:
        logger.error(f"Data Analyst structured output failed: {e}")
        content_json = json.dumps({"error": str(e)}, ensure_ascii=False)

    return Command(
        update={
            "messages": [HumanMessage(content=settings.RESPONSE_FORMAT.format(role="data_analyst", content=content_json), name="data_analyst")],
            "artifacts": _update_artifact(state, f"step_{current_step['id']}_data", content_json)
        },
        goto="reviewer",
    )

def reviewer_node(state: State) -> Command[Literal["supervisor", "storywriter", "visualizer", "researcher", "data_analyst"]]:
    """
    Generic Reviewer (Critic) Node.
    
    Evaluates the quality of the output produced by the previous agent against the requirements.
    Implements a **Reflexion** loop:
    - **Approved**: Passes control back to Supervisor to proceed to the next step.
    - **Rejected**: Returns control to the Worker (Writer/Visualizer/etc.) for retry, up to MAX_RETRIES.
    - **Failed**: Escalates to Supervisor if max retries are exceeded.

    Args:
        state (State): Current graph state.

    Returns:
        Command: Routing command to either Supervisor (next step/fail) or Worker (retry).
    """
    logger.info("Reviewer evaluating output...")
    
    current_step = state["plan"][state["current_step_index"]]
    current_role = current_step["role"]
    
    # Identify the target artifact
    role_suffix_map = {
        "storywriter": "story",
        "visualizer": "visual",
        "coder": "code",
        "researcher": "research",
        "data_analyst": "data"
    }
    suffix = role_suffix_map.get(current_role, "unknown")
    artifact_key = f"step_{current_step['id']}_{suffix}"
    latest_artifact = state["artifacts"].get(artifact_key)
    
    if not latest_artifact:
        logger.error(f"No artifact found for review at {artifact_key}")
        # Skip review if artifact is missing (fail safe)
        return Command(goto="supervisor", update={"error_context": f"Missing artifact for {current_role}"})

    # LLM Evaluation (Using Reasoning Model)
    messages = [
        SystemMessage(content="You are a strict QA Lead. Grade the work based on instructions. Output must be in JSON."),
        HumanMessage(content=f"Instruction: {current_step['instruction']}\nOutput: {latest_artifact}")
    ]
    
    # Use structured output
    llm = get_llm_by_type("reasoning") # Use reasoning model for critique
    structured_llm = llm.with_structured_output(ReviewOutput)
    
    try:
        review: ReviewOutput = structured_llm.invoke(messages)
    except Exception as e:
        logger.error(f"Review structured output failed: {e}")
        # If critique fails, default to approved to avoid blocking workflow
        review = ReviewOutput(approved=True, score=0.5, feedback=f"Auto-approved due to critic error: {e}")

    # --- Routing Logic (Reflexion) ---
    current_retries = state.get("retry_count", 0)
    feedback_history = state.get("feedback_history", {})
    step_id_str = str(current_step['id'])
    
    if step_id_str not in feedback_history:
        feedback_history[step_id_str] = []

    # Case 1: Approved
    if review.approved:
        logger.info(f"Work approved (Score: {review.score})")
        feedback_history[step_id_str].append(f"APPROVED: {review.feedback}")
        return Command(
            goto="supervisor",
            update={
                "current_quality_score": review.score,
                "feedback_history": feedback_history,
                # [FIX] Add message so Supervisor knows Reviewer finished
                "messages": [HumanMessage(content=f"Step {current_step['id']} approved by Reviewer.", name="reviewer")],
                # [NEW] Explicit State Update
                "review_status": "approved"
            }
        )

    # Case 2: Rejected (Retry available)
    if current_retries < settings.MAX_RETRIES:
        logger.info(f"Rejecting work (Score: {review.score}). Retry {current_retries + 1}/{settings.MAX_RETRIES}")
        feedback_history[step_id_str].append(f"REJECTED: {review.feedback}")
        return Command(
            goto=current_role, # Route back to Worker
            update={
                "retry_count": current_retries + 1,
                "messages": [HumanMessage(content=f"Review Feedback (QC Failed, Score={review.score}): {review.feedback}. Please fix and regenerate.", name="reviewer")],
                "feedback_history": feedback_history,
                # [NEW] Explicit State Update
                "review_status": "rejected"
            }
        )
    
    # Case 3: Rejected (Max retries exceeded)
    logger.warning("Max retries reached. Escalating to Supervisor.")
    feedback_history[step_id_str].append(f"FAILED (Max Retries): {review.feedback}")
    return Command(
        goto="supervisor",
        update={
            "error_context": f"Failed criteria after {settings.MAX_RETRIES} retries. Last feedback: {review.feedback}",
            "feedback_history": feedback_history
        }
    )

def supervisor_node(state: State) -> Command[Literal[*TEAM_MEMBERS, "planner", "__end__", "reviewer"]]:
    """
    Supervisor Node (Orchestrator).

    Manages the execution flow of the graph.
    - **Task Assignment**: Routes to the appropriate worker based on the current plan step.
    - **Progress Tracking**: Moves to the next step upon successful completion (signaled by Reviewer).
    - **Dynamic Replanning**: triggers the Planner if the workflow stalls or encounters unrecoverable errors (Error Context).
    - **Completion**: Routes to END when all steps are finished.

    Args:
        state (State): Current graph state.

    Returns:
        Command: Routing command to Worker, Planner, or END.
    """
    logger.info("Supervisor evaluating state")
    
    step_index = state.get("current_step_index", 0)
    plan = state.get("plan", [])
    error_context = state.get("error_context")

    # --- 1. Dynamic Replanning Trigger ---
    if error_context:
        current_replans = state.get("replanning_count", 0)
        max_replans = settings.MAX_REPLANNING
        
        if current_replans >= max_replans:
            logger.critical(f"Max replanning limit ({max_replans}) reached. Force stopping to prevent infinite loop.")
            return Command(
                goto="__end__",
                update={
                    "messages": [HumanMessage(content=f"System Stopped: Unable to complete task after {max_replans} replanning attempts. Last error: {error_context}", name="supervisor")]
                }
            )

        logger.error(f"Critical Failure/Stall detected: {error_context}. Requesting Re-planning ({current_replans + 1}/{max_replans}).")
        return Command(
            goto="planner",
            update={
                "messages": [HumanMessage(content=f"Replanning Request: Current plan stalled at step {step_index+1}. Reason: {error_context}", name="supervisor")],
                "retry_count": 0,
                "replanning_count": current_replans + 1,
                "error_context": None 
            }
        )

    # --- 2. Normal Plan Progression ---
    if step_index >= len(plan):
        logger.info("All steps completed. Converting artifacts to final response.")
        return Command(goto="__end__", update={"current_step_index": step_index})

    next_step = plan[step_index]
    current_role = next_step["role"]
    
    # Check if we are coming from a successful Review
    # Logic: Check explicit "review_status" state first.
    # If not present (backward compatibility), fall back to checking strict message sender.
    
    review_status = state.get("review_status")
    last_message_from_reviewer = False
    messages = state.get("messages", [])
    if messages and messages[-1].name == "reviewer":
        last_message_from_reviewer = True

    if review_status == "approved" or (review_status is None and last_message_from_reviewer):
         # Moved to next step
         new_index = step_index + 1
         logger.info(f"Step {step_index} approved. Moving to Step {new_index}")
         
         if new_index >= len(plan):
             return Command(goto="__end__", update={"current_step_index": new_index})
             
         next_step = plan[new_index] # Update to new next step
         return Command(
            goto=next_step["role"],
            update={
                "current_step_index": new_index,
                "retry_count": 0,
                # "feedback_history": {} # Keep history for audit trail
                "review_status": "pending" # Reset status for next step
            }
        )

    # Initial Assignment (or standard progression)
    logger.info(f"Assigning task to {next_step['role']}")
    return Command(
        goto=next_step["role"],
        update={"retry_count": 0}
    )

def planner_node(state: State) -> Command[Literal["supervisor", "__end__"]]:
    """Planner node - uses structured output for reliable JSON execution plan."""
    logger.info("Planner creating execution plan")
    messages = apply_prompt_template("planner", state)
    
    # Add search results if needed (keep existing logic)
    if state.get("search_before_planning"):
        searched_content = google_search_tool.invoke(state["messages"][-1].content)
        messages = deepcopy(messages)
        messages[-1].content += f"\n\n# Relative Search Results\n\n{searched_content}"

    # Use structured output with Pydantic schema
    llm = get_llm_by_type("reasoning")
    structured_llm = llm.with_structured_output(PlannerOutput)
    
    try:
        result: PlannerOutput = structured_llm.invoke(messages)
        plan_data = [step.model_dump() for step in result.steps]
        
        logger.info(f"Plan generated with {len(plan_data)} steps (structured output).")
        return Command(
            update={
                "messages": [HumanMessage(content=f"Plan Generated: {len(plan_data)} steps defined.", name="planner")],
                "plan": plan_data,
                "current_step_index": 0,
                "artifacts": {}
            },
            goto="supervisor",
        )
    except Exception as e:
        logger.error(f"Planner structured output failed: {e}")
        return Command(
            update={"messages": [HumanMessage(content=f"Failed to generate a valid plan: {e}", name="planner")]},
            goto="__end__"
        )

def coordinator_node(state: State) -> Command[Literal["planner", "__end__"]]:
    """Coordinator: Gatekeeper."""
    logger.info("Coordinator processing request")
    messages = apply_prompt_template("coordinator", state)
    response = get_llm_by_type(AGENT_LLM_MAP["coordinator"]).invoke(messages)
    content = response.content
    
    # [Fix] Handle multimodal content (list of dicts) from Gemini
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        content = "".join(text_parts)
    
    logger.debug(f"Coordinator response: {content}")
    logger.debug(f"Coordinator Raw Content: '{content}'")
    logger.debug(f"Tool Calls: {response.tool_calls}")
    logger.debug(f"Additional Kwargs: {response.additional_kwargs}")

    if "handoff_to_planner" in content:
        logger.info("Handing off to planner detected.")
        return Command(goto="planner")
    
    # Simple chat response
    return Command(
        update={"messages": [HumanMessage(content=content, name="coordinator")]},
        goto="__end__"
    )


# === Parallel Researcher Nodes ===

def research_dispatcher_node(state: State) -> dict:
    """
    Dispatcher node for parallel research.
    Prepares tasks for the fan-out edge.
    If 'research_tasks' is empty (legacy plan), creates a single task from the instruction.
    Returning dict to update state, allowing conditional edge to run next.
    """
    logger.info("Research Dispatcher: Preparing tasks...")
    
    # 1. Check for existing tasks from Planner
    tasks = state.get("research_tasks", [])
    
    # 2. If empty, create legacy single task (Backward Compatibility)
    if not tasks:
        current_step = state["plan"][state["current_step_index"]]
        legacy_task = ResearchTask(
            id=0,
            perspective="General Investigation",
            query_hints=[], 
            priority="medium",
            expected_output=f"Detailed report based on: {current_step['instruction']}"
        )
        tasks = [legacy_task]
        logger.info("Created legacy single task for research.")
    
    # 3. Update State (Clear previous results)
    return {
        "research_tasks": tasks,
        "research_results": [] 
    }


def fan_out_research(state: State) -> list[Send]:
    """Conditional edge logic for fanning out research tasks to workers."""
    tasks = state.get("research_tasks", [])
    logger.info(f"Fanning out {len(tasks)} research tasks.")
    
    return [
        Send("research_worker", {"task": task}) 
        for task in tasks
    ]


def research_worker_node(state: dict) -> dict:
    """
    Worker node for executing a single research task.
    Receives only the specific 'task' payload (not full state).
    """
    task: ResearchTask = state.get("task")
    if not task:
        # Fallback or error handling
        return {"research_results": []}

    logger.info(f"Worker executing task {task.id}: {task.perspective}")
    
    try:
        # Construct specific instruction for the Research Agent
        instruction = (
            f"You are investigating: '{task.perspective}'.\n"
            f"Requirement: {task.expected_output}\n"
        )
        if task.query_hints:
            instruction += f"Suggested Queries: {', '.join(task.query_hints)}"
            
        # Create a fresh message history for this task to keep context clean
        # We need to simulate a clean state for the agent
        messages = [HumanMessage(content=instruction, name="dispatcher")]
        
        # Invoke the ReAct Agent
        # Note: We pass a strict recursion limit to prevent infinite loops
        result = research_agent.invoke(
            {"messages": messages}, 
            {"recursion_limit": settings.RECURSION_LIMIT_RESEARCHER}
        )
        content = result["messages"][-1].content
        
        # Note: Ideally we parse sources from tool calls, but here we take the final answer
        res = ResearchResult(
            task_id=task.id,
            perspective=task.perspective,
            report=content,
            sources=[], 
            confidence=1.0
        )
        return {"research_results": [res]}
        
    except Exception as e:
        logger.error(f"Worker failed task {task.id}: {e}")
        # Return error result to allow aggregation to proceed
        err_res = ResearchResult(
            task_id=task.id,
            perspective=task.perspective,
            report=f"## Error\nInvestigation failed: {str(e)}",
            sources=[],
            confidence=0.0
        )
        return {"research_results": [err_res]}


def research_aggregator_node(state: State) -> Command[Literal["reviewer"]]:
    """
    Aggregates all research results into a single step artifact.
    """
    logger.info("Aggregating research results...")
    results = state.get("research_results", [])
    
    # Sort by task ID to maintain logical order from Planner
    results.sort(key=lambda x: x.task_id)
    
    # Build Integrated Markdown Report
    report_lines = ["# Integrated Research Report\n"]
    
    for res in results:
        # Add Section Header
        report_lines.append(f"## {res.perspective}")
        if res.confidence < 0.5:
             report_lines.append("> [!WARNING]\n> This section encountered issues during investigation.\n")
        
        # Content
        report_lines.append(res.report)
        report_lines.append("\n---\n")
    
    full_content = "\n".join(report_lines)
    
    # Identify Artifact Key
    current_step = state["plan"][state["current_step_index"]]
    
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=settings.RESPONSE_FORMAT.format(
                        role="research_aggregator", 
                        content=f"Aggregated {len(results)} reports into final research document."
                    ), 
                    name="research_aggregator"
                )
            ],
            "artifacts": _update_artifact(state, f"step_{current_step['id']}_research", full_content)
        },
        goto="reviewer",
    )
