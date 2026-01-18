"use client";

import React, { useEffect, useRef } from 'react';
import { useStore } from "@/lib/store";
import { useChatStream } from "@/lib/sse";
import { AgentLogs } from "./AgentLogs";
import { ArtifactCard } from "./ArtifactCard";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, StopCircle } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from "@/lib/utils";

export function ChatPane() {
    const {
        messages,
        artifacts,
        messageInput,
        setMessageInput,
        isStreaming,
        currentSessionId
    } = useStore();

    const { startStream } = useChatStream();
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll on new messages
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, artifacts]);

    const handleSend = () => {
        if (!messageInput.trim() || isStreaming) return;

        const text = messageInput;
        setMessageInput(""); // Clear input

        // Assume "Demo Session" if none exists, or use current
        const threadId = currentSessionId || "demo-thread";

        startStream(text, threadId);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    // Merge Messages and Artifacts for Timeline View?
    // Simply rendering messages, then a separate list of recently created artifacts?
    // SPEC: "event: artifact -> Artifact Cardをチャット欄に生成"
    // To do this strictly chronologically, we'd need a unified 'TimelineItem' list.
    // For now, let's render standard messages. Artifacts are added to the list as they come?
    // Actually, 'messages' store only has ChatMessage. 'artifacts' store has Artifact.
    // We can render artifacts at the bottom or intersperse them if we stored them in 'messages' as a specific type.
    // Let's render "Latest Artifacts" separately or just check timestamps?
    // SIMPLIFICATION for Prototype:
    // Render Messages.
    // Render the *Latest* Artifact Card immediately after the assistant message if it was just created.
    // actually, let's just show artifacts in the chat flow. 
    // We can create a "System Message" that holds the artifact ID.
    // But for now, let's keep it simple: Messages in the ScrollArea. 
    // We will map artifacts to the bottom or use the logs for that.

    // Better approach: When an artifact is added, maybe we should also add a "System Message" saying "Generated Artifact: X"?
    // Let's stick to: Messages + Logs. Artifacts appear in the Right Pane automatically.
    // But wait, user wants cards in Chat.
    // I will filter artifacts that are 'new' and display them.
    // Actually, let's just display ALL artifacts that belong to this session interleaved?
    // Let's just render the Artifacts in a separate "Recent Artifacts" block above the Logs or combined.

    // CURRENT DECISION: Split Chat View:
    // Top: Message History
    // Bottom: Agent Logs (Process)
    // Artifacts are technically part of the output.

    return (
        <div className="flex flex-col h-full bg-background/50 backdrop-blur-sm">
            {/* Chat Area */}
            <div className="flex-1 overflow-hidden flex flex-col relative">
                <ScrollArea className="flex-1 p-4">
                    <div className="space-y-6 pb-20"> {/* Padding for potential floating input */}
                        <AnimatePresence initial={false}>
                            {messages.map((msg) => (
                                <motion.div
                                    key={msg.id}
                                    initial={{ opacity: 0, y: 20, scale: 0.95 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                                    className={cn("flex flex-col gap-2 group", msg.role === 'user' ? "items-end" : "items-start")}
                                >
                                    <div className={cn(
                                        "max-w-[85%] rounded-2xl p-4 text-sm shadow-sm transition-all duration-200",
                                        msg.role === 'user'
                                            ? "bg-primary text-primary-foreground rounded-br-none"
                                            : "bg-muted/50 border border-border/50 text-foreground rounded-bl-none hover:bg-muted/80 hover:shadow-md"
                                    )}>
                                        <div className="prose dark:prose-invert text-sm break-words leading-relaxed">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {msg.content}
                                            </ReactMarkdown>
                                        </div>
                                    </div>
                                    <span className="text-[10px] text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity px-2">
                                        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                </motion.div>
                            ))}
                        </AnimatePresence>

                        {/* Render Artifact Cards inline based on time? 
                            For now, let's render ALL artifacts at the bottom of the chat as a "Result Stack"
                            until we have better intercalation logic. 
                        */}
                        {artifacts.length > 0 && (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="space-y-2 pt-4 border-t border-border/40 mt-8"
                            >
                                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-3 px-1">Artifacts</p>
                                <div className="grid grid-cols-1 gap-2">
                                    {artifacts.map(art => (
                                        <ArtifactCard key={art.id} artifact={art} />
                                    ))}
                                </div>
                            </motion.div>
                        )}

                        <div ref={scrollRef} />
                    </div>
                </ScrollArea>
            </div>

            {/* Process / Logs Section (Collapsible or Fixed Height) */}
            <div className="h-1/3 border-t border-border bg-muted/10 flex flex-col min-h-[150px]">
                <div className="px-4 py-2 bg-muted/20 border-b border-border/50 flex justify-between items-center">
                    <span className="text-xs font-medium text-muted-foreground">Process Logs</span>
                    {isStreaming && <StopCircle className="h-4 w-4 text-red-500 animate-pulse cursor-pointer" />}
                </div>
                <div className="flex-1 overflow-hidden">
                    <AgentLogs />
                </div>
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-border bg-background">
                <div className="flex gap-2">
                    <Textarea
                        value={messageInput}
                        onChange={(e) => setMessageInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Type a message..."
                        className="min-h-[50px] max-h-[150px] resize-none"
                        disabled={isStreaming}
                    />
                    <Button
                        className="h-auto"
                        onClick={handleSend}
                        disabled={!messageInput.trim() || isStreaming}
                    >
                        <Send className="h-4 w-4" />
                    </Button>
                </div>
            </div>
        </div>
    );
}
