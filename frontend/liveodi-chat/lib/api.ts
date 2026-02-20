const API_URL = process.env.NEXT_PUBLIC_ODI_API_URL || "https://api.liveodi.com";

export interface ChatResponse {
  response: string;
  session_id: string;
  guardian_color: string;
  productos_encontrados: number;
  productos: Array<{
    codigo: string;
    nombre: string;
    precio_cop: number;
    proveedor: string;
    imagen_url?: string;
    shopify_url?: string;
    fitment?: string[];
    disponible?: boolean;
    categoria?: string;
  }>;
  nivel_intimidad: number;
  modo: string;
  voice: string;
  audio_enabled: boolean;
}

export async function sendMessage(
  message: string,
  sessionId?: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/odi/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId || undefined,
    }),
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return res.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/odi/chat/health`);
    const data = await res.json();
    return data.ok === true;
  } catch {
    return false;
  }
}
