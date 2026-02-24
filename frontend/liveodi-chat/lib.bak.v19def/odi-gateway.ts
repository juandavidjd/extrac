const API =
  process.env.NEXT_PUBLIC_ODI_API || "https://api.liveodi.com/odi/v1";

async function gw<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export const gateway = {
  health: () => gw<any>("/health"),

  searchProducts: (q: string, limit = 20, store?: string) => {
    const params = new URLSearchParams({ q, limit: String(limit) });
    if (store) params.set("store", store);
    return gw<any>(`/products/search?${params}`);
  },

  getEcosystem: () => gw<any>("/ecosystem/stores"),

  getStoreSummary: (id: string) => gw<any>(`/stores/${id}/summary`),

  getProduct360: (sku: string) => gw<any>(`/products/${sku}/360`),

  searchFitment: (params: Record<string, string>) => {
    const sp = new URLSearchParams(params);
    return gw<any>(`/fitment/search?${sp}`);
  },

  chat: (message: string, session_id?: string) =>
    gw<any>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id }),
    }),
};
