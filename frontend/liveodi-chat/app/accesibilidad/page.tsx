"use client";

import { useAccessibility } from "@/lib/useAccessibility";
import Link from "next/link";

export default function AccesibilidadPage() {
  const { prefs, updatePref } = useAccessibility();

  const fontSizes = [
    { value: "small", label: "Pequeno" },
    { value: "normal", label: "Normal" },
    { value: "large", label: "Grande" },
    { value: "xlarge", label: "Muy grande" },
  ] as const;

  return (
    <main className="min-h-screen px-6 py-12 max-w-lg mx-auto">
      <Link
        href="/habitat"
        className="text-sm text-neutral-500 hover:text-neutral-300 mb-8 block"
      >
        &larr; Volver al habitat
      </Link>

      <h1 className="text-xl font-semibold text-neutral-100 mb-6">
        Accesibilidad
      </h1>

      <div className="space-y-6">
        {/* Font size */}
        <div>
          <label className="text-sm text-neutral-400 block mb-2">
            Tamano de texto
          </label>
          <div className="flex gap-2">
            {fontSizes.map((fs) => (
              <button
                key={fs.value}
                onClick={() => updatePref("fontSize", fs.value)}
                className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                  prefs.fontSize === fs.value
                    ? "bg-emerald-600 text-white"
                    : "bg-neutral-800 text-neutral-400 hover:text-neutral-200"
                }`}
              >
                {fs.label}
              </button>
            ))}
          </div>
        </div>

        {/* Toggles */}
        {[
          {
            key: "highContrast" as const,
            label: "Alto contraste",
            desc: "Colores mas definidos para mejor visibilidad",
          },
          {
            key: "textOnly" as const,
            label: "Solo texto",
            desc: "Desactiva audio y animaciones. Para personas sordas.",
          },
          {
            key: "simplified" as const,
            label: "Modo simplificado",
            desc: "Interfaz reducida. Oculta panel ecosistema y notificaciones.",
          },
        ].map((item) => (
          <div
            key={item.key}
            className="flex items-center justify-between bg-neutral-900 rounded-lg p-4"
          >
            <div>
              <div className="text-sm text-neutral-200">{item.label}</div>
              <div className="text-xs text-neutral-500 mt-0.5">
                {item.desc}
              </div>
            </div>
            <button
              onClick={() => updatePref(item.key, !prefs[item.key])}
              className={`w-10 h-6 rounded-full transition-colors relative ${
                prefs[item.key] ? "bg-emerald-600" : "bg-neutral-700"
              }`}
              role="switch"
              aria-checked={prefs[item.key]}
            >
              <span
                className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  prefs[item.key] ? "translate-x-5" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        ))}
      </div>
    </main>
  );
}
