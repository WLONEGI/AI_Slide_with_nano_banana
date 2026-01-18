"use client";

import React from 'react';
import { Artifact } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Image as ImageIcon } from "lucide-react";

interface SlideViewerProps {
    artifact: Artifact;
}

export function SlideViewer({ artifact }: SlideViewerProps) {
    if (artifact.type === 'image') {
        const imageUrl = typeof artifact.content === 'string' ? artifact.content : null;

        return (
            <div className="h-full flex flex-col">
                <div className="flex-1 flex items-center justify-center p-8 bg-black/5 relative overflow-hidden">
                    {/* Placeholder for Image & In-painting Overlay */}
                    {imageUrl ? (
                        <div className="relative shadow-2xl border-4 border-white rounded-lg max-h-full max-w-full">
                            <img src={imageUrl} alt="Slide Preview" className="max-h-full max-w-full object-contain" />
                            {/* In-painting Overlay would go here */}
                        </div>
                    ) : (
                        <div className="text-muted-foreground flex flex-col items-center">
                            <ImageIcon className="h-12 w-12 mb-4 opacity-50" />
                            <p>Image not available or invalid format</p>
                        </div>
                    )}
                </div>

                {/* Controls Area (Zoom, In-paint Toggle) */}
                <div className="p-4 border-t border-border bg-background flex justify-end gap-2">
                    <Button variant="outline">Zoom In</Button>
                    <Button variant="outline">Zoom Out</Button>
                    <Button>Edit Slide (In-paint)</Button>
                </div>
            </div>
        );
    }

    // Default Fallback
    return (
        <ScrollArea className="h-full p-4">
            <pre className="text-xs font-mono bg-muted p-4 rounded">
                {JSON.stringify(artifact.content, null, 2)}
            </pre>
        </ScrollArea>
    );
}
