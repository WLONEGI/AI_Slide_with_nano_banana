# Gemini 3.0 Pro Image ("Nano Banana Pro") Prompt Guide

**Core Philosophy: Reasoning-Enhanced Generation**
Unlike previous models (Stable Diffusion, Imagen 2) that relied on "keyword soup", Gemini 3.0 Pro Image uses a large language model core to *reason* about the image before rendering. 
**Best Practice:** Do not just describe *what* to see. Explain *why* it looks that way and *how* the elements relate logically.

---

## 1. The Optimal Prompt Structure (The "Reasoning" Protocol)

The most effective structure mirrors how you would brief a human art director.

`[Role Definition] -> [Objective & Context] -> [The "Visual Logic"] -> [Subject Details] -> [Style & Atmosphere] -> [Technical Constraints]`

### Component Breakdown

| Section | Description | Example |
| :--- | :--- | :--- |
| **1. Role** | Activates specific expert knowledge. | "You are a specialized CGI artist for high-end fintech commercials." |
| **2. Objective** | Sets the intent. | "Create a slide background that metaphorically explains 'Database Sharding'." |
| **3. Visual Logic** | **CRITICAL for Gemini 3.0**. Explain the reasoning. | "The image must show a single massive data block being sliced into smaller, glowing shards to demonstrate efficiency. The shards should float in an organized grid to imply structure, not chaos." |
| **4. Subject** | Standard physical description. | "A central cube made of obsidian, cracking open to reveal blue light." |
| **5. Style** | Aesthetic direction. | "Isometric 3D, Glassmorphism, 8k resolution, ray-tracing." |
| **6. Constraints** | Integration & technicals. | "--ar 16:9, ensure the Right side is empty for text overlay, raw style." |

---

## 2. Text Rendering "Logic" (The Breakthrough)

Gemini 3.0 can render long text if you give it a **logical reason** to exist.

*   **Bad**: "Image with text 'Hello'."
*   **Good (Logical)**: "A futuristic airport departure board. One specific row is glitching and distinctly displays the destination 'HELLO WORLD' in yellow LED dots."

**Capabilities:**
*   **Length**: Can handle full sentences or slogans if integrated into signage, paper, or screens.
*   **Multilingual**: Native support for Japanese, Chinese, etc.
*   **Accuracy**: High (~94%).

---

## 3. Sample "Nano Banana" System Prompt

```markdown
# Role
You are the "Nano Banana" Visual Engine, a reasoning-based image generator.

# Thinking Process
Before generating, YOU MUST REASON:
1.  **Analyze the Abstract Concept**: What is the core metaphor? (e.g., Growth = Plant, Speed = Light)
2.  **Determine the Logic**: How do the visual elements interact physically? (e.g., "The light casts shadows because...")
3.  **Plan the Text**: If text is required, where does it logically exist in the scene? (On a screen? Etched in stone?)

# Prompt Construction Rule
Construct the direct image prompt using this format:

[Logic]: <Explain the cause-and-effect or metaphor>
[Scene]: <Physical description of subjects>
[Integration]: <How text/data is embedded in the world>
[Style]: <Artistic medium and lighting>
```

---

## 4. Comparison with Old Methods

| Feature | Old Method (Imagen 2 style) | **Nano Banana Pro Method** |
| :--- | :--- | :--- |
| **Structure** | Comma-separated descriptors | **Natural language with logic** |
| **Text** | "Text: 'Idea'" (Limit 25 chars) | **"A neon sign displaying the slogan..." (No explicit limit, logical integration)** |
| **Complexity** | Simple objects | **Complex cause-and-effect scenes** |
