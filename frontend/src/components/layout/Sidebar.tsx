"use client";

import * as React from "react";
import { useStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, MessageSquare, History } from "lucide-react";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";

export function Sidebar() {
    const { isSidebarOpen, sessions, currentSessionId, setCurrentSessionId } = useStore();
    const router = useRouter();

    // Mock fetching history (in real app, this would be an effect calling /api/history)
    React.useEffect(() => {
        // Only fetch if empty for now
        if (sessions.length === 0) {
            // Mock data
            useStore.getState().setSessions([
                { id: "1", title: "Japan Economy", timestamp: new Date().toISOString() },
                { id: "2", title: "AI Trends 2024", timestamp: new Date().toISOString() },
            ]);
        }
    }, [sessions.length]);

    if (!isSidebarOpen) return null;

    const handleNewChat = () => {
        setCurrentSessionId(null);
        // Logic to start new chat or navigate
    };

    return (
        <div className="w-64 h-full border-r border-border bg-card flex flex-col">
            <div className="p-4 border-b border-border">
                <Button onClick={handleNewChat} className="w-full gap-2" variant="outline">
                    <Plus className="h-4 w-4" />
                    New Chat
                </Button>
            </div>

            <ScrollArea className="flex-1">
                <div className="p-2 space-y-1">
                    <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                        Recents
                    </div>
                    {sessions.map((session) => (
                        <Button
                            key={session.id}
                            variant={currentSessionId === session.id ? "secondary" : "ghost"}
                            className={cn("w-full justify-start font-normal truncat",
                                currentSessionId === session.id && "bg-accent text-accent-foreground"
                            )}
                            onClick={() => setCurrentSessionId(session.id)}
                        >
                            <MessageSquare className="mr-2 h-4 w-4" />
                            <span className="truncate">{session.title}</span>
                        </Button>
                    ))}
                </div>
            </ScrollArea>

            <div className="p-4 border-t border-border">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                        U
                    </div>
                    <span>User</span>
                </div>
            </div>
        </div>
    );
}
