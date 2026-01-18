"use client";

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownViewerProps {
    content: any; // string or object
}

export function MarkdownViewer({ content }: MarkdownViewerProps) {
    // Ensure content is string
    const stringContent = typeof content === 'string'
        ? content
        : JSON.stringify(content, null, 2);

    return (
        <article className="prose dark:prose-invert max-w-none prose-sm sm:prose-base lg:prose-lg text-foreground">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {stringContent}
            </ReactMarkdown>
        </article>
    );
}
