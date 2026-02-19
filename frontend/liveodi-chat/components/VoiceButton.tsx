"use client";

interface Props {
  isListening: boolean;
  isSupported: boolean;
  onToggle: () => void;
}

export default function VoiceButton({
  isListening,
  isSupported,
  onToggle,
}: Props) {
  if (!isSupported) return null;

  return (
    <button
      onClick={onToggle}
      className={`p-3 rounded-xl transition-all ${
        isListening
          ? "bg-red-600 text-white animate-pulse"
          : "bg-neutral-800 text-neutral-400 hover:text-neutral-200 hover:bg-neutral-700"
      }`}
      aria-label={isListening ? "Dejar de escuchar" : "Hablar con ODI"}
      title={isListening ? "Dejar de escuchar (Ctrl+M)" : "Hablar (Ctrl+M)"}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="currentColor"
        className="w-5 h-5"
      >
        {isListening ? (
          <path d="M8.25 4.5a3.75 3.75 0 117.5 0v8.25a3.75 3.75 0 11-7.5 0V4.5z" />
        ) : (
          <>
            <path d="M8.25 4.5a3.75 3.75 0 117.5 0v8.25a3.75 3.75 0 11-7.5 0V4.5z" />
            <path d="M6 10.5a.75.75 0 01.75.75 5.25 5.25 0 1010.5 0 .75.75 0 011.5 0 6.75 6.75 0 01-6 6.709v2.291h3a.75.75 0 010 1.5h-7.5a.75.75 0 010-1.5h3v-2.291a6.75 6.75 0 01-6-6.709.75.75 0 01.75-.75z" />
          </>
        )}
      </svg>
      {isListening && (
        <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-ping" />
      )}
    </button>
  );
}
