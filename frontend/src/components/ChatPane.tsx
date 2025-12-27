import { useState, useEffect, useRef } from 'react';
import { SlidePlan, StyleDef, Slide } from '../types';
import { apiUrl } from '../lib/api';
import EnhancedInput from './EnhancedInput';
import LiveThinkingDisplay from './LiveThinkingDisplay';

// --- Typewriter Hook ---
function useTypewriter(text: string, speed = 10) {
    const [displayedText, setDisplayedText] = useState("");

    useEffect(() => {
        setDisplayedText("");
        let i = 0;
        const timer = setInterval(() => {
            if (i < text.length) {
                setDisplayedText((prev) => prev + text.charAt(i));
                i++;
            } else {
                clearInterval(timer);
            }
        }, speed);
        return () => clearInterval(timer);
    }, [text, speed]);

    return displayedText;
}

// --- Streaming Message Component ---
const StreamingMessage = ({ content }: { content: string }) => {
    const displayed = useTypewriter(content, 5); // Fast typing
    return <div className="whitespace-pre-wrap">{displayed}<span className="inline-block w-1.5 h-4 ml-0.5 bg-blue-500 animate-pulse align-middle"></span></div>;
};

interface ChatPaneProps {
    onPlanGenerated: (plan: SlidePlan, styleDef: StyleDef | null) => void;
    onSlideUpdated?: (slide: Slide) => void;
    selectedSlide: Slide | null;
    plan: SlidePlan | null;
    styleDef: StyleDef | null;
    initialMessage?: string;
}

