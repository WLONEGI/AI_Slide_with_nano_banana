"use client";

import React from 'react';
import { useStore } from "@/lib/store";
import { MarkdownViewer } from "./MarkdownViewer";
import { SlideViewer } from "./SlideViewer";
import { ScrollArea } from "@/components/ui/scroll-area";

export function PreviewPane() {
    const { artifacts, activeArtifactId } = useStore();

    const activeArtifact = artifacts.find(a => a.id === activeArtifactId);

    if (!activeArtifact) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground p-8 text-center">
                <h3 className="text-lg font-medium">No Artifact Selected</h3>
                <p className="text-sm">Select an artifact from the chat timeline to view details.</p>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col">
            <div className="px-6 py-4 border-b border-border bg-background flex justify-between items-center">
                <h2 className="font-semibold text-lg truncate">{activeArtifact.title}</h2>
                <span className="text-xs text-muted-foreground uppercase tracking-wider border px-2 py-1 rounded">
                    {activeArtifact.type}
                </span>
            </div>

            <div className="flex-1 overflow-hidden relative bg-background/50">
                {activeArtifact.type === 'report' || activeArtifact.type === 'outline' ? (
                    <ScrollArea className="h-full">
                        <div className="p-8 max-w-4xl mx-auto">
                            <MarkdownViewer content={activeArtifact.content} />
                        </div>
                    </ScrollArea>
                ) : activeArtifact.type === 'image' || activeArtifact.type === 'plan' ? (
                    <SlideViewer artifact={activeArtifact} />
                ) : (
                    <div className="p-8">
                        <pre className="text-xs bg-muted p-4 rounded overflow-auto max-h-[500px]">
                            {JSON.stringify(activeArtifact.content, null, 2)}
                        </pre>
                    </div>
                )}
            </div>
        </div>
    );
}
