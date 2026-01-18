import { create } from 'zustand';
import { Artifact, ChatMessage, AgentLog, Session, User } from './types';

interface AppState {
    // User/Auth
    user: User | null;
    setUser: (user: User | null) => void;

    // Session
    currentSessionId: string | null;
    setCurrentSessionId: (id: string | null) => void;
    sessions: Session[];
    setSessions: (sessions: Session[]) => void;

    // Chat & Process
    messages: ChatMessage[];
    addMessage: (msg: ChatMessage) => void;
    appendMessageContent: (id: string, content: string) => void;
    setMessages: (msgs: ChatMessage[]) => void;

    logs: AgentLog[];
    addLog: (log: AgentLog) => void;
    clearLogs: () => void;

    isStreaming: boolean;
    setIsStreaming: (v: boolean) => void;

    // Artifacts & Preview
    artifacts: Artifact[];
    addArtifact: (artifact: Artifact) => void;
    updateArtifact: (id: string, updates: Partial<Artifact>) => void;

    activeArtifactId: string | null; // What is shown in Right Pane
    setActiveArtifactId: (id: string | null) => void;

    // UI State
    isSidebarOpen: boolean;
    toggleSidebar: () => void;
    messageInput: string;
    setMessageInput: (v: string) => void;
}

export const useStore = create<AppState>((set) => ({
    user: null,
    setUser: (user) => set({ user }),

    currentSessionId: null,
    setCurrentSessionId: (id) => set({ currentSessionId: id }),
    sessions: [],
    setSessions: (sessions) => set({ sessions }),

    messages: [],
    addMessage: (msg) => set((state) => {
        const exists = state.messages.find(m => m.id === msg.id);
        if (exists) return state; // Prevent duplicates if full message re-sent
        return { messages: [...state.messages, msg] };
    }),
    appendMessageContent: (id, content) => set((state) => ({
        messages: state.messages.map(m =>
            m.id === id
                ? { ...m, content: (typeof m.content === 'string' ? m.content + content : m.content) }
                : m
        )
    })),
    setMessages: (messages) => set({ messages }),

    logs: [],
    addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),
    clearLogs: () => set({ logs: [] }),

    isStreaming: false,
    setIsStreaming: (v) => set({ isStreaming: v }),

    artifacts: [],
    addArtifact: (artifact) => set((state) => {
        // Check if exists
        const exists = state.artifacts.find(a => a.id === artifact.id);
        if (exists) {
            return {
                artifacts: state.artifacts.map(a => a.id === artifact.id ? { ...a, ...artifact } : a)
            };
        }
        return { artifacts: [...state.artifacts, artifact] };
    }),
    updateArtifact: (id, updates) => set((state) => ({
        artifacts: state.artifacts.map(a => a.id === id ? { ...a, ...updates } : a)
    })),

    activeArtifactId: null,
    setActiveArtifactId: (id) => set({ activeArtifactId: id }),

    isSidebarOpen: true,
    toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

    messageInput: "",
    setMessageInput: (v) => set({ messageInput: v }),
}));
