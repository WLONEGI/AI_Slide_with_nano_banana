# Gemini 3.0 Pro Image (Nano Banana Pro): Text Rendering Guide

**Correction**: Previous advice based on "Imagen 3" limits (25 chars) has been superseded. "Gemini 3.0 Pro Image" uses a different, reasoning-enhanced architecture.

## Key Differences from Standard Models
| Feature | Standard (Imagen 3) | **Gemini 3.0 Pro Image** |
| :--- | :--- | :--- |
| **Engine** | Diffusion-based | **Reasoning-Enhanced (Gemini 3.0 + GemPix 2)** |
| **Text Capability** | Short phrases (<25 chars) | **Long text passages, complex scripts** |
| **Accuracy** | Good | **High (94% internal benchmark)** |
| **Multilingual** | Limited | **Native support (incl. Chinese/Japanese)** |

## Optimal Prompt Structure for Gemini 3.0
Leverage the model's **reasoning** capabilities. Instead of just keywords, explain *why* the text is there.

`[Context & Logic] -> [Subject + Integrated Text] -> [Style]`

### 1. The "Logic" Layer
The model plans the image before rendering. Explain the text's purpose.
*   *Example*: "A diagram explaining the water cycle. The text 'EVAPORATION' labels the rising steam..."

### 2. Integrated Text & Length
You are **NOT** limited to 25 characters. You can render full titles or short sentences.
*   *Example*: "A futuristic billboard displaying the full slogan: 'Empowering the Next Generation of AI'."

## Recommendation for Project
*   **Titles**: Can be longer and more descriptive.
*   **Labels**: You can safely use the model to label diagrams or charts.
*   **Japanese Text**: Native support is strong, so you can attempt to render Japanese keywords directly if the font style is specified (e.g., "Mincho style").
