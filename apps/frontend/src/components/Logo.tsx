import React from 'react';

export const Logo: React.FC<{ className?: string }> = ({ className = "w-8 h-8" }) => {
    return (
        <svg
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className={className}
        >
            <rect width="32" height="32" rx="8" fill="currentColor"/>
            <text
                x="16"
                y="22"
                fontFamily="Inter, system-ui, sans-serif"
                fontWeight="900"
                fontSize="20"
                fill="white"
                textAnchor="middle"
            >
                S
            </text>
            <path
                d="M22 8L24 10L22 12"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
        </svg>
    );
};
