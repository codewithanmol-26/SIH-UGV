import type { ReactNode } from 'react';

export function Panel({ title, children, className = '' }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section className={`bg-panel border border-panel-line rounded-sm p-4 ${className}`}>
      <h2 className="font-mono text-[11px] tracking-wide text-text-dim font-medium pb-2.5 mb-3 border-b border-panel-line">
        {title}
      </h2>
      {children}
    </section>
  );
}

type DotTone = 'ok' | 'warn' | 'down';

const DOT_COLOR: Record<DotTone, string> = {
  ok: 'bg-sage shadow-[0_0_7px_var(--color-sage)]',
  warn: 'bg-amber shadow-[0_0_7px_var(--color-amber)]',
  down: 'bg-rust shadow-[0_0_7px_var(--color-rust)]',
};

export function StatusDot({ tone, pulse = false }: { tone: DotTone; pulse?: boolean }) {
  return <span className={`inline-block w-2 h-2 rounded-full flex-none ${DOT_COLOR[tone]} ${pulse ? 'pulse' : ''}`} />;
}
