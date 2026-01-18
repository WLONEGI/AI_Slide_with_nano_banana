export type Role = 'user' | 'assistant' | 'system' | 'researcher' | 'storywriter' | 'visualizer' | 'planner' | 'data_analyst' | 'coordinator' | 'reviewer';

export interface ChatMessage {
    id: string;
    role: Role;
    content: string; // HTML/Markdown string
    timestamp: Date;
    agentName?: string;
    isThinking?: boolean;
}

export interface AgentLog {
    id: string;
    agent: string;
    step: string;
    status: 'running' | 'completed' | 'failed' | 'pending';
    timestamp: Date;
    details?: string;
}

export type ArtifactType = 'report' | 'outline' | 'image' | 'code' | 'plan';

export interface Artifact {
    id: string;
    type: ArtifactType;
    title: string;
    content: any; // Markdown string, JSON object, or Image URL
    version: number;
    timestamp: Date;
}

export interface Session {
    id: string;
    title: string;
    timestamp: string; // ISO date
    summary?: string;
}

export interface User {
    uid: string;
    email?: string;
    displayName?: string;
    photoURL?: string;
}
