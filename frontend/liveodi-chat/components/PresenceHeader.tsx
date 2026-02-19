"use client";

import FlameIndicator from "./FlameIndicator";

interface Props {
  guardianState: string;
  isConnected: boolean;
  isThinking: boolean;
  isSpeaking: boolean;
  muted: boolean;
  onToggleMute: () => void;
  onToggleEcosystem: () => void;
  totalStores: number;
  totalProducts: number;
}

export default function PresenceHeader({
  guardianState,
  isConnected,
  isThinking,
  isSpeaking,
  muted,
  onToggleMute,
  onToggleEcosystem,
  totalStores,
  totalProducts,
}: Props) {
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-800/50">
      <div className="flex items-center gap-3">
        <FlameIndicator
          guardianColor={guardianState as any}
          isThinking={isThinking}
          isSpeaking={isSpeaking}
          size={32}
        />
        <span className="text-sm font-medium text-neutral-300 tracking-wide">
          ODI
        </span>
        {/* Guardian dot */}
        <span
          className={`w-2 h-2 rounded-full ${
            guardianState === "verde"
              ? "bg-emerald-500"
              : guardianState === "amarillo"
                ? "bg-amber-500"
                : guardianState === "naranja"
                  ? "bg-orange-500"
                  : guardianState === "rojo"
                    ? "bg-red-500"
                    : "bg-neutral-500"
          }`}
          title={`Guardian: ${guardianState}`}
        />
        {/* WebSocket dot */}
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            isConnected ? "bg-emerald-400" : "bg-neutral-600"
          }`}
          title={isConnected ? "Conectado" : "Desconectado"}
        />
      </div>

      <div className="flex items-center gap-3">
        {/* Stats micro */}
        <span className="text-xs text-neutral-600 hidden sm:inline">
          {totalStores} tiendas &middot;{" "}
          {totalProducts.toLocaleString("es-CO")} productos
        </span>

        {/* Mute toggle */}
        <button
          onClick={onToggleMute}
          className="text-neutral-500 hover:text-neutral-300 transition-colors"
          aria-label={muted ? "Activar voz" : "Silenciar voz"}
        >
          {muted ? (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-4 h-4"
            >
              <path d="M9.547 3.062A.75.75 0 0110 3.75v12.5a.75.75 0 01-1.264.546L5.203 13.5H2.667a.75.75 0 01-.7-.48A6.985 6.985 0 011.5 10c0-.972.198-1.899.467-3.02a.75.75 0 01.7-.48h2.536l3.533-3.296a.75.75 0 01.811-.142zM13.28 7.22a.75.75 0 10-1.06 1.06L13.94 10l-1.72 1.72a.75.75 0 001.06 1.06L15 11.06l1.72 1.72a.75.75 0 001.06-1.06L16.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L15 8.94l-1.72-1.72z" />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-4 h-4"
            >
              <path d="M10 3.75a.75.75 0 00-1.264-.546L5.203 6.5H2.667a.75.75 0 00-.7.48 6.985 6.985 0 000 6.04.75.75 0 00.7.48h2.536l3.533 3.296A.75.75 0 0010 16.25V3.75zM15.95 5.05a.75.75 0 00-1.06 1.061 5.5 5.5 0 010 7.778.75.75 0 001.06 1.06 7 7 0 000-9.899z" />
              <path d="M13.829 7.172a.75.75 0 00-1.061 1.06 2.5 2.5 0 010 3.536.75.75 0 001.06 1.06 4 4 0 000-5.656z" />
            </svg>
          )}
        </button>

        {/* Ecosystem toggle */}
        <button
          onClick={onToggleEcosystem}
          className="text-neutral-500 hover:text-neutral-300 transition-colors"
          aria-label="Ecosistema"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-4 h-4"
          >
            <path
              fillRule="evenodd"
              d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zm0 10.5a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75zM2 10a.75.75 0 01.75-.75h7.5a.75.75 0 010 1.5h-7.5A.75.75 0 012 10z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
