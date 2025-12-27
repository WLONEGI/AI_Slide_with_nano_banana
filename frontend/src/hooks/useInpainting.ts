import { useState, useRef } from 'react';
import { Slide, StyleDef } from '../types';
import { apiUrl } from '../lib/api';

export function useInpainting(
    slide: Slide,
    styleDef: StyleDef | null,
    imageUrl: string | null,
    setImageUrl: (url: string | null) => void,
    imageRef: React.RefObject<HTMLImageElement | null>,
    containerRef: React.RefObject<HTMLDivElement | null>,
    isEditMode: boolean
) {
    const [isSelecting, setIsSelecting] = useState(false);
    const [selection, setSelection] = useState<{ x: number, y: number, w: number, h: number } | null>(null);
    const [startPos, setStartPos] = useState<{ x: number, y: number } | null>(null);
    const [showInstruction, setShowInstruction] = useState(false);
    const [instruction, setInstruction] = useState("");
    const [isRefining, setIsRefining] = useState(false);

    // --- Internal Helper ---
    const getCoords = (e: React.MouseEvent) => {
        if (!containerRef.current) return { x: 0, y: 0 };
        const rect = containerRef.current.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    };

    const handleMouseDown = (e: React.MouseEvent) => {
        if (!isEditMode || !imageUrl || isRefining) return;
        setIsSelecting(true);
        setSelection(null);
        setShowInstruction(false);
        setStartPos(getCoords(e));
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!isSelecting || !startPos) return;
        const current = getCoords(e);
        const w = current.x - startPos.x;
        const h = current.y - startPos.y;

        setSelection({
            x: w > 0 ? startPos.x : current.x,
            y: h > 0 ? startPos.y : current.y,
            w: Math.abs(w),
            h: Math.abs(h)
        });
    };

    const handleMouseUp = () => {
        if (!isSelecting) return;
        setIsSelecting(false);
        if (selection && selection.w > 10 && selection.h > 10) {
            setShowInstruction(true);
        } else {
            setSelection(null);
        }
    };

    const handleInpaint = async () => {
        if (!selection || !imageRef.current || !imageUrl) return;
        setIsRefining(true);
        try {
            // 1. Create Mask
            const naturalWidth = imageRef.current.naturalWidth;
            const naturalHeight = imageRef.current.naturalHeight;
            const displayWidth = imageRef.current.clientWidth;
            const displayHeight = imageRef.current.clientHeight;

            const scaleX = naturalWidth / displayWidth;
            const scaleY = naturalHeight / displayHeight;

            const canvas = document.createElement('canvas');
            canvas.width = naturalWidth;
            canvas.height = naturalHeight;
            const ctx = canvas.getContext('2d');
            if (!ctx) throw new Error("No context");

            // Fill black (keep)
            ctx.fillStyle = "black";
            ctx.fillRect(0, 0, naturalWidth, naturalHeight);

            // Fill white (inpaint area)
            ctx.fillStyle = "white";
            ctx.fillRect(
                selection.x * scaleX,
                selection.y * scaleY,
                selection.w * scaleX,
                selection.h * scaleY
            );

            const maskBase64 = canvas.toDataURL('image/png');

            // 2. Extract filename
            // URL: http://.../static/images/UUID.png?t=...
            const urlObj = new URL(imageUrl);
            // path /static/images/UUID.png
            const filename = urlObj.pathname.split('/').pop() || "";

            // 3. Call API
            const res = await fetch(apiUrl("/api/inpaint-slide"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    slide_id: slide.slide_id,
                    image_filename: filename,
                    mask_base64: maskBase64,
                    instruction: instruction,
                    style_def: styleDef
                })
            });
            if (!res.ok) throw new Error("Inpaint failed");
            const data = await res.json();

            // Update Image
            setImageUrl(`${data.url}?t=${Date.now()}`);
            setSelection(null);
            setShowInstruction(false);
            setInstruction("");

        } catch (e) {
            console.error(e);
            alert("Inpaint failed. See console.");
        } finally {
            setIsRefining(false);
        }
    };

    const cancelSelection = () => {
        setSelection(null);
        setShowInstruction(false);
    };

    return {
        selection,
        isSelecting,
        showInstruction,
        instruction,
        setInstruction,
        isRefining,
        handleMouseDown,
        handleMouseMove,
        handleMouseUp,
        handleInpaint,
        cancelSelection,
        setSelection,
        setShowInstruction
    };
}
