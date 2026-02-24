"use client";
import { useRef, useEffect } from "react";

interface FlameProps {
  guardianColor: "verde" | "amarillo" | "rojo" | "negro";
  isThinking: boolean;
  isSpeaking: boolean;
  size?: number;
}

const COLORS: Record<string, { r: number; g: number; b: number }> = {
  verde: { r: 16, g: 185, b: 129 },
  amarillo: { r: 245, g: 158, b: 11 },
  rojo: { r: 239, g: 68, b: 68 },
  negro: { r: 107, g: 114, b: 128 },
};

export default function FlameIndicator({
  guardianColor,
  isThinking,
  isSpeaking,
  size = 48,
}: FlameProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = size;
    canvas.height = size;
    const center = size / 2;

    let animFrame: number;

    const draw = () => {
      frameRef.current++;
      const t = frameRef.current * 0.02;
      ctx.clearRect(0, 0, size, size);

      const color = COLORS[guardianColor] || COLORS.verde;

      let breathe = Math.sin(t * 0.8) * 0.15 + 0.85;

      if (isThinking) {
        breathe = Math.sin(t * 3) * 0.2 + 0.8;
      }

      if (isSpeaking) {
        breathe = Math.sin(t * 4) * 0.25 + 0.75;
      }

      const radius = center * 0.35 * breathe;

      // Glow exterior (aura)
      const glow = ctx.createRadialGradient(
        center,
        center,
        radius * 0.5,
        center,
        center,
        radius * 3
      );
      glow.addColorStop(
        0,
        `rgba(${color.r}, ${color.g}, ${color.b}, 0.15)`
      );
      glow.addColorStop(
        1,
        `rgba(${color.r}, ${color.g}, ${color.b}, 0)`
      );
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, size, size);

      // Nucleo
      const core = ctx.createRadialGradient(
        center,
        center,
        0,
        center,
        center,
        radius
      );
      core.addColorStop(
        0,
        `rgba(${color.r}, ${color.g}, ${color.b}, 0.9)`
      );
      core.addColorStop(
        0.6,
        `rgba(${color.r}, ${color.g}, ${color.b}, 0.4)`
      );
      core.addColorStop(
        1,
        `rgba(${color.r}, ${color.g}, ${color.b}, 0)`
      );

      ctx.beginPath();
      ctx.arc(center, center, radius, 0, Math.PI * 2);
      ctx.fillStyle = core;
      ctx.fill();

      animFrame = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animFrame);
  }, [guardianColor, isThinking, isSpeaking, size]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: size, height: size, imageRendering: "auto" }}
    />
  );
}
