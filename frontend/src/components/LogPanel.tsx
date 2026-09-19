import { Panel } from './Primitives';
import type { LogEntry } from '../types';

const KIND_COLOR: Record<LogEntry['kind'], string> = {
  '': 'text-text-dim',
  good: 'text-sage-dim',
  flag: 'text-rust',
};

export function LogPanel({ logs }: { logs: LogEntry[] }) {
  return (
    <Panel title="EVENT LOG">
      <div className="flex flex-col gap-2 max-h-56 overflow-y-auto">
        {logs.length === 0 && <p className="font-mono text-[11px] text-text-dim">No events yet.</p>}
        {logs.map((entry, i) => (
          <div key={`${entry.t}-${i}`} className={`font-mono text-[11px] leading-relaxed flex gap-2 ${entry.kind === 'flag' ? 'text-rust' : 'text-text-dim'}`}>
            <span className={KIND_COLOR[entry.kind]}>{entry.t}</span>
            <span>{entry.text}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}
