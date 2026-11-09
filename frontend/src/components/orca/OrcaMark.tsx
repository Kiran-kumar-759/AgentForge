/** Minimal ORCA mark: a contour ring with a single depth line. */
export function OrcaMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden fill="none">
      <rect x="1" y="1" width="22" height="22" rx="6" className="fill-foreground" />
      <circle cx="12" cy="12" r="5.5" className="stroke-background" strokeWidth="1.6" />
      <path d="M6.5 12.6c1.8-1.2 3.6-1.2 5.5 0s3.7 1.2 5.5 0" className="stroke-background" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
