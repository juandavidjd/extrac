"use client";
import { useState, useEffect } from "react";

interface AccessibilityPrefs {
  fontSize: "small" | "normal" | "large" | "xlarge";
  highContrast: boolean;
  voiceOnly: boolean;
  textOnly: boolean;
  simplified: boolean;
  reduceMotion: boolean;
}

const DEFAULTS: AccessibilityPrefs = {
  fontSize: "normal",
  highContrast: false,
  voiceOnly: false,
  textOnly: false,
  simplified: false,
  reduceMotion: false,
};

export function useAccessibility() {
  const [prefs, setPrefs] = useState<AccessibilityPrefs>(DEFAULTS);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    const prefersHighContrast = window.matchMedia(
      "(prefers-contrast: more)"
    ).matches;

    const saved = localStorage.getItem("odi-accessibility");
    if (saved) {
      setPrefs({
        ...JSON.parse(saved),
        reduceMotion: prefersReducedMotion,
      });
    } else {
      setPrefs((prev) => ({
        ...prev,
        reduceMotion: prefersReducedMotion,
        highContrast: prefersHighContrast,
      }));
    }
  }, []);

  useEffect(() => {
    const classes: string[] = [];
    if (prefs.highContrast) classes.push("high-contrast");
    if (prefs.reduceMotion) classes.push("reduce-motion");
    if (prefs.simplified) classes.push("simplified");
    classes.push(`font-${prefs.fontSize}`);

    document.body.className = document.body.className
      .replace(
        /\b(high-contrast|reduce-motion|simplified|font-(small|normal|large|xlarge))\b/g,
        ""
      )
      .trim();
    document.body.classList.add(...classes);

    localStorage.setItem("odi-accessibility", JSON.stringify(prefs));
  }, [prefs]);

  const updatePref = (key: keyof AccessibilityPrefs, value: any) => {
    setPrefs((prev) => ({ ...prev, [key]: value }));
  };

  return { prefs, updatePref };
}
