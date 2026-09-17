import { useEffect, useRef, useState } from 'react';
import type { TelemetryMessage } from '../types';

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws/telemetry';

export type ConnectionState = 'connecting' | 'open' | 'closed';

interface TelemetryStream {
  message: TelemetryMessage | null;
  connection: ConnectionState;
}

/**
 * Owns the WebSocket connection to the backend telemetry stream and
 * reconnects with backoff if the backend restarts. This is the *only*
 * place live navigation data enters the React tree — every panel reads
 * from the message this hook returns rather than opening its own socket.
 */
export function useTelemetryStream(): TelemetryStream {
  const [message, setMessage] = useState<TelemetryMessage | null>(null);
  const [connection, setConnection] = useState<ConnectionState>('connecting');
  const retryDelay = useRef(1000);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    function connect() {
      setConnection('connecting');
      socket = new WebSocket(WS_URL);

      socket.onopen = () => {
        retryDelay.current = 1000;
        setConnection('open');
      };

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as TelemetryMessage;
          setMessage(parsed);
        } catch {
          // Malformed frame — drop it, keep the connection alive.
        }
      };

      socket.onclose = () => {
        setConnection('closed');
        if (!cancelled) {
          retryTimer = setTimeout(connect, retryDelay.current);
          retryDelay.current = Math.min(retryDelay.current * 1.5, 10000);
        }
      };

      socket.onerror = () => {
        socket?.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  return { message, connection };
}
