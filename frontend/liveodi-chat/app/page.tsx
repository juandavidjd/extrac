"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchEcosystemStats } from "@/lib/odi-gateway";
import type { EcosystemStats } from "@/lib/odi-gateway";

export default function LandingPage() {
  const router = useRouter();
  const [stats, setStats] = useState<EcosystemStats | null>(null);

  useEffect(() => { fetchEcosystemStats().then(setStats); }, []);

  const statusText = stats
    ? `${stats.activeStores} tiendas · ${stats.products.toLocaleString("es-CO")} productos · vivo`
    : "vivo";

  return (
    <main className="min-h-screen bg-[#03070d] text-[#dbe7ff] flex flex-col items-center justify-center font-sans">
      <button
        onClick={() => router.push("/habitat")}
        className="w-40 h-40 rounded-full bg-transparent border-none cursor-pointer mb-5"
        aria-label="Entrar a ODI"
      >
        <span
          className="block w-full h-full rounded-full animate-[breathe_4s_ease-in-out_infinite]"
          style={{
            background: "radial-gradient(circle at 50% 35%, #9be2ff 0%, #49c2ff 32%, #6f6dff 65%, rgba(111,109,255,0.1) 82%, transparent 100%)",
            boxShadow: "0 0 38px #4ab8ffaa, inset 0 0 35px #b8d8ff70",
          }}
        />
      </button>
      <h1 className="text-3xl md:text-4xl font-bold m-0">Soy ODI.</h1>
      <p className="text-sm text-[#b6e5ff] mt-3 opacity-90">{statusText}</p>
    </main>
  );
}
