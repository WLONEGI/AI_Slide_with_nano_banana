import { useState, useEffect, useCallback } from 'react';
import { Slide, StyleDef } from '../types';
import { apiUrl } from '../lib/api';

export function useSlideGeneration(
    slide: Slide,
    styleDef: StyleDef | null,
    regenerateSignal: { slideId: number; nonce: number } | null
) {
    const [imageUrl, setImageUrl] = useState<string | null>(null);
    const [isGenerating, setIsGenerating] = useState(false);

    // Reset state on slide change
    useEffect(() => {
        setIsGenerating(false);
        setImageUrl(null);
    }, [slide.slide_id]);

    const generateImage = useCallback(async () => {
        if (imageUrl) return;
        setIsGenerating(true);
        try {
            const res = await fetch(apiUrl("/api/generate-slide"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ slide: slide, style_def: styleDef })
            });
            if (!res.ok) throw new Error("Generation failed");
            const data = await res.json();
            setImageUrl(`${data.url}?t=${Date.now()}`);
        } catch (e) {
            console.error(e);
            setImageUrl(null);
        } finally {
            setIsGenerating(false);
        }
    }, [slide, styleDef, imageUrl]);

    useEffect(() => {
        if (!imageUrl && !isGenerating) {
            generateImage();
        }
    }, [imageUrl, isGenerating, generateImage]);

    useEffect(() => {
        if (regenerateSignal && regenerateSignal.slideId === slide.slide_id) {
            setImageUrl(null);
        }
    }, [regenerateSignal, slide.slide_id]);

    return {
        imageUrl,
        setImageUrl,
        isGenerating,
        generateImage
    };
}
