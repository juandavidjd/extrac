import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ODI — Organismo Digital Industrial",
  description:
    "Repuestos de motos. 15 tiendas, 33,000+ productos. Precios reales. ODI no se usa, ODI se habita.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className="dark">
      <body
        className={`${inter.className} bg-[#0A0A0A] text-[#E8E8E8] antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
