"use client";

import * as React from "react";
import {
    ResizableHandle,
    ResizablePanel,
    ResizablePanelGroup,
} from "@/components/ui/resizable";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useStore } from "@/lib/store";

interface DualPaneProps {
    leftContent: React.ReactNode;
    rightContent: React.ReactNode;
}

export function DualPane({ leftContent, rightContent }: DualPaneProps) {
    const { activeArtifactId } = useStore();

    return (
        <div className="h-screen w-full bg-background text-foreground overflow-hidden flex flex-col">
            {/* Header/Nav could go here */}

            <ResizablePanelGroup direction="horizontal" className="flex-1 h-full">
                {/* LEFT PANE: Communication & Process */}
                <ResizablePanel defaultSize={50} minSize={30} maxSize={70} className="flex flex-col border-r border-border/40">
                    <div className="h-full w-full relative">
                        {leftContent}
                    </div>
                </ResizablePanel>

                <ResizableHandle withHandle />

                {/* RIGHT PANE: Artifact Preview */}
                <ResizablePanel defaultSize={50} minSize={30} maxSize={70}>
                    <div className="h-full w-full bg-muted/20 relative flex flex-col">
                        {/* If no artifact is selected, show a placeholder or empty state */}
                        {!activeArtifactId ? (
                            <div className="flex-1 flex items-center justify-center text-muted-foreground flex-col gap-2">
                                <p>Select an artifact to preview</p>
                            </div>
                        ) : (
                            rightContent
                        )}
                    </div>
                </ResizablePanel>
            </ResizablePanelGroup>
        </div>
    );
}
