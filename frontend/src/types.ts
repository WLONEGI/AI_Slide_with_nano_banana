export interface LayoutDef {
    layout_id: string;
    visual_description: string;
}

export interface StyleDef {
    global_prompt: string;
    layouts: LayoutDef[];
}

export interface Slide {
    slide_id: number;
    text_expected: boolean;
    layout_id: string;
    visual_prompt: string;
    content_text: string;
    tool?: string;      // "imagen" or "code_interpreter"
    reasoning?: string; // Refiner's reasoning
}

export interface SlidePlan {
    slides: Slide[];
    reasoning?: string;
    thinking_steps?: { phase: string, content: string }[];
    refinement_log?: string[];  // Refiner's thought log
}

