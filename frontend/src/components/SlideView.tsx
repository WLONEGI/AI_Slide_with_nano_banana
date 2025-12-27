"use client";
import React, { useRef } from 'react';
import Image from 'next/image';
import { Slide, StyleDef } from '../types';
import { getSkeletonForLayout } from './skeletons/LayoutSkeletons';
import { useSlideGeneration } from '../hooks/useSlideGeneration';
import { useInpainting } from '../hooks/useInpainting';

export interface SlideViewProps {
    slide: Slide;
    styleDef: StyleDef | null;
    regenerateSignal: { slideId: number; nonce: number } | null;
    isEditMode: boolean;
}

export function SlideView({ slide, styleDef, regenerateSignal, isEditMode }: SlideViewProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const imageRef = useRef<HTMLImageElement | null>(null);

    const {
        imageUrl,
        setImageUrl,
        isGenerating
    } = useSlideGeneration(slide, styleDef, regenerateSignal);

    const {
        selection,
        isSelecting, // used in logic, but verify if needed in JSX ? No specific usage in JSX except derived state logic inside hook
        showInstruction,
        instruction,
        setInstruction,
        isRefining,
        handleMouseDown,
        handleMouseMove,
        handleMouseUp,
        handleInpaint,
        setSelection,
        setShowInstruction
    } = useInpainting(
        slide,
        styleDef,
        imageUrl,
        setImageUrl,
        imageRef,
        containerRef,
        isEditMode
    );

    const status = imageUrl ? 'ready' : isGenerating ? 'generating' : 'idle';

    return (
        <div
            ref={containerRef}
            data-testid={`slide-status-${slide.slide_id}`}
            className={`w-full h-full flex flex-col items-center justify-center bg-white relative select-none ${isEditMode && imageUrl ? 'cursor-crosshair' : ''}`}
            data-status={status}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
        >
            {imageUrl ? (
                <>
                    <Image
                        ref={(el) => { imageRef.current = el; }}
                        data-testid={`slide-image-${slide.slide_id}`}
                        src={imageUrl}
                        fill
                        className="object-cover animate-fade-in pointer-events-none"
                        alt={`Slide ${slide.slide_id}`}
                        unoptimized
                    />

                    {/* Selection Box */}
                    {selection && (
                        <div
                            className="absolute border-2 border-white/80 shadow-[0_0_0_9999px_rgba(0,0,0,0.5)] z-10"
                            style={{
                                left: selection.x,
                                top: selection.y,
                                width: selection.w,
                                height: selection.h,
                                boxShadow: '0 0 0 9999px rgba(0,0,0,0.5)' // Dim outside
                            }}
                        />
                    )}

                    {/* Instruction Popover */}
                    {showInstruction && selection && (
                        <div
                            className="absolute z-20 bg-white rounded-xl shadow-2xl p-4 w-72 border border-gray-100 animate-in fade-in zoom-in duration-200"
                            style={{
                                top: Math.min(selection.y + selection.h + 10, containerRef.current?.clientHeight ? containerRef.current.clientHeight - 150 : 0),
                                left: Math.min(selection.x, containerRef.current?.clientWidth ? containerRef.current.clientWidth - 300 : 0)
                            }}
                            onMouseDown={(e) => e.stopPropagation()} // Prevent creating new selection / drag
                        >
                            <h4 className="text-xs font-bold uppercase text-gray-400 mb-2">Precision Edit</h4>
                            <textarea
                                className="w-full text-sm p-2 border border-gray-200 rounded-lg mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800"
                                rows={2}
                                placeholder="E.g., Change text to 'Growth'"
                                value={instruction}
                                onChange={(e) => setInstruction(e.target.value)}
                                autoFocus
                            />
                            <div className="flex justify-end space-x-2">
                                <button
                                    onClick={() => { setSelection(null); setShowInstruction(false); }}
                                    className="px-3 py-1.5 text-xs font-bold text-gray-500 hover:bg-gray-100 rounded-lg"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleInpaint}
                                    disabled={!instruction.trim() || isRefining}
                                    className="px-3 py-1.5 text-xs font-bold bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                                >
                                    {isRefining ? 'Refining...' : 'Apply Fix'}
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Refining overlay */}
                    {isRefining && (
                        <div className="absolute inset-x-0 bottom-4 flex justify-center z-20">
                            <div className="bg-black/80 text-white text-xs px-4 py-2 rounded-full backdrop-blur-md flex items-center space-x-2 shadow-lg">
                                <div className="animate-spin h-3 w-3 border-2 border-white border-t-transparent rounded-full" />
                                <span>Refining Selection...</span>
                            </div>
                        </div>
                    )}
                </>
            ) : (
                // Semantic Skeleton instead of Spinner
                <div className="w-full h-full relative group/skeleton">
                    {getSkeletonForLayout(slide.layout_id, slide.content_text)}

                    {/* Progressive Painting Status */}
                    {isGenerating && (
                        <div className="absolute inset-x-0 bottom-0 p-4 bg-gradient-to-t from-white via-white/90 to-transparent">
                            <div className="flex items-center space-x-3 bg-white/80 backdrop-blur rounded-full px-4 py-2 shadow-sm border border-gray-100 w-fit max-w-[90%] mx-auto">
                                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-500 shrink-0"></div>
                                <div className="flex flex-col">
                                    <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">Painting...</span>
                                    <span className="text-xs text-gray-600 font-medium truncate max-w-[300px]">{slide.visual_prompt}</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
