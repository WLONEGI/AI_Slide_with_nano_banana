import React from 'react';
import { ScrollArea } from "@/components/ui/scroll-area";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { CheckCircle2, Loader2, Circle, XCircle } from "lucide-react";

export function AgentLogs() {
    const { logs } = useStore();
    const scrollRef = React.useRef<HTMLDivElement>(null);

    React.useEffect(() => {
        // Auto-scroll to bottom
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
    }, [logs]);

    return (
        <ScrollArea className="h-full pr-4">
            <div className="space-y-4 p-4">
                {logs.map((log, index) => (
                    <div key={index} className="flex items-start gap-3 animate-in fade-in slide-in-from-bottom-2">
                        <div className="mt-1">
                            {log.status === 'running' && <Loader2 className="h-4 w-4 animate-spin text-blue-500" />}
                            {log.status === 'completed' && <CheckCircle2 className="h-4 w-4 text-green-500" />}
                            {log.status === 'failed' && <XCircle className="h-4 w-4 text-red-500" />}
                            {log.status === 'pending' && <Circle className="h-4 w-4 text-muted-foreground" />}
                        </div>
                        <div className="flex-1 space-y-1">
                            <p className="text-sm font-medium leading-none">
                                {log.agent}
                            </p>
                            <p className="text-xs text-muted-foreground">
                                {log.step}
                            </p>
                        </div>
                        <span className="text-xs text-muted-foreground tabular-nums">
                            {log.timestamp.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                    </div>
                ))}
                <div ref={scrollRef} />
            </div>
        </ScrollArea>
    );
}
