"use client";

const GATEWAY_API = process.env.NEXT_PUBLIC_ODI_GATEWAY || "https://api.liveodi.com/odi/v1";
const CHAT_API = process.env.NEXT_PUBLIC_ODI_CHAT || "https://api.liveodi.com";
const SPEAK_API = process.env.NEXT_PUBLIC_ODI_SPEAK || "https://api.liveodi.com/odi/chat/speak";

const GOVERNED_STORES = new Set([
  "DFG", "ARMOTOS", "VITTON", "IMBRA", "BARA", "KAIQI", "MCLMOTOS"
]);

export interface EcosystemStats {
  activeStores: number;
  products: number;
}

export interface ChatProduct {
  sku: string;
  title: string;
  price: number | null;
  image: string;
  url: string;
  store: string;
}

export interface ChatResult {
  response: string;
  narrative: string;
  voice: string;
  sessionId: string;
  products: ChatProduct[];
}

function parseStoreName(store: Record<string, unknown>): string {
  return String(store?.name || store?.store || store?.code || "").toUpperCase();
}

function countProducts(store: Record<string, unknown>): number {
  return Number(store?.products_count ?? store?.active ?? store?.total ?? 0);
}

function parsePrice(value: unknown): number | null {
  if (value == null || value === "") return null;
  const normalized = Number(
    String(value).replace(/[^\d.,-]/g, "").replace(/\./g, "").replace(",", ".")
  );
  return Number.isFinite(normalized) ? normalized : null;
}

function normalizeProducts(data: Record<string, unknown>): ChatProduct[] {
  const raw = (data?.productos || data?.products || data?.product_list || []) as Record<string, unknown>[];
  if (!Array.isArray(raw)) return [];

  return raw
    .map((item) => ({
      sku: String(item?.sku || item?.code || item?.codigo || item?.id_producto || ""),
      title: String(item?.title || item?.name || item?.nombre || "Producto"),
      price: parsePrice(item?.price ?? item?.precio ?? item?.precio_venta),
      image: String(item?.image || item?.imagen || item?.thumbnail || ""),
      url: String(item?.url || item?.link || item?.permalink || ""),
      store: String(item?.store || item?.tienda || item?.proveedor || ""),
    }))
    .filter((item) => item.title || item.sku || item.url);
}

export async function fetchEcosystemStats(): Promise<EcosystemStats | null> {
  try {
    const res = await fetch(`${GATEWAY_API}/ecosystem/stores`, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;

    const data = await res.json();
    const stores: Record<string, unknown>[] = Array.isArray(data)
      ? data
      : data?.stores || data?.data || [];

    const governedActive = stores.filter((store) => {
      const name = parseStoreName(store);
      const products = countProducts(store);
      return GOVERNED_STORES.has(name) && products > 0;
    });

    const target = governedActive.length > 0
      ? governedActive
      : stores.filter((store) => countProducts(store) > 0);

    return target.reduce<EcosystemStats>(
      (acc, store) => ({
        activeStores: acc.activeStores + 1,
        products: acc.products + countProducts(store),
      }),
      { activeStores: 0, products: 0 }
    );
  } catch {
    return null;
  }
}

export async function sendChatMessage(
  message: string,
  sessionId: string
): Promise<ChatResult | null> {
  const payload = { message, session_id: sessionId };
  const candidates = [`${CHAT_API}/odi/chat`, `${GATEWAY_API}/chat`];

  for (const url of candidates) {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) continue;
      const data = await res.json();

      return {
        response: data.response || data.message || data.narrative || "",
        narrative: data.narrative || data.response || data.message || "",
        voice: data.voice || "ramona",
        sessionId: data.session_id || sessionId,
        products: normalizeProducts(data),
      };
    } catch {
      continue;
    }
  }
  return null;
}

export async function speakText(text: string, voice: string = "ramona"): Promise<boolean> {
  if (!text) return false;
  try {
    const res = await fetch(SPEAK_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice }),
    });
    if (!res.ok) return false;

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);
    audio.onerror = () => URL.revokeObjectURL(url);
    await audio.play();
    return true;
  } catch {
    return false;
  }
}
