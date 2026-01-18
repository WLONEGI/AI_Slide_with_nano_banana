"use client";

import * as React from "react";
import { DualPane } from "@/components/layout/DualPane";
import { Sidebar } from "@/components/layout/Sidebar";
import { useStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Menu } from "lucide-react";
import { ChatPane } from "@/components/chat/ChatPane";
import { PreviewPane } from "@/components/preview/PreviewPane";

export default function WorkspacePage() {
    const { isSidebarOpen, toggleSidebar } = useStore();

    return (
        <div className="flex h-screen w-full overflow-hidden bg-background">
            {/* Sidebar (Conditional) */}
            {isSidebarOpen && <Sidebar />}

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col h-full overflow-hidden">
                {/* Top Header (Mobile/Toggle) */}
                {!isSidebarOpen && (
                    <div className="absolute top-4 left-4 z-50">
                        <Button variant="ghost" size="icon" onClick={toggleSidebar}>
                            <Menu className="h-5 w-5" />
                        </Button>
                    </div>
                )}

                {/* Dual Pane Layout */}
                <DualPane
                    leftContent={<ChatPane />}
                    rightContent={<PreviewPane />}
                />
            </div>
        </div>
    );
}
