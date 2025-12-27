import { useState } from 'react';

interface LandingPageProps {
    onStart: (message: string) => void;
}

export default function LandingPage({ onStart }: LandingPageProps) {
    const [input, setInput] = useState("");

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (input.trim()) {
                onStart(input);
            }
        }
    };

    const suggestions = [
        "Explain Quantum Computing in 3 slides",
        "Pitch deck for a new AI startup",
        "Quarterly marketing report strategy",
        "Design trends for 2025"
    ];

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-[#F9FAFB] text-[#1F2937] p-4 font-sans">
            <div className="w-full max-w-2xl flex flex-col items-center space-y-8 animate-fade-in-up">

                {/* Hero Section */}
                <div className="text-center space-y-2">
                    <h1 className="text-4xl md:text-5xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-600 pb-1">
                        What would you like to create?
                    </h1>
                    <p className="text-gray-500 text-lg">
                        Generate professional presentations with AI guidance.
                    </p>
                </div>

                {/* Input Area */}
                <div className="w-full relative group">
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-100 to-purple-100 rounded-2xl blur opacity-25 group-hover:opacity-40 transition duration-500"></div>
                    <div className="relative bg-white rounded-2xl shadow-lg border border-gray-100 p-2 flex flex-col">
                        <textarea
                            className="w-full bg-transparent border-none focus:ring-0 text-lg p-4 resize-none min-h-[60px] max-h-[200px] outline-none placeholder-gray-400 text-gray-800"
                            placeholder="Describe your presentation..."
                            rows={1}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                        />
                        <div className="flex justify-between items-center px-2 pb-2">
                            <div className="flex space-x-2">
                                {/* Placeholder for future attachments button */}
                            </div>
                            <button
                                onClick={() => input.trim() && onStart(input)}
                                disabled={!input.trim()}
                                className={`p-2 rounded-full transition-all duration-200 ${input.trim() ? 'bg-black text-white hover:bg-gray-800 shadow-md transform hover:scale-105' : 'bg-gray-100 text-gray-300 cursor-not-allowed'}`}
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" /></svg>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Suggestions */}
                <div className="flex flex-wrap justify-center gap-2 w-full">
                    {suggestions.map((s, i) => (
                        <button
                            key={i}
                            onClick={() => onStart(s)}
                            className="px-4 py-2 bg-white border border-gray-200 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 text-sm font-medium rounded-full transition-colors shadow-sm text-gray-600"
                        >
                            {s}
                        </button>
                    ))}
                </div>

            </div>

            <div className="fixed bottom-4 text-xs text-gray-400">
                AI can make mistakes. Please verify generated content.
            </div>
        </div>
    );
}
