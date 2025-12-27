import { useState, useEffect, useRef } from 'react';
import { apiUrl } from '../lib/api';

// Configuration for the phases (fallback simulation)
const PHASES = [
    { id: 'analysis', label: 'ANALYSIS', color: 'text-blue-500', bg: 'bg-blue-500' },
    { id: 'planning', label: 'PLANNING', color: 'text-purple-500', bg: 'bg-purple-500' },
    { id: 'refinement', label: 'REFINEMENT', color: 'text-emerald-500', bg: 'bg-emerald-500' },
];

const FALLBACK_LOGS = {
    analysis: [
        "Parsing user intent...",
        "Identifying key themes...",
        "Analyzing semantic structure...",
    ],
    planning: [
        "Structuring narrative flow...",
        "Drafting slide outline...",
        "Selecting optimal layouts...",
    ],
    refinement: [
        "Polishing language tones...",
        "Optimizing visual prompts...",
        "Finalizing slide composition...",
    ]
};

interface Props {
    sessionId?: string;  // If provided, stream from backend
}

export default function LiveThinkingDisplay({ sessionId }: Props) {
    const [phaseIndex, setPhaseIndex] = useState(0);
    const [logs, setLogs] = useState<string[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    const currentPhase = PHASES[phaseIndex];

    // SSE Streaming if sessionId is provided
    useEffect(() => {
        if (!sessionId) return;

        setIsStreaming(true);
        const eventSource = new EventSource(apiUrl(`/api/plan/stream/${sessionId}`));

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const timestamp = new Date().toISOString().split('T')[1].slice(0, 8);

                if (data.type === 'log') {
                    setLogs(prev => [...prev, `[${timestamp}] ${data.content}`].slice(-8));

                    // Update phase based on content
                    if (data.content.includes('Director')) {
                        setPhaseIndex(1); // planning
                    } else if (data.content.includes('Refiner')) {
                        setPhaseIndex(2); // refinement
                    }
                } else if (data.type === 'done' || data.type === 'timeout') {
                    eventSource.close();
                    setIsStreaming(false);
                }
            } catch (e) {
                console.error('SSE parse error:', e);
            }
        };

        eventSource.onerror = () => {
            eventSource.close();
            setIsStreaming(false);
        };

        return () => {
            eventSource.close();
        };
    }, [sessionId]);

    // Fallback: Phase cycling if NOT streaming
    useEffect(() => {
        if (isStreaming || sessionId) return;

        const interval = setInterval(() => {
            setPhaseIndex(prev => (prev + 1) % PHASES.length);
        }, 4000);
        return () => clearInterval(interval);
    }, [isStreaming, sessionId]);

    // Fallback: Local log generation if NOT streaming
    useEffect(() => {
        if (isStreaming || sessionId) return;

        let timeoutId: NodeJS.Timeout;
        let isMounted = true;

        const generateFallbackLog = () => {
            const currentLogs = FALLBACK_LOGS[currentPhase.id as keyof typeof FALLBACK_LOGS];
            const randomLog = currentLogs[Math.floor(Math.random() * currentLogs.length)];
            const timestamp = new Date().toISOString().split('T')[1].slice(0, 8);

            if (isMounted) {
                setLogs(prev => [...prev, `[${timestamp}] ${randomLog}`].slice(-6));
            }

            const nextDelay = Math.random() * 1500 + 800;
            timeoutId = setTimeout(generateFallbackLog, nextDelay);
        };

        generateFallbackLog();
        return () => {
            isMounted = false;
            clearTimeout(timeoutId);
        };
    }, [currentPhase, isStreaming, sessionId]);

    // Auto-scroll
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div className="w-full max-w-lg bg-gray-900 rounded-lg p-4 font-mono text-xs border border-gray-700 shadow-xl overflow-hidden relative group">
            {/* decorative header */}
            <div className="flex items-center justify-between mb-3 border-b border-gray-800 pb-2">
                <div className="flex items-center gap-2">
                    <span className="relative flex h-2 w-2">
                        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${currentPhase.bg} opacity-75`}></span>
                        <span className={`relative inline-flex rounded-full h-2 w-2 ${currentPhase.bg}`}></span>
                    </span>
                    <span className={`font-bold tracking-widest ${currentPhase.color}`}>
                        {isStreaming ? 'LIVE_STREAM' : 'ULTRATHINKING'}::{currentPhase.label}
                    </span>
                </div>
                <div className="text-gray-500">{isStreaming ? '● LIVE' : 'v3.0'}</div>
            </div>

            {/* Log Feed */}
            <div
                ref={scrollRef}
                className="h-32 overflow-hidden flex flex-col justify-end space-y-1 relative"
            >
                {/* scanline effect */}
                <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/10 pointer-events-none z-10" />

                {logs.map((log, i) => (
                    <div
                        key={i}
                        className={`transition-opacity duration-300 ${i === logs.length - 1 ? 'text-white font-bold opacity-100' : 'text-gray-400 opacity-60'}`}
                    >
                        <span className="text-gray-600 mr-2">{'>'}</span>{log}
                    </div>
                ))}
            </div>

            {/* Decorative footer */}
            <div className="mt-2 pt-2 border-t border-gray-800 flex justify-between text-[10px] text-gray-500 uppercase">
                <span>{isStreaming ? 'SSE Connected' : `Cpu usage: ${Math.floor(Math.random() * 30 + 40)}%`}</span>
                <span>Memory: {Math.floor(Math.random() * 200 + 1024)}mb</span>
            </div>
        </div>
    );
}

