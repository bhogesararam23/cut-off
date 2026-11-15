export function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden="true" className={`rounded-card bg-ink/10 ${className}`} />;
}
