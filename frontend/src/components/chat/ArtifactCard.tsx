"use client";

import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Artifact } from "@/lib/types";
import { useStore } from "@/lib/store";
import { FileText, Image as ImageIcon, LayoutList, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface ArtifactCardProps {
    artifact: Artifact;
}

export function ArtifactCard({ artifact }: ArtifactCardProps) {
    const { setActiveArtifactId, activeArtifactId } = useStore();
    const isActive = activeArtifactId === artifact.id;

    const getIcon = () => {
        switch (artifact.type) {
            case 'image': return <ImageIcon className="h-5 w-5 text-purple-500" />;
            case 'plan': return <LayoutList className="h-5 w-5 text-blue-500" />;
            default: return <FileText className="h-5 w-5 text-orange-500" />;
        }
    };

    return (
        <motion.div
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            transition={{ type: "spring", stiffness: 400, damping: 17 }}
        >
            <Card
                className={cn(
                    "cursor-pointer transition-all duration-300 border-l-4 overflow-hidden relative group",
                    isActive
                        ? "border-l-primary bg-accent/20 border-y-accent/20 border-r-accent/20 shadow-lg"
                        : "border-l-transparent hover:bg-muted/40 hover:border-l-muted-foreground/30 hover:shadow-md"
                )}
                onClick={() => setActiveArtifactId(artifact.id)}
            >
                <CardHeader className="p-4 flex flex-row items-center gap-4 space-y-0 relative z-10">
                    <div className={cn(
                        "p-2.5 rounded-xl shadow-sm border transition-colors duration-300",
                        isActive ? "bg-background border-primary/20 text-primary" : "bg-muted/30 text-muted-foreground group-hover:bg-background group-hover:text-foreground"
                    )}>
                        {getIcon()}
                    </div>
                    <div className="flex-1 min-w-0">
                        <CardTitle className="text-sm font-semibold truncate group-hover:text-primary transition-colors">
                            {artifact.title}
                        </CardTitle>
                        <CardDescription className="text-[10px] font-medium tracking-wide text-muted-foreground/80 truncate flex items-center gap-2 mt-0.5">
                            <span className="uppercase">{artifact.type}</span>
                            <span className="w-1 h-1 rounded-full bg-border" />
                            <span>v{artifact.version}</span>
                        </CardDescription>
                    </div>
                    <Button variant="ghost" size="icon" className="opacity-0 group-hover:opacity-100 transition-opacity -mr-2">
                        <ArrowRight className="h-4 w-4" />
                    </Button>
                </CardHeader>
                {/* Abstract background decoration */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-transparent to-primary/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            </Card>
        </motion.div>
    );
}
