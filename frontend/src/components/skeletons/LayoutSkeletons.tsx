import React from 'react';

interface SkeletonProps {
    text?: string;
    className?: string;
}

const ShimmerBlock = ({ className }: { className?: string }) => (
    <div className={`bg-gray-200 animate-pulse rounded ${className}`} />
);

// --- Layout: Title ---
export const TitleSkeleton = ({ text }: SkeletonProps) => {
    return (
        <div className="w-full h-full bg-white flex flex-col items-center justify-center p-16 space-y-8 animate-fade-in relative overflow-hidden">
            {/* Background Hint */}
            <div className="absolute inset-0 bg-gradient-to-br from-gray-50 to-white -z-10" />

            {/* Title Area */}
            <div className="w-3/4 space-y-4 flex flex-col items-center">
                {text ? (
                    <h1 className="text-4xl font-bold text-gray-300 text-center leading-tight tracking-tight line-clamp-3">
                        {text}
                    </h1>
                ) : (
                    <>
                        <ShimmerBlock className="h-12 w-3/4" />
                        <ShimmerBlock className="h-12 w-1/2" />
                    </>
                )}
            </div>

            {/* Subtitle/Decoration Area */}
            <ShimmerBlock className="h-1 w-24 mt-8 bg-gray-300" />
            <ShimmerBlock className="h-4 w-1/3" />
        </div>
    );
};

// --- Layout: Content Left ---
export const ContentLeftSkeleton = ({ text }: SkeletonProps) => {
    return (
        <div className="w-full h-full bg-white flex p-12 space-x-12 animate-fade-in relative overflow-hidden">
            <div className="absolute inset-0 bg-gray-50 -z-10" />

            {/* Left: Content */}
            <div className="w-1/2 flex flex-col justify-center space-y-6">
                {/* Title Hint */}
                <ShimmerBlock className="h-8 w-3/4 mb-4" />

                {/* Body Text / Bullets */}
                <div className="space-y-3">
                    {text ? (
                        <p className="text-lg text-gray-300 leading-relaxed whitespace-pre-wrap line-clamp-[8]">
                            {text}
                        </p>
                    ) : (
                        <>
                            <ShimmerBlock className="h-4 w-full" />
                            <ShimmerBlock className="h-4 w-full" />
                            <ShimmerBlock className="h-4 w-5/6" />
                            <ShimmerBlock className="h-4 w-4/6" />
                        </>
                    )}
                </div>
            </div>

            {/* Right: Visual */}
            <div className="w-1/2 flex items-center justify-center">
                <div className="w-full aspect-[4/3] bg-gray-200 rounded-lg animate-pulse shadow-sm flex items-center justify-center">
                    <svg className="w-12 h-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                </div>
            </div>
        </div>
    );
};

// --- Layout: Visual Center ---
export const VisualCenterSkeleton = ({ text }: SkeletonProps) => {
    return (
        <div className="w-full h-full bg-white flex flex-col items-center justify-center p-8 space-y-6 animate-fade-in relative">
            {/* Visual Area (Dominant) */}
            <div className="w-2/3 aspect-[16/9] bg-gray-200 rounded-lg animate-pulse shadow-sm flex items-center justify-center relative">
                <div className="absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-gray-300/20 to-transparent" />
            </div>

            {/* Caption Area */}
            <div className="w-3/4 text-center space-y-2">
                {text ? (
                    <p className="text-xl font-medium text-gray-300 line-clamp-2">{text}</p>
                ) : (
                    <ShimmerBlock className="h-6 w-1/2 mx-auto" />
                )}
            </div>
        </div>
    );
};

// --- Layout: Split Horizontal ---
export const SplitHorizontalSkeleton = ({ text }: SkeletonProps) => {
    return (
        <div className="w-full h-full bg-white flex flex-col animate-fade-in">
            {/* Top: Visual */}
            <div className="h-1/2 bg-gray-200 animate-pulse w-full relative overflow-hidden">
                <div className="absolute inset-0 flex items-center justify-center opacity-30">
                    <div className="w-32 h-32 rounded-full border-4 border-white/50" />
                </div>
            </div>

            {/* Bottom: Content */}
            <div className="h-1/2 p-10 flex flex-col justify-center space-y-4 bg-white">
                <ShimmerBlock className="h-8 w-1/3 mb-2" />
                <div className="space-y-2">
                    {text ? (
                        <div className="grid grid-cols-2 gap-4">
                            <p className="text-sm text-gray-300 line-clamp-3 col-span-1">{text}</p>
                            <div className="space-y-2 col-span-1">
                                <ShimmerBlock className="h-2 w-full" />
                                <ShimmerBlock className="h-2 w-5/6" />
                            </div>
                        </div>
                    ) : (
                        <>
                            <ShimmerBlock className="h-4 w-full" />
                            <ShimmerBlock className="h-4 w-5/6" />
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

// --- Default / Fallback ---
export const DefaultSkeleton = ({ text }: SkeletonProps) => {
    return (
        <div className="w-full h-full bg-gray-50 flex items-center justify-center p-12 space-x-8 animate-fade-in">
            <div className="flex-1 space-y-4">
                <ShimmerBlock className="h-10 w-3/4" />
                <ShimmerBlock className="h-4 w-full" />
                <ShimmerBlock className="h-4 w-5/6" />
                <ShimmerBlock className="h-4 w-4/6" />
            </div>
            <div className="w-1/3 aspect-square bg-gray-200 rounded animate-pulse" />
        </div>
    );
};

export const getSkeletonForLayout = (layoutId: string, text?: string | null) => {
    const textContent = text || undefined;
    switch (layoutId) {
        case 'title': return <TitleSkeleton text={textContent} />;
        case 'content_left': return <ContentLeftSkeleton text={textContent} />;
        case 'visual_center': return <VisualCenterSkeleton text={textContent} />;
        case 'split_horizontal': return <SplitHorizontalSkeleton text={textContent} />;
        default: return <DefaultSkeleton text={textContent} />;
    }
};
