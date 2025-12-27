
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import io
import logging
import uuid
import os
from google import genai
from google.genai import types
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

# Ensure static dir exists
os.makedirs("static/images", exist_ok=True)

CODE_GEN_PROMPT: str = """
You are a Python data visualization expert. Generate matplotlib code to create a chart based on the description.

RULES:
1. Output ONLY valid Python code, no markdown fences or explanations.
2. Use matplotlib.pyplot as plt (already imported).
3. Create a single figure with plt.figure(figsize=(12, 7)).
4. Use professional styling: clean colors, readable fonts, proper labels.
5. End with plt.savefig(buf, format='png', dpi=150, bbox_inches='tight') where buf is a BytesIO object.
6. Do NOT call plt.show().
7. Make the chart visually appealing for a business presentation.

DESCRIPTION: {description}

Generate the Python code now:
"""

async def generate_chart_code(visual_description: str) -> str:
    """
    Asks Gemini to generate matplotlib code for the chart.

    Args:
        visual_description (str): Description of the chart to be generated.

    Returns:
        str: Generated Python code string.
    """
    try:
        client = genai.Client()
        prompt = CODE_GEN_PROMPT.format(description=visual_description)
        
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
            )
        )
        
        code: str = response.text.strip()
        # Clean up any markdown fences if present
        if code.startswith("```python"):
            code = code[9:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        
        return code.strip()
    except Exception as e:
        logger.error(f"LLM code generation failed: {e}")
        return ""


def execute_chart_code(code: str) -> bytes:
    """
    Safely execute generated matplotlib code.

    Args:
        code (str): The Python code to execute.

    Returns:
        bytes: The generated image bytes, or empty bytes on failure.
    """
    try:
        # Create the BytesIO buffer required by the generated code
        buf = io.BytesIO()
        
        # Define a restricted global namespace
        safe_globals: Dict[str, Any] = {
            'plt': plt,
            'buf': buf,
            'io': io,
            '__builtins__': {
                'range': range,
                'len': len,
                'list': list,
                'dict': dict,
                'str': str,
                'int': int,
                'float': float,
                'sum': sum,
                'max': max,
                'min': min,
                'abs': abs,
                'round': round,
                'enumerate': enumerate,
                'zip': zip,
            }
        }
        
        # Execute the code
        exec(code, safe_globals)
        
        # Get the result
        buf.seek(0)
        result: bytes = buf.read()
        
        plt.close('all')  # Clean up
        
        return result if result else b""
        
    except Exception as e:
        logger.error(f"Code execution failed: {e}")
        plt.close('all')
        return b""


def generate_fallback_chart(visual_description: str, title: str = "") -> bytes:
    """
    Fallback deterministic chart generation when LLM code fails.

    Args:
        visual_description (str): Description to infer chart type.
        title (str): Title for the chart.

    Returns:
        bytes: The generated image bytes.
    """
    logger.info("Using fallback chart generation")
    try:
        plt.figure(figsize=(12, 7))
        plt.style.use('seaborn-v0_8-whitegrid')
        
        if "bar" in visual_description.lower():
            categories = ['Q1', 'Q2', 'Q3', 'Q4']
            values = [23, 45, 56, 78]
            colors = ['#4F46E5', '#7C3AED', '#EC4899', '#F59E0B']
            plt.bar(categories, values, color=colors)
            plt.title(title or "Quarterly Performance", fontsize=16, fontweight='bold')
            plt.ylabel("Value", fontsize=12)
        elif "line" in visual_description.lower() or "trend" in visual_description.lower():
            x = range(1, 11)
            y = [10, 15, 13, 18, 20, 25, 28, 32, 35, 40]
            plt.plot(x, y, marker='o', linewidth=2, color='#4F46E5', markersize=8)
            plt.fill_between(x, y, alpha=0.2, color='#4F46E5')
            plt.title(title or "Growth Trend", fontsize=16, fontweight='bold')
            plt.xlabel("Period", fontsize=12)
            plt.ylabel("Value", fontsize=12)
        elif "pie" in visual_description.lower():
            labels = ['Product A', 'Product B', 'Product C', 'Others']
            sizes = [35, 30, 20, 15]
            colors = ['#4F46E5', '#7C3AED', '#EC4899', '#F59E0B']
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', 
                    startangle=90, explode=(0.02, 0, 0, 0))
            plt.title(title or "Market Distribution", fontsize=16, fontweight='bold')
        else:
            # Default: horizontal bar chart
            categories = ['Metric A', 'Metric B', 'Metric C', 'Metric D', 'Metric E']
            values = [85, 72, 90, 65, 78]
            colors = ['#4F46E5' if v >= 80 else '#94A3B8' for v in values]
            plt.barh(categories, values, color=colors)
            plt.title(title or "Performance Metrics", fontsize=16, fontweight='bold')
            plt.xlabel("Score (%)", fontsize=12)
            plt.xlim(0, 100)
            
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf.getvalue()
        
    except Exception as e:
        logger.error(f"Fallback chart error: {e}")
        plt.close('all')
        return b""


async def execute_code_worker(slide_id: int, visual_description: str) -> str:
    """
    Executes the code worker to generate a chart image.

    Args:
        slide_id (int): ID of the slide.
        visual_description (str): Description to generate chart from.

    Returns:
        str: URL of the generated chart image.
    """
    import anyio
    
    logger.info(f"Code Worker: Generating chart for slide {slide_id}: '{visual_description[:50]}...'")
    
    image_bytes: bytes = b""
    
    # Try LLM-generated code first
    code: str = await generate_chart_code(visual_description)
    if code:
        logger.info(f"LLM generated {len(code)} chars of code")
        image_bytes = await anyio.to_thread.run_sync(execute_chart_code, code)
    
    # Fallback if LLM code failed
    if not image_bytes:
        logger.warning("LLM code execution failed, using fallback")
        image_bytes = await anyio.to_thread.run_sync(
            generate_fallback_chart, 
            visual_description, 
            f"Slide {slide_id}"
        )
    
    if not image_bytes:
        logger.error("All chart generation methods failed")
        return ""
        
    filename: str = f"chart_{uuid.uuid4()}.png"
    filepath: str = f"static/images/{filename}"
    
    with open(filepath, "wb") as f:
        f.write(image_bytes)
        
    logger.info(f"Chart saved to {filepath}")
    return f"http://localhost:8000/static/images/{filename}"
