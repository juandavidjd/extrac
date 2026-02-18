import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ODI — Organismo Digital Industrial",
  description:
    "Repuestos de motos. 16,681 productos, 15 proveedores, 43 marcas. Precios reales.",
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
