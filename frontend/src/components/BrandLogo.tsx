import React from "react";

interface BrandLogoProps {
  size?: number;
  variant?: "forest" | "emerald";
  className?: string;
}

export function BrandLogo({ size = 36, variant = "emerald", className = "" }: BrandLogoProps) {
  const bg = variant === "emerald" ? "#168A57" : "#0B2A22";
  const border = variant === "emerald" ? "rgba(255,255,255,0.14)" : "rgba(22,138,87,0.45)";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${className}`}
      aria-label="Campaign Intelligence logo"
    >
      <rect x="1.5" y="1.5" width="97" height="97" rx="23" fill={bg} stroke={border} strokeWidth="3" />
      <path
        d="M 67.46 34.28 A 23.5 23.5 0 1 0 67.46 65.72"
        stroke="#F7F6F0"
        strokeWidth="12.5"
        strokeLinecap="round"
      />
      <circle cx="50" cy="50" r="7.5" fill="#E9A22E" />
    </svg>
  );
}
