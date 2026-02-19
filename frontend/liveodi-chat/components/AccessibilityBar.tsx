"use client";

import { useAccessibility } from "@/lib/useAccessibility";
import { useState } from "react";

export default function AccessibilityBar() {
  const { prefs, updatePref } = useAccessibility();
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-neutral-950 border-b border-neutral-800/30">
      <div className="flex items-center justify-end px-4">
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-neutral-600 hover:text-neutral-400 transition-colors py-1 text-xs flex items-center gap-1"
          aria-label="Accesibilidad"
        >
          <span aria-hidden="true">&#9855;</span>
          {expanded ? "Cerrar" : "Accesibilidad"}
        </button>
      </div>

      {expanded && (
        <div className="flex flex-wrap items-center gap-3 px-4 pb-2 text-xs">
          {/* Font size */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => updatePref("fontSize", "small")}
              className={`px-1.5 py-0.5 rounded ${prefs.fontSize === "small" ? "bg-neutral-700 text-white" : "text-neutral-500 hover:text-neutral-300"}`}
            >
              A-
            </button>
            <button
              onClick={() => updatePref("fontSize", "normal")}
              className={`px-1.5 py-0.5 rounded ${prefs.fontSize === "normal" ? "bg-neutral-700 text-white" : "text-neutral-500 hover:text-neutral-300"}`}
            >
              A
            </button>
            <button
              onClick={() => updatePref("fontSize", "large")}
              className={`px-1.5 py-0.5 rounded ${prefs.fontSize === "large" ? "bg-neutral-700 text-white" : "text-neutral-500 hover:text-neutral-300"}`}
            >
              A+
            </button>
          </div>

          <span className="text-neutral-800">|</span>

          {/* High contrast */}
          <button
            onClick={() => updatePref("highContrast", !prefs.highContrast)}
            className={`px-2 py-0.5 rounded ${prefs.highContrast ? "bg-amber-600 text-white" : "text-neutral-500 hover:text-neutral-300"}`}
          >
            Contraste
          </button>

          {/* Text only */}
          <button
            onClick={() => updatePref("textOnly", !prefs.textOnly)}
            className={`px-2 py-0.5 rounded ${prefs.textOnly ? "bg-blue-600 text-white" : "text-neutral-500 hover:text-neutral-300"}`}
          >
            Solo texto
          </button>

          {/* Simplified */}
          <button
            onClick={() => updatePref("simplified", !prefs.simplified)}
            className={`px-2 py-0.5 rounded ${prefs.simplified ? "bg-purple-600 text-white" : "text-neutral-500 hover:text-neutral-300"}`}
          >
            Simplificado
          </button>
        </div>
      )}
    </div>
  );
}
