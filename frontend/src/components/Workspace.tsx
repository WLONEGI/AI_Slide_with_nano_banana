"use client";
import { useState, useCallback, useEffect, useRef } from 'react';
import ChatPane from './ChatPane';
import PreviewPane from './PreviewPane';
import { SlidePlan, StyleDef, Slide } from '../types';

interface WorkspaceProps {
    initialMessage?: string;
}

import Sidebar from './Sidebar';

export default function Workspace({ initialMessage }: WorkspaceProps) {
    const [plan, setPlan] = useState<SlidePlan | null>(null);
    const [styleDef, setStyleDef] = useState<StyleDef | null>(null);
    const [selectedSlide, setSelectedSlide] = useState<Slide | null>(null);
    const [regenerateSignal, setRegenerateSignal] = useState<{ slideId: number; nonce: number } | null>(null);
    const [isSidebarOpen, setSidebarOpen] = useState(true); // Sidebar state

    // Resizing logic
    const [chatWidth, setChatWidth] = useState(400); // Default width
    const [isResizing, setIsResizing] = useState(false);
    const mainRef = useRef<HTMLDivElement>(null);

    const startResizing = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        setIsResizing(true);
    }, []);

    const stopResizing = useCallback(() => {
        setIsResizing(false);
    }, []);

    const resize = useCallback((e: MouseEvent) => {
        if (isResizing) {
            // Limit width between 250px and 800px or 50% of screen
            const newWidth = Math.max(250, Math.min(e.clientX, 800));
            setChatWidth(newWidth);
        }
    }, [isResizing]);

    useEffect(() => {
        if (isResizing) {
            window.addEventListener('mousemove', resize);
            window.addEventListener('mouseup', stopResizing);
        } else {
            window.removeEventListener('mousemove', resize);
            window.removeEventListener('mouseup', stopResizing);
        }
        return () => {
            window.removeEventListener('mousemove', resize);
            window.removeEventListener('mouseup', stopResizing);
        };
    }, [isResizing, resize, stopResizing]);

    // Memoized callbacks for ChatPane
    const handleNewChat = useCallback(() => {
        window.location.reload();
    }, []);

    const handlePlanGenerated = useCallback((nextPlan: SlidePlan, nextStyleDef: StyleDef | null) => {
        setPlan(nextPlan);
        setStyleDef(nextStyleDef);
        setSelectedSlide(null);
        setRegenerateSignal(null);
    }, []);

    const handleSlideUpdated = useCallback((updatedSlide: Slide) => {
        setPlan(prev => {
            if (!prev) return prev;
            return {
                ...prev,
                slides: prev.slides.map(slide =>
                    slide.slide_id === updatedSlide.slide_id ? updatedSlide : slide
                ),
            };
        });
        setSelectedSlide(updatedSlide);
        setRegenerateSignal({ slideId: updatedSlide.slide_id, nonce: Date.now() });
    }, []);

    return (
        <div className={`flex flex-col h-screen w-screen overflow-hidden bg-[#F5F5F7] text-[#1D1D1F] font-sans ${isResizing ? 'cursor-col-resize select-none' : ''}`}>
            {/* Persistent Header */}
            <header className="h-14 flex items-center justify-between px-4 bg-white border-b border-gray-200 z-30 shrink-0 shadow-sm relative">
                <div className="flex items-center space-x-3">
                    {/* Sidebar Toggle */}
                    <button onClick={() => setSidebarOpen(!isSidebarOpen)} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500 transition-colors">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
                    </button>

                    <div className="w-px h-6 bg-gray-200 mx-2"></div>

                    <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center text-white font-bold text-xs">AI</div>
                    <div className="flex items-center space-x-2">
                        <h1 className="text-sm font-semibold truncate text-gray-700">
                            {plan?.slides[0]?.content_text.split('\n')[0] || "Untitled Presentation"}
                        </h1>
                    </div>
                </div>
                <div className="flex items-center space-x-2 text-sm text-gray-500">
                    <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold">Beta</span>
                </div>
            </header>

            {/* Main Workspace */}
            <div className="flex flex-1 overflow-hidden" ref={mainRef}>

                {/* Sidebar (Left) */}
                <Sidebar
                    isOpen={isSidebarOpen}
                    onToggle={() => setSidebarOpen(!isSidebarOpen)}
                    onNewChat={handleNewChat}
                />

                {/* Chat Pane Frame */}
                <aside
                    className="flex-shrink-0 bg-white flex flex-col border-r border-gray-200 z-10"
                    style={{ width: `${chatWidth}px` }}
                >
                    <ChatPane
                        initialMessage={initialMessage}
                        onPlanGenerated={handlePlanGenerated}
                        onSlideUpdated={handleSlideUpdated}
                        selectedSlide={selectedSlide}
                        plan={plan}
                        styleDef={styleDef}
                    />
                </aside>

                {/* Resizable Divider - Invisible but accessible */}
                <div
                    onMouseDown={startResizing}
                    className={`w-[4px] -ml-[2px] cursor-col-resize z-50 flex-shrink-0 hover:bg-blue-400 opacity-0 hover:opacity-100 transition-opacity ${isResizing ? 'bg-blue-500 opacity-100' : ''}`}
                />

                {/* Preview Canvas Frame (Artifacts View) */}
                <main className="flex-1 overflow-hidden bg-[#F5F5F7] relative flex flex-col">
                    {/* Artifacts Header */}
                    <div className="h-10 bg-gray-50 border-b border-gray-200 flex items-center px-4 justify-between shrink-0 text-xs text-gray-500 uppercase tracking-widest font-semibold">
                        <span>Preview / Artifacts</span>
                        <div className="flex space-x-2">
                            <button className="hover:text-gray-900 transition-colors">Code</button>
                            <button className="text-blue-600 font-bold border-b-2 border-blue-600">Preview</button>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
                        <div className="max-w-[1000px] mx-auto min-h-full">
                            <PreviewPane
                                plan={plan}
                                styleDef={styleDef}
                                onSlideSelect={setSelectedSlide}
                                regenerateSignal={regenerateSignal}
                            />
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}
