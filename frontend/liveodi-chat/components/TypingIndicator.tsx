"use client";

export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className="flex items-center gap-1">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-[pulse_1.4s_ease-in-out_infinite]" />
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-[pulse_1.4s_ease-in-out_0.2s_infinite]" />
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-[pulse_1.4s_ease-in-out_0.4s_infinite]" />
      </div>
      <span className="text-sm text-neutral-500">ODI procesando...</span>
    </div>
  );
}
