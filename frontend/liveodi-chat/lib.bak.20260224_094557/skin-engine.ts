/**
 * ODI Skin Engine v19
 * "ODI no se usa. ODI se habita."
 *
 * Sistema de pieles que transforma el hábitat según contexto.
 * Detecta industria por dominio, mensaje o respuesta del backend.
 * Transiciona colores suavemente con CSS custom properties.
 */

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

export interface SkinColors {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  text: string;
  textMuted: string;
}

export interface IndustrySkin {
  id: string;
  name: string;
  domain: string | null;
  colors: SkinColors;
  voice: "tony" | "ramona";
  greeting: string;
  keywords: string[];
}

export interface CompanyIdentity {
  name: string;
  logo: string | null;
  colors: { primary: string; accent: string };
}

// ---------------------------------------------------------------------------
// Skins — 4 industrias + default
// ---------------------------------------------------------------------------

const DEFAULT_SKIN: IndustrySkin = {
  id: "default",
  name: "ODI",
  domain: null,
  colors: {
    primary: "#d4a017",
    secondary: "#1a1a1a",
    accent: "#e6b800",
    background: "#0a0a0a",
    text: "#e0e0e0",
    textMuted: "#888888",
  },
  voice: "ramona",
  greeting: "Bienvenido a ODI. Industria, salud, lo que necesites. Solo háblame.",
  keywords: [],
};

const SKINS: Record<string, IndustrySkin> = {
  motos: {
    id: "motos",
    name: "Somos Repuestos Motos",
    domain: "somosrepuestosmotos.com",
    colors: {
      primary: "#3a7bd5",
      secondary: "#1e2a3a",
      accent: "#5a9bf5",
      background: "#0d1117",
      text: "#c9d1d9",
      textMuted: "#7d8590",
    },
    voice: "tony",
    greeting: "Repuestos de motos. Marca, modelo y qué necesitas.",
    keywords: [
      "filtro", "bomba", "kit", "banda", "pastilla", "cadena",
      "aceite", "freno", "moto", "pulsar", "bajaj", "yamaha",
      "honda", "suzuki", "akt", "tvs", "hero", "repuesto",
      "pieza", "empaque", "tensor", "disco", "clutch", "embrague",
      "rodamiento", "retenedor", "corona", "llanta", "rin",
      "manigueta", "cable", "bws", "nmax", "fz", "duke",
      "dominar", "boxer", "discover", "splendor",
    ],
  },

  salud_dental: {
    id: "salud_dental",
    name: "Matzu Dental Aesthetics",
    domain: "matzudentalaesthetics.com",
    colors: {
      primary: "#0ea5a5",
      secondary: "#f0f9f9",
      accent: "#14b8a6",
      background: "#0c1a1a",
      text: "#d0e8e8",
      textMuted: "#7aa3a3",
    },
    voice: "ramona",
    greeting: "Salud dental con estética. Cuéntame qué necesitas.",
    keywords: [
      "dental", "diente", "dientes", "muela", "implante", "ortodoncia",
      "blanqueamiento", "sonrisa", "endodoncia", "periodoncia",
      "matzu", "odontolog",
    ],
  },

  salud_bruxismo: {
    id: "salud_bruxismo",
    name: "Cover's Lab",
    domain: "mis-cubiertas.com",
    colors: {
      primary: "#8b5cf6",
      secondary: "#1a1528",
      accent: "#a78bfa",
      background: "#0d0b14",
      text: "#d4c8ef",
      textMuted: "#8070a0",
    },
    voice: "ramona",
    greeting: "Protección dental nocturna. Cuéntame sobre tu bruxismo.",
    keywords: [
      "bruxismo", "cubierta", "protector nocturno", "smokover",
      "rechinar", "cover", "guarda oclusal", "ferula",
    ],
  },

  salud_capilar: {
    id: "salud_capilar",
    name: "Cabezas Sanas",
    domain: "cabezasanas.com",
    colors: {
      primary: "#22c55e",
      secondary: "#0f2918",
      accent: "#4ade80",
      background: "#0a120d",
      text: "#c8e6d0",
      textMuted: "#6a9a76",
    },
    voice: "ramona",
    greeting: "Tratamiento capilar profesional. Cuéntame tu caso.",
    keywords: [
      "capilar", "cabello", "calvicie", "pelo", "alopecia",
      "tratamiento capilar", "cabeza sana", "cabezas sanas",
      "injerto capilar", "minoxidil",
    ],
  },
};

