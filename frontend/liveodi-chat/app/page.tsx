import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen px-6 text-center">
      <div className="flex flex-col items-center gap-8 max-w-md">
        {/* Pulso vital */}
        <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />

        {/* Identidad */}
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-100">
            ODI
          </h1>
          <p className="text-sm text-neutral-500 mt-1">
            Organismo Digital Industrial
          </p>
        </div>

        {/* Datos duros */}
        <div className="text-sm text-neutral-400 space-y-1">
          <p>16,681 productos &middot; 15 proveedores</p>
          <p>43 marcas de motos &middot; precios reales</p>
        </div>

        {/* CTA */}
        <Link
          href="/chat"
          className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-xl transition-colors"
        >
          Empezar conversacion
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-4 h-4"
          >
            <path
              fillRule="evenodd"
              d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z"
              clipRule="evenodd"
            />
          </svg>
        </Link>

        {/* Mantra */}
        <p className="text-xs text-neutral-600 italic">
          &ldquo;ODI no se usa. ODI se habita.&rdquo;
        </p>
      </div>
    </main>
  );
}
