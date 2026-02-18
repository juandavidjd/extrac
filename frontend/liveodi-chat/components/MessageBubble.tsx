"use client";

interface Props {
  role: "user" | "odi";
  text: string;
}

export default function MessageBubble({ role, text }: Props) {
  const isOdi = role === "odi";

  return (
    <div className={`flex ${isOdi ? "justify-start" : "justify-end"} mb-3`}>
      <div
        className={`max-w-[85%] sm:max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
          isOdi
            ? "bg-neutral-800/70 text-neutral-200 rounded-bl-sm"
            : "bg-emerald-600/20 text-neutral-200 border border-emerald-500/20 rounded-br-sm"
        }`}
      >
        {text}
      </div>
    </div>
  );
}