// ---------------------------------------------------------------------------
// Domain map (includes www variants)
// ---------------------------------------------------------------------------

const DOMAIN_MAP: Record<string, string> = {};
for (const [id, skin] of Object.entries(SKINS)) {
  if (skin.domain) {
    DOMAIN_MAP[skin.domain] = id;
    DOMAIN_MAP[`www.${skin.domain}`] = id;
  }
}

// ---------------------------------------------------------------------------
// Detection functions
// ---------------------------------------------------------------------------

/** Detecta piel por dominio del navegador. */
export function detectSkinByDomain(hostname: string): IndustrySkin | null {
  const h = hostname.toLowerCase().replace(/:\d+$/, "");
  const id = DOMAIN_MAP[h];
  return id ? SKINS[id] : null;
}

/** Detecta piel por keywords en el mensaje del usuario. */
export function detectSkinByMessage(message: string): IndustrySkin | null {
  const msg = message.toLowerCase();
  for (const skin of Object.values(SKINS)) {
    if (skin.keywords.some((kw) => msg.includes(kw))) {
      return skin;
    }
  }
  return null;
}

/** Detecta piel por el campo industry del response del backend. */
export function detectSkinFromResponse(industry: string): IndustrySkin {
  return SKINS[industry] ?? DEFAULT_SKIN;
}

/** Retorna la piel por defecto (liveodi.com — negro + llama dorada). */
export function getDefaultSkin(): IndustrySkin {
  return DEFAULT_SKIN;
}

/** Retorna una piel por su ID. */
export function getSkin(id: string): IndustrySkin {
  return SKINS[id] ?? DEFAULT_SKIN;
}

/** Retorna todas las pieles disponibles. */
export function getAllSkins(): IndustrySkin[] {
  return Object.values(SKINS);
}

// ---------------------------------------------------------------------------
// CSS custom properties — transiciones suaves
// ---------------------------------------------------------------------------

const CSS_VARS = [
  ["--skin-primary", "primary"],
  ["--skin-secondary", "secondary"],
  ["--skin-accent", "accent"],
  ["--skin-bg", "background"],
  ["--skin-text", "text"],
  ["--skin-text-muted", "textMuted"],
] as const;

/** Aplica los colores de una piel al document root con transición CSS. */
export function applySkin(skin: IndustrySkin): void {
  if (typeof document === "undefined") return;

  const root = document.documentElement;
  for (const [cssVar, colorKey] of CSS_VARS) {
    root.style.setProperty(cssVar, skin.colors[colorKey]);
  }

  root.setAttribute("data-skin", skin.id);
  root.classList.add("skin-transitioning");
  setTimeout(() => root.classList.remove("skin-transitioning"), 800);
}

/** Aplica identidad de empresa (colores de la empresa sobre la piel). */
export function applyCompanyAccent(company: CompanyIdentity | null): void {
  if (typeof document === "undefined" || !company) return;

  const root = document.documentElement;
  root.style.setProperty("--company-primary", company.colors.primary);
  root.style.setProperty("--company-accent", company.colors.accent);
  root.setAttribute("data-company", company.name);
}

/** Reset a la piel default. */
export function resetSkin(): void {
  applySkin(DEFAULT_SKIN);
  if (typeof document === "undefined") return;
  document.documentElement.removeAttribute("data-company");
  document.documentElement.style.removeProperty("--company-primary");
  document.documentElement.style.removeProperty("--company-accent");
}

// ---------------------------------------------------------------------------
// CSS base — inyectar en el <head> una sola vez
// ---------------------------------------------------------------------------

export const SKIN_CSS = `
:root {
  --skin-primary: ${DEFAULT_SKIN.colors.primary};
  --skin-secondary: ${DEFAULT_SKIN.colors.secondary};
  --skin-accent: ${DEFAULT_SKIN.colors.accent};
  --skin-bg: ${DEFAULT_SKIN.colors.background};
  --skin-text: ${DEFAULT_SKIN.colors.text};
  --skin-text-muted: ${DEFAULT_SKIN.colors.textMuted};
  --skin-transition: 0.8s ease;
}

body {
  background-color: var(--skin-bg);
  color: var(--skin-text);
  transition:
    background-color var(--skin-transition),
    color var(--skin-transition);
}

.skin-transitioning * {
  transition:
    background-color var(--skin-transition),
    color var(--skin-transition),
    border-color var(--skin-transition) !important;
}
`;
