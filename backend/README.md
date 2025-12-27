# AI Slide Generator - Backend

FastAPI backend service for the AI Slide Generator Prototype.
Handles slide planning (Gemini), style extraction, image generation (Gemini 3 Pro Image Preview),
quality checks, and PDF assembly.

## Prerequisites

- Python 3.11+
- Virtual Environment (`venv`)
- Google Cloud Application Default Credentials (for Prod mode)
- `libreoffice` (only required when extracting style from PPTX)

## Setup

1.  **Create Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    # Or manual:
    pip install fastapi uvicorn google-cloud-aiplatform python-multipart pillow img2pdf python-dotenv
    ```
    *(Note: `libreoffice` is required for PPTX visual extraction.)*

## Configuration

Control the application mode via environment variables.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `dev` | `dev` for Mock Mode (no requests to Vertex AI). `prod` for Real Mode. |
| `GOOGLE_CLOUD_PROJECT` | - | Required in `prod` mode if not inferred from ADC. |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | Region for Vertex AI. |
| `GEMINI_API_KEY` | - | Required in `prod` mode for image generation. |
| `GEMINI_IMAGE_MODEL` | `gemini-3-pro-image-preview` | Image model name. |
| `GROUNDING_MODE` | `auto` | `auto` attempts grounded search; `off` disables grounding and the Sources slide. |
| `QUALITY_GATE_MODE` | `on` | `on` enables text legibility checks for text slides; `off` disables. |
| `STYLE_CONSISTENCY_MODE` | `on` | `on` enables cross-slide style consistency checks during assembly; `off` disables. |

## Running the Application

### Development (Mock Mode)
Uses internal mocks for Gemini and image generation. No cost, no credentials needed.

```bash
source venv/bin/activate
# Default is dev
uvicorn main:app --reload
# Or explicit:
APP_ENV=dev uvicorn main:app --reload
```

### Production (Real Mode)
Connects to Google Cloud Vertex AI for text/vision and Gemini API for image generation. Requires credentials.

```bash
source venv/bin/activate
APP_ENV=prod uvicorn main:app --reload
```

## API Endpoints

-   `POST /api/plan`: Generates a slide deck outline from text.
-   `POST /api/style`: Generates a `StyleDef` from text and/or an uploaded file (PPTX/PDF/image).
-   `POST /api/generate-slide`: Generates a single slide image.
-   `POST /api/edit-slide`: Updates a single slide based on user instruction.
-   `POST /api/assemble`: Assembles generated images into a PDF.

## Notes

- Grounding is optional; when enabled and supported by the SDK, a Sources slide is appended.
- Quality Gate and Style Consistency are optional checks and can be disabled via env vars.

## Project Structure

-   `main.py`: Entry point and API routes.
-   `logic/`: Core business logic.
    -   `director.py`: Slide planning (Gemini).
    -   `editor.py`: Slide editing (Gemini).
    -   `style_extractor.py`: Style extraction from text/files.
    -   `image_generator.py`: Visual generation (Imagen).
    -   `assembler.py`: PDF assembly.
    -   `quality_gate.py`: Text legibility and style consistency checks.
    -   `grounding.py`: Grounded research (optional).
    -   `vertex_wrapper.py`: Client wrapper with Mock switching.
    -   `mocks.py`: Mock implementation.
-   `static/`: Stores generated images and PDFs.