export default function ChatPane({ onPlanGenerated, onSlideUpdated, selectedSlide, plan, styleDef, initialMessage }: ChatPaneProps) {
    const [messages, setMessages] = useState<{ role: string, content: string, isStreaming?: boolean }[]>([
        { role: 'ai', content: "Hello! checking in. How can I assist you with your presentation today?" }
    ]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [streamSessionId, setStreamSessionId] = useState<string | null>(null);  // For SSE streaming
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const hasStartedRef = useRef(false);

    // Auto-scroll
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Handle Initial Message
    useEffect(() => {
        if (initialMessage && !hasStartedRef.current) {
            hasStartedRef.current = true;
            setTimeout(() => {
                handleSubmission(initialMessage);
            }, 500);
        }
    }, [initialMessage]);

    // Handle Slide Selection Context
    /* 
       Note: We removed the auto-population of input on slide select 
       to respect the "Zero-state" / "Editor feel" requested.
       We can add a subtle indicator instead if needed.
    */

    const handleSubmission = async (text: string, file?: File | null) => {
        if (!text && !file) return;
        setLoading(true);
        setError(null);

        // Add User Message
        const userMsgContent = text + (file ? ` [Attached: ${file.name}]` : "");
        setMessages(prev => [...prev, { role: 'user', content: userMsgContent }]);

        await processBackendCall(text, file);
    };

    const processBackendCall = async (text: string, file?: File | null) => {
        let nextStyleDef: StyleDef | null = null;
        try {
            const isEdit = !!plan && !file; // Edit mode if we have a plan and NO file (assuming file implies new start)

            if (isEdit) {
                // Edit Logic
                setMessages(prev => [...prev, { role: 'ai', content: "Reading your request...", isStreaming: true }]);

                const editRes = await fetch(apiUrl("/api/edit-slide"), {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        instruction: text,
                        slide: selectedSlide ?? null,
                        plan: selectedSlide ? null : plan,
                        style_def: styleDef
                    })
                });

                if (!editRes.ok) throw new Error("Failed to edit slide.");
                const updatedSlide: Slide = await editRes.json();
                onSlideUpdated?.(updatedSlide);

                // Replace "Reading..." with success
                setMessages(prev => {
                    const newMsgs = [...prev];
                    newMsgs.pop(); // Remove streaming msg
                    return [...newMsgs, { role: 'ai', content: `Updated Slide ${updatedSlide.slide_id}.` }];
                });

            } else {
                // Generate Logic
                // 1. Style
                setMessages(prev => [...prev, { role: 'ai', content: "Analyzing requirements...", isStreaming: true }]);

                const formData = new FormData();
                formData.append("description", text);
                if (file) formData.append("file", file);

                const styleRes = await fetch(apiUrl("/api/style"), { method: "POST", body: formData });
                if (!styleRes.ok) throw new Error("Style analysis failed.");

                nextStyleDef = await styleRes.json();

                // Update streaming message
                setMessages(prev => {
                    const newMsgs = [...prev];
                    newMsgs.pop();
                    // Use special role for LiveThinkingDisplay
                    return [...newMsgs, { role: 'ai-streaming-thinking', content: "Thinking..." }];
                });

                // Generate session ID for SSE streaming
                const sessionId = `plan_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
                setStreamSessionId(sessionId);

                // 2. Plan - include session_id for SSE streaming
                const res = await fetch(apiUrl(`/api/plan?session_id=${sessionId}`), {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ text, style_def: nextStyleDef })
                });

                if (!res.ok) throw new Error("Plan generation failed.");
                const data: SlidePlan = await res.json();
                onPlanGenerated(data, nextStyleDef);

                // Finalize messages
                setMessages(prev => {
                    const newMsgs = [...prev];
                    // Remove the streaming thinking component
                    if (newMsgs[newMsgs.length - 1].role === 'ai-streaming-thinking') {
                        newMsgs.pop();
                    }

                    const finalMsgs = [...newMsgs];

                    // Add Refiner's Log (Emotional Loading - real backend thoughts)
                    if (data.refinement_log && data.refinement_log.length > 0) {
                        finalMsgs.push({ role: 'ai-refiner', content: JSON.stringify(data.refinement_log) });
                    }

                    // Add Thinking (Non-streaming for now as it's complex JSON)
                    if (data.thinking_steps && data.thinking_steps.length > 0) {
                        finalMsgs.push({ role: 'ai-thinking', content: JSON.stringify(data.thinking_steps) });
                    } else if (data.reasoning) {
                        finalMsgs.push({ role: 'ai-thinking', content: data.reasoning });
                    }

                    finalMsgs.push({ role: 'ai', content: `Created a plan with ${data.slides.length} slides. Check the preview!` });
                    return finalMsgs;
                });

                // Clear session ID after plan completes
                setStreamSessionId(null);
            }

        } catch (e: any) {
            console.error(e);
            setError(e.message || "Error occurred.");
            setMessages(prev => {
                const newMsgs = [...prev];
                // Remove thinking component if error
                if (newMsgs[newMsgs.length - 1].role === 'ai-streaming-thinking' || newMsgs[newMsgs.length - 1].isStreaming) {
                    newMsgs.pop();
                }
                return [...newMsgs, { role: 'ai', content: "Sorry, I encountered an error. Please try again." }];
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full bg-white relative">
            {/* Error Alert */}
            {error && (
                <div className="mx-4 mt-2 bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm relative">
                    <span className="font-bold">Error:</span> {error}
                    <button onClick={() => setError(null)} className="absolute right-2 top-2 p-1">✕</button>
                </div>
            )}

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar pb-40">
                {messages.map((msg, i) => (
                    <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} animate-fade-in-up`}>
                        {/* Avatar/Icon for AI */}
                        {msg.role !== 'user' && msg.role !== 'ai-thinking' && msg.role !== 'ai-refiner' && (
                            <div className="mb-1 ml-1 text-xs font-bold text-gray-400">AI Partner</div>
                        )}

                        <div className={`max-w-[85%] text-[15px] leading-relaxed shadow-sm ${msg.role === 'user'
                            ? 'bg-[#1D1D1F] text-white rounded-[20px] rounded-br-[4px] px-5 py-3'
                            : msg.role === 'ai-thinking'
                                ? 'bg-white border border-gray-100 text-gray-500 text-xs font-mono rounded-xl p-3 w-full'
                                : msg.role === 'ai-refiner'
                                    ? 'bg-gradient-to-br from-purple-50 to-blue-50 border border-purple-100 text-gray-600 text-xs font-mono rounded-xl p-3 w-full'
                                    : msg.role === 'ai-streaming-thinking'
                                        ? 'w-full max-w-lg' // Special container for the thinking display
                                        : 'bg-[#F2F4F7] text-[#1D1D1F] rounded-[20px] rounded-bl-[4px] px-5 py-3'
                            }`}>

                            {/* Content Rendering */}
                            {msg.role === 'ai-refiner' ? (
                                <RefinerLogRenderer content={msg.content} />
                            ) : msg.role === 'ai-thinking' ? (
                                <ThinkingProcessRenderer content={msg.content} />
                            ) : msg.role === 'ai-streaming-thinking' ? (
                                <LiveThinkingDisplay sessionId={streamSessionId || undefined} />
                            ) : msg.isStreaming ? (
                                <StreamingMessage content={msg.content} />
                            ) : (
                                <div className="whitespace-pre-wrap">{msg.content}</div>
                            )}

                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Enhanced Input Area */}
            <div className="absolute bottom-6 left-0 right-0 px-4 z-20">
                <EnhancedInput
                    onSubmit={handleSubmission}
                    disabled={loading}
                    placeholder={loading ? "AI is thinking..." : "Message AI Partner..."}
                />
                <div className="text-center mt-2">
                    <p className="text-[10px] text-gray-400">AI can make mistakes. Design generated by Gemini 2.0 Flash.</p>
                </div>
            </div>
        </div>
    );
}

