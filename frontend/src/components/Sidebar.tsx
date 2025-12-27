import { useState } from 'react';

interface SidebarProps {
    isOpen: boolean;
    onToggle: () => void;
    onNewChat: () => void;
}

export default function Sidebar({ isOpen, onToggle, onNewChat }: SidebarProps) {
    // Mock History Data
    const history = [
        { id: 1, title: "Quantum Computing Logic", date: "Today" },
        { id: 2, title: "Q3 Marketing Strategy", date: "Today" },
        { id: 3, title: "Startup Pitch Deck", date: "Yesterday" },
        { id: 4, title: "Dark Matter Explanation", date: "Yesterday" },
    ];

    return (
        <div
            className={`
                bg-[#F9FAFB] border-r border-gray-200 flex flex-col transition-all duration-300 ease-in-out
                ${isOpen ? 'w-64' : 'w-0 opacity-0 overflow-hidden'}
            `}
        >
            {/* Header */}
            <div className="h-14 flex items-center px-4 border-b border-gray-200 shrink-0">
                <button
                    onClick={onNewChat}
                    className="flex-1 flex items-center justify-center space-x-2 bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 rounded-lg py-1.5 px-3 text-sm font-medium transition-colors shadow-sm"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                    <span>New Chat</span>
                </button>
            </div>

            {/* Content check */}
            <div className="flex-1 overflow-y-auto p-3 custom-scrollbar">
                <div className="space-y-6">
                    {/* Group: Today */}
                    <div>
                        <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 px-2">Today</h3>
                        <ul className="space-y-1">
                            {history.filter(h => h.date === "Today").map(h => (
                                <li key={h.id}>
                                    <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-200 rounded-lg transition-colors truncate">
                                        {h.title}
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Group: Yesterday */}
                    <div>
                        <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 px-2">Yesterday</h3>
                        <ul className="space-y-1">
                            {history.filter(h => h.date === "Yesterday").map(h => (
                                <li key={h.id}>
                                    <button className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-200 rounded-lg transition-colors truncate">
                                        {h.title}
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            </div>

            {/* Footer / User Profile */}
            <div className="p-4 border-t border-gray-200">
                <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-400 to-blue-500 flex items-center justify-center text-white text-xs font-bold">
                        U
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">User Account</p>
                        <p className="text-xs text-gray-500 truncate">Pro Plan</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
