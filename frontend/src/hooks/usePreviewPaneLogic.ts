import { useState } from 'react';
import { SlidePlan } from '../types';
import { apiUrl } from '../lib/api';

export function usePreviewPaneLogic(plan: SlidePlan | null) {
    const [downloading, setDownloading] = useState(false);
    const [activeTab, setActiveTab] = useState<Record<number, 'preview' | 'prompt'>>({});
    const [isEditMode, setIsEditMode] = useState(false); // Global edit mode

    const handleDownloadPDF = async () => {
        if (!plan) return;
        setDownloading(true);
        try {
            const images = document.querySelectorAll('img[data-testid^="slide-image-"]');
            const urls = Array.from(images).map(img => (img as HTMLImageElement).src);

            const res = await fetch(apiUrl("/api/assemble"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image_urls: urls })
            });
            if (!res.ok) throw new Error("Download failed");
            const data = await res.json();
            window.open(data.url, '_blank');
        } catch (e) {
            console.error(e);
            alert("Failed to download PDF");
        } finally {
            setDownloading(false);
        }
    };

    return {
        downloading,
        activeTab,
        setActiveTab,
        isEditMode,
        setIsEditMode,
        handleDownloadPDF
    };
}
