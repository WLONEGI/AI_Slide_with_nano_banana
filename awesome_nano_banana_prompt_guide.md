# Awesome Nano Banana Pro: The Definitive Prompt Structure
*Based on the YouMind-OpenLab/awesome-nano-banana-pro-prompts methodology*

After analyzing the "Awesome" repository theories, we have derived the **Optimal 5-Part Scaffold**.
This structure abandons the "Tag Soup" approach (e.g., `blue, city, futuristic`) in favor of **Structured Natural Language**.

## The 5-Part Scaffold

To generate the highest quality slides, the System Prompt must force the Agent to output prompts in this exact JSON-friendly or string format:

### 1. Task (The "Directive")
**What is the specific goal?**
*   *Old Way*: "A slide background."
*   *Awesome Way*: "Generate a high-contrast presentation background optimized for white text overlay. The image must function as a metaphorical backdrop for 'Market Volatility'."

### 2. Context (The "Story")
**Why does this image exist?**
*   *Awesome Way*: "This slide is for a Series B investor pitch deck. The audience is conservative but tech-savvy. The tone should be 'Trustworthy' yet 'Innovative'."

### 3. Visual Instructions (The "Scene")
**Detailed, physically consistent description.**
*   *Crucial Change*: Use **"Layout-First"** descriptions.
*   *Awesome Way*: "Composition splits the frame: The left 1/3 features a photorealistic glass hourglass with upward-flowing golden sand (symbolizing defying time). The right 2/3 is a deep, blurred charcoal gradient specifically reserved for copy."

### 4. Style Parameters (The "Vibe")
**Specific artistic constraints.**
*   *Awesome Way*: "Art Direction: Apple Keynote style mixed with 'Blade Runner 2049' cinematography. Lighting: Volumetric soft-box lighting. Color Palette: Slate Grey (#333) and Neon Amber."

### 5. Technical Specifications (The "Rules")
**Hard constraints for the model.**
*   *Awesome Way*: "--ar 16:9, NO text rendering (unless specified), NO cluttered details, 8k resolution, raw render."

---

## Applied Example: Visualizer Prompt v3

The Visualizer should output a prompt string that looks like this:

```text
[Task]: Create a Title Slide background for an AI Ethics seminar.
[Context]: Professional, academic tone. Needs to look expensive and thought-provoking.
[Visual]: A central marble statue of a human head, half-submerged in a pool of liquid digital chrome. The liquid ripples outward.
[Layout]: Center-weighted composition. The top 20% is negative space for the title.
[Style]: Classical Sculpture meets Cyberpunk. High-key lighting, white marble, silver chrome.
[Tech]: --ar 16:9, sharp focus, 8k.
```

## Why this is better?
1.  **Layout Awareness**: Explicitly reserving space (e.g., "Right 2/3") prevents the "bisy" slide problem.
2.  **Context**: Telling the AI "Investor Pitch" vs "Kindergarten Lesson" completely changes the output aesthetic automatically.
3.  **Natural Language**: Gemini 3.0 follows instruction-following better than token-matching.
