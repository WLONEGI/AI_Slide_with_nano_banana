import { useCallback } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useStore } from './store';
import { Artifact, AgentLog } from './types';

// Endpoint
const API_URL = '/api/chat/stream'; // Next.js will proxy this to Backend

export function useChatStream() {
    const {
        addMessage,
        addLog,
        addArtifact,
        setIsStreaming,
        currentSessionId,
        setActiveArtifactId
    } = useStore();

    const startStream = useCallback(async (message: string, threadId: string) => {
        setIsStreaming(true);
        const ctrl = new AbortController();
        const seenMessageIds = new Set<string>();

        try {
            await fetchEventSource(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    messages: [
                        {
                            role: "user",
                            content: message
                        }
                    ],
                    thread_id: threadId,
                    debug: true, // For logs
                    deep_thinking_mode: true,
                    search_before_planning: true
                }),
                signal: ctrl.signal,

                onopen(response) {
                    if (response.ok) {
                        return Promise.resolve();
                    } else {
                        return Promise.reject(new Error(`Failed to connect: ${response.status}`));
                    }
                },

                onmessage(ev) {
                    if (!ev.data) return;

                    try {
                        if (ev.event === 'message') {
                            // OPTIMIZED: Raw Text for Message Content
                            // Backend sends: "event": "message", "id": "msg_id", "data": "raw content"
                            const content = ev.data;
                            const msgId = ev.id || `msg-${Date.now()}`;
                            const role = 'assistant';

                            if (content) {
                                // Add or Append
                                if (!seenMessageIds.has(msgId)) {
                                    seenMessageIds.add(msgId);
                                    addMessage({
                                        id: msgId,
                                        role: role,
                                        content: content,
                                        timestamp: new Date()
                                    });
                                } else {
                                    appendMessageContent(msgId, content);
                                }
                            }
                        } else {
                            // JSON Protocol (Logs, Artifacts)
                            const data = JSON.parse(ev.data);

                            switch (ev.event) {
                                case 'start_of_agent':
                                case 'on_chain_start':
                                    addLog({
                                        id: `log-${Date.now()}`,
                                        agent: data.agent_name || "System",
                                        step: "Started",
                                        status: 'running',
                                        timestamp: new Date()
                                    });
                                    break;

                                case 'end_of_agent':
                                case 'on_chain_end':
                                    addLog({
                                        id: `log-${Date.now()}`,
                                        agent: data.agent_name || "System",
                                        step: "Completed",
                                        status: 'completed',
                                        timestamp: new Date()
                                    });
                                    break;

                                case 'artifact':
                                    const newArtifact: Artifact = {
                                        id: data.id,
                                        type: data.type,
                                        title: data.title,
                                        content: data.content,
                                        version: data.version || 1,
                                        timestamp: new Date()
                                    };
                                    addArtifact(newArtifact);
                                    setActiveArtifactId(newArtifact.id);
                                    break;
                            }
                        }

                    } catch (e) {
                        console.error("Error parsing event data", e);
                    }
                },

                onerror(err) {
                    console.error("SSE Error", err);
                    // Don't retry automatically for now to avoid loops
                    throw err;
                },

                onclose() {
                    setIsStreaming(false);
                }
            });
        } catch (err) {
            console.error("Stream failed", err);
            setIsStreaming(false);
        }
    }, [addMessage, addLog, addArtifact, setIsStreaming, setActiveArtifactId]);

    return { startStream };
}
