"use client";
import { useRef, useEffect } from "react";

interface Props {
  guardianColor: "verde" | "amarillo" | "rojo" | "negro";
  isThinking: boolean;
  isSpeaking: boolean;
}

const COLORS: Record<string, { r: number; g: number; b: number }> = {
  verde: { r: 16, g: 185, b: 129 },
  amarillo: { r: 245, g: 158, b: 11 },
  rojo: { r: 239, g: 68, b: 68 },
  negro: { r: 107, g: 114, b: 128 },
};

export default function FlameCenter({ guardianColor, isThinking, isSpeaking }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const size = 200;
    const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = size + "px";
    canvas.style.height = size + "px";
    ctx.scale(dpr, dpr);

    const center = size / 2;
    let animFrame: number;

    const draw = () => {
      frameRef.current++;
      const t = frameRef.current * 0.015;
      ctx.clearRect(0, 0, size, size);

      const color = COLORS[guardianColor] || COLORS.verde;

      let breathe: number;
      if (isThinking) {
        breathe = Math.sin(t * 3) * 0.2 + 0.8;
      } else if (isSpeaking) {
        breathe = Math.sin(t * 4) * 0.25 + 0.75 + Math.sin(t * 7) * 0.08;
      } else {
        breathe = Math.sin(t * 0.6) * 0.12 + 0.88;
      }

      const baseRadius = 28 * breathe;

      // Outer aura
      const aura = ctx.createRadialGradient(center, center, baseRadius, center, center, baseRadius * 3.5);
      aura.addColorStop(0, "rgba(" + color.r + "," + color.g + "," + color.b + ",0.06)");
      aura.addColorStop(1, "rgba(" + color.r + "," + color.g + "," + color.b + ",0)");
      ctx.fillStyle = aura;
      ctx.fillRect(0, 0, size, size);

      // Mid glow
      const mid = ctx.createRadialGradient(center, center, baseRadius * 0.3, center, center, baseRadius * 2);
      mid.addColorStop(0, "rgba(" + color.r + "," + color.g + "," + color.b + ",0.12)");
      mid.addColorStop(0.5, "rgba(" + color.r + "," + color.g + "," + color.b + ",0.04)");
      mid.addColorStop(1, "rgba(" + color.r + "," + color.g + "," + color.b + ",0)");
      ctx.fillStyle = mid;
      ctx.beginPath();
      ctx.arc(center, center, baseRadius * 2, 0, Math.PI * 2);
      ctx.fill();

      // Core
      const core = ctx.createRadialGradient(center, center, 0, center, center, baseRadius);
      core.addColorStop(0, "rgba(" + color.r + "," + color.g + "," + color.b + ",0.95)");
      core.addColorStop(0.4, "rgba(" + color.r + "," + color.g + "," + color.b + ",0.5)");
      core.addColorStop(0.8, "rgba(" + color.r + "," + color.g + "," + color.b + ",0.15)");
      core.addColorStop(1, "rgba(" + color.r + "," + color.g + "," + color.b + ",0)");
      ctx.fillStyle = core;
      ctx.beginPath();
      ctx.arc(center, center, baseRadius, 0, Math.PI * 2);
      ctx.fill();

      // White-hot center
      const hot = ctx.createRadialGradient(center, center, 0, center, center, baseRadius * 0.3);
      hot.addColorStop(0, "rgba(255,255,255,0.4)");
      hot.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = hot;
      ctx.beginPath();
      ctx.arc(center, center, baseRadius * 0.3, 0, Math.PI * 2);
      ctx.fill();

      animFrame = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animFrame);
  }, [guardianColor, isThinking, isSpeaking]);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none"
      style={{ width: 200, height: 200 }}
    />
  );
}
