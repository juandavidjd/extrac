"use client";

const colorMap: Record<string, string> = {
  verde: "border-emerald-500/30",
  amarillo: "border-amber-500/40",
  rojo: "border-red-500/50",
  negro: "border-red-900/60",
};

const glowMap: Record<string, string> = {
  verde: "shadow-emerald-500/10",
  amarillo: "shadow-amber-500/15",
  rojo: "shadow-red-500/20",
  negro: "shadow-red-900/30",
};

interface Props {
  color: string;
  children: React.ReactNode;
}

export default function GuardianAura({ color, children }: Props) {
  const borderClass = colorMap[color] || colorMap.verde;
  const glowClass = glowMap[color] || glowMap.verde;

  return (
    <div
      className={`flex flex-col h-screen border-t-2 transition-all duration-1000 ${borderClass} shadow-lg ${glowClass}`}
    >
      {children}
    </div>
  );
}
