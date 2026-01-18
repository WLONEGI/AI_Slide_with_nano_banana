"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Sparkles, ArrowRight } from "lucide-react";
import { useStore } from "@/lib/store";

export default function HomePage() {
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const { setCurrentSessionId, addMessage } = useStore();

  const handleStart = () => {
    if (!topic.trim()) return;

    // In a real app, we might call API to create session first
    const newSessionId = `session-${Date.now()}`;
    setCurrentSessionId(newSessionId);

    // Add initial user message
    addMessage({
      id: `msg-${Date.now()}`,
      role: 'user',
      content: topic,
      timestamp: new Date()
    });

    router.push("/workspace");
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-lg border-none shadow-2xl bg-card/50 backdrop-blur-sm">
        <CardHeader className="text-center">
          <div className="mx-auto bg-primary/10 p-3 rounded-full w-fit mb-4">
            <Sparkles className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-3xl font-bold">AI Slide Generator</CardTitle>
          <CardDescription className="text-lg mt-2">
            What would you like to create a presentation about today?
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="relative">
            <Input
              placeholder="e.g. The Future of AI in Healthcare..."
              className="pl-4 pr-12 h-14 text-lg rounded-full shadow-sm"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleStart()}
            />
            <Button
              size="icon"
              className="absolute right-1.5 top-1.5 h-11 w-11 rounded-full"
              onClick={handleStart}
              disabled={!topic.trim()}
            >
              <ArrowRight className="h-5 w-5" />
            </Button>
          </div>

          <div className="flex justify-center gap-2 mt-6">
            <p className="text-xs text-muted-foreground">
              Powered by Gemini 2.0 & LangGraph
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