// Helper to render Thinking Process (Extracted for cleanliness)
function ThinkingProcessRenderer({ content }: { content: string }) {
    let steps = [];
    try {
        const parsed = JSON.parse(content);
        if (Array.isArray(parsed)) steps = parsed;
        else steps = [{ phase: "Thinking Process", content: content }];
    } catch {
        steps = [{ phase: "Thinking Process", content: content }];
    }

    return (
        <div className="space-y-2 w-full">
            {steps.map((step: any, idx: number) => (
                <details key={idx} className="group">
                    <summary className="list-none cursor-pointer flex items-center space-x-2 font-bold mb-1 text-purple-500 uppercase tracking-widest text-[10px] hover:text-purple-700 transition-colors select-none">
                        <span className="flex items-center gap-1">
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                            {step.phase}
                        </span>
                        <svg className="w-3 h-3 transform group-open:rotate-180 transition-transform text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                    </summary>
                    <div className="whitespace-pre-wrap text-[11px] leading-relaxed pl-2 border-l-2 border-purple-100 mt-2 text-gray-600 animate-fade-in">
                        {step.content}
                    </div>
                </details>
            ))}
        </div>
    );
}

// Helper to render Refiner Log (Emotional Loading)
function RefinerLogRenderer({ content }: { content: string }) {
    let logs: string[] = [];
    try {
        const parsed = JSON.parse(content);
        if (Array.isArray(parsed)) logs = parsed;
        else logs = [content];
    } catch {
        logs = [content];
    }

    return (
        <details className="group w-full" open>
            <summary className="list-none cursor-pointer flex items-center space-x-2 font-bold mb-2 text-blue-600 uppercase tracking-widest text-[10px] hover:text-blue-700 transition-colors select-none">
                <span className="flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                    REFINER INSIGHTS
                </span>
                <svg className="w-3 h-3 transform group-open:rotate-180 transition-transform text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
            </summary>
            <div className="space-y-1 pl-2 border-l-2 border-blue-200 mt-2">
                {logs.map((log, idx) => (
                    <div key={idx} className="text-[11px] leading-relaxed text-gray-600 animate-fade-in flex items-start gap-2">
                        <span className="text-blue-400 mt-0.5">▸</span>
                        <span>{log}</span>
                    </div>
                ))}
            </div>
        </details>
    );
}
