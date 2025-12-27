import { useState, useRef, useEffect } from 'react';

interface EnhancedInputProps {
    onSubmit: (text: string, file?: File | null) => void;
    placeholder?: string;
    initialValue?: string;
    disabled?: boolean;
}

export default function EnhancedInput({ onSubmit, placeholder = "Message...", initialValue = "", disabled = false }: EnhancedInputProps) {
    const [text, setText] = useState(initialValue);
    const [file, setFile] = useState<File | null>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Auto-resize logic
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'; // Reset to calculate scrollHeight
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
        }
    }, [text]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (text.trim() || file) {
                onSubmit(text, file);
                setText("");
                setFile(null);
            }
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
        }
    };

    return (
        <div className={`
            relative flex flex-col w-full bg-[#F5F5F7] border border-gray-200 
            rounded-2xl shadow-sm transition-all focus-within:ring-2 focus-within:ring-blue-100 focus-within:border-blue-300
            ${disabled ? 'opacity-60 pointer-events-none' : ''}
        `}>
            {/* File Preview */}
            {file && (
                <div className="mx-3 mt-3 px-3 py-2 bg-white rounded-lg border border-gray-200 flex items-center justify-between shadow-sm animate-fade-in">
                    <div className="flex items-center space-x-2 overflow-hidden">
                        <div className="w-8 h-8 bg-blue-50 text-blue-500 rounded flex items-center justify-center">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                        </div>
                        <span className="text-xs font-medium text-gray-700 truncate max-w-[200px]">{file.name}</span>
                    </div>
                    <button
                        onClick={() => setFile(null)}
                        className="text-gray-400 hover:text-red-500 p-1 rounded-full hover:bg-gray-100 transition-colors"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                </div>
            )}

            {/* Config & Text Area */}
            <div className="flex flex-col px-1 pb-1">
                <textarea
                    ref={textareaRef}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder}
                    rows={1}
                    className="
                        w-full bg-transparent border-none focus:ring-0 
                        text-[15px] leading-relaxed text-gray-800 placeholder-gray-400
                        p-3 resize-none min-h-[44px] max-h-[200px]
                        scrollbar-thin scrollbar-thumb-gray-200
                    "
                />

                {/* Bottom Toolbar */}
                <div className="flex items-center justify-between px-2 pb-1 pt-1">
                    <div className="flex items-center space-x-1">
                        {/* Attachment Button */}
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-lg transition-colors group relative"
                            title="Attach file"
                        >
                            <input
                                type="file"
                                ref={fileInputRef}
                                className="hidden"
                                onChange={handleFileChange}
                            />
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" /></svg>
                        </button>

                        {/* Image Button (Visual Only for now) */}
                        <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-lg transition-colors" title="Add Image">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                        </button>

                        {/* Voice Button (Visual Only for now) */}
                        <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-lg transition-colors" title="Voice Input">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" /></svg>
                        </button>
                    </div>

                    <div className="flex items-center space-x-3">
                        {/* Token Count (Visual Estimate) */}
                        {text.length > 0 && (
                            <span className="text-[10px] text-gray-400 font-mono">
                                {text.length} chars
                            </span>
                        )}

                        {/* Submit Button */}
                        <button
                            onClick={() => { if (text.trim() || file) { onSubmit(text, file); setText(""); setFile(null); } }}
                            disabled={!text.trim() && !file}
                            className={`
                                p-2 rounded-xl transition-all shadow-sm flex items-center justify-center
                                ${text.trim() || file
                                    ? 'bg-black text-white hover:bg-gray-800 hover:shadow-md transform hover:scale-105'
                                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'}
                            `}
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" /></svg>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
