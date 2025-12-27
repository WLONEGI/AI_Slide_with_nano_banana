"use client";
import React from 'react';
import { Slide, SlidePlan, StyleDef } from '../types';
import { usePreviewPaneLogic } from '../hooks/usePreviewPaneLogic';
import { SlideView } from './SlideView';

// --- Main Component: PreviewPane ---
interface PreviewPaneProps {
    plan: SlidePlan | null;
    styleDef: StyleDef | null;
    onSlideSelect: (slide: Slide) => void;
    regenerateSignal: { slideId: number; nonce: number } | null;
}

export default function PreviewPane({ plan, styleDef, onSlideSelect, regenerateSignal }: PreviewPaneProps) {
    const {
        downloading,
        activeTab,
        setActiveTab,
        isEditMode,
        setIsEditMode,
        handleDownloadPDF
    } = usePreviewPaneLogic(plan);

    if (!plan) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center min-h-[400px] text-gray-400 space-y-4">
                <div className="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center">
                    <svg className="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                </div>
                <p className="text-sm font-medium">Your slides will appear here</p>
            </div>
        );
    }

    return (
        <div className="space-y-12 pb-20 relative">
            {/* Global Toolbar (Sticky) */}
            <div className="sticky top-0 z-40 bg-[#F5F5F7]/95 backdrop-blur py-4 flex justify-between items-center px-2">
                <div className="text-sm font-bold text-gray-400 uppercase tracking-widest">{plan.slides.length} Slides</div>

                <div className="flex items-center space-x-2 bg-white rounded-full p-1 shadow-sm border border-gray-200">
                    <button
                        onClick={() => setIsEditMode(false)}
                        className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${!isEditMode ? 'bg-[#1D1D1F] text-white shadow-md' : 'text-gray-500 hover:bg-gray-100'}`}
                    >
                        View
                    </button>
                    <button
                        onClick={() => setIsEditMode(true)}
                        className={`px-4 py-1.5 rounded-full text-xs font-bold flex items-center gap-2 transition-all ${isEditMode ? 'bg-blue-600 text-white shadow-md' : 'text-gray-500 hover:bg-gray-100'}`}
                    >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                        Precision Edit
                    </button>
                </div>
            </div>

            {/* Slides List */}
            <div className="flex flex-col items-center space-y-16 pt-4">
                {plan.slides.map((slide, idx) => {
                    const tab = activeTab[slide.slide_id] || 'preview';
                    return (
                        <div key={slide.slide_id} className="w-full relative group">
                            {/* Slide Card */}
                            <div className="bg-white rounded-xl shadow-[0_4px_25px_rgba(0,0,0,0.04)] overflow-hidden border border-gray-100 transition-all hover:shadow-[0_12px_40px_rgba(0,0,0,0.06)]">
                                {/* Slide Toolbar */}
                                <div className="h-10 px-4 flex items-center justify-between border-b border-gray-50 bg-[#FAFAFB]">
                                    <div className="flex items-center space-x-6 h-full">
                                        <button
                                            onClick={() => setActiveTab(prev => ({ ...prev, [slide.slide_id]: 'preview' }))}
                                            className={`h-full text-[11px] font-extrabold border-b-2 transition-all uppercase tracking-tight ${tab === 'preview' ? 'border-[#1D1D1F] text-[#1D1D1F]' : 'border-transparent text-gray-400 hover:text-gray-600'}`}
                                        >
                                            Preview
                                        </button>
                                        <button
                                            onClick={() => setActiveTab(prev => ({ ...prev, [slide.slide_id]: 'prompt' }))}
                                            className={`h-full text-[11px] font-extrabold border-b-2 transition-all uppercase tracking-tight ${tab === 'prompt' ? 'border-[#1D1D1F] text-[#1D1D1F]' : 'border-transparent text-gray-400 hover:text-gray-600'}`}
                                        >
                                            Prompt
                                        </button>
                                    </div>
                                    {isEditMode && tab === 'preview' && (
                                        <span className="text-[10px] text-blue-600 font-bold bg-blue-50 px-2 py-0.5 rounded animate-pulse">
                                            Select area to edit
                                        </span>
                                    )}
                                </div>

                                {/* Slide Content Area */}
                                <div className="aspect-[16/9] bg-[#F5F5F7] flex items-center justify-center relative group/content" onClick={() => onSlideSelect(slide)}>
                                    {/* Preview Tab (Always mounted, hidden via CSS) */}
                                    <div className={`w-full h-full ${tab === 'preview' ? 'block' : 'hidden'}`}>
                                        <SlideView
                                            slide={slide}
                                            styleDef={styleDef}
                                            regenerateSignal={regenerateSignal?.slideId === slide.slide_id ? regenerateSignal : null}
                                            isEditMode={isEditMode}
                                        />
                                    </div>

                                    {/* Prompt Tab */}
                                    <div className={`w-full h-full p-8 font-mono text-[11px] text-[#424245] bg-white overflow-y-auto leading-relaxed ${tab === 'prompt' ? 'block' : 'hidden'}`}>
                                        <div className="mb-2 font-bold text-xs uppercase tracking-wider text-gray-400">Image Generation Prompt</div>
                                        <p className="whitespace-pre-wrap">{slide.visual_prompt}</p>
                                    </div>

                                    {/* Border highlight for structure */}
                                    <div className="absolute inset-0 border-4 border-transparent hover:border-[#0071E3]/20 transition-all pointer-events-none rounded-b-xl z-0" />
                                </div>
                            </div>

                            {/* Visual index indicator on left */}
                            <div className="absolute -left-14 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-all duration-300">
                                <div className="w-10 h-10 rounded-full bg-white border border-gray-200 flex items-center justify-center text-xs font-extrabold text-[#86868B] shadow-sm">
                                    {idx + 1}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Global Actions */}
            <div className="flex justify-center pt-8">
                <button
                    data-testid="download-pdf"
                    onClick={handleDownloadPDF}
                    disabled={downloading}
                    className="flex items-center space-x-2 px-8 py-3 bg-[#1D1D1F] text-white rounded-full font-bold text-sm shadow-xl hover:bg-black transition-all disabled:opacity-50"
                >
                    {downloading ? (
                        <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            <span>Assembling PDF...</span>
                        </>
                    ) : (
                        <>
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                            <span>Download Full PDF</span>
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}
