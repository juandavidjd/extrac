import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Truck,
  Heart,
  Sparkles,
  Globe,
  ChevronRight,
  Phone,
  Mail,
  MapPin,
  ExternalLink
} from 'lucide-react'

// ═══════════════════════════════════════════════════════════════════════════════
// CATRMU — Canal Transversal Multitemático
// "Una lógica, infinitas industrias"
//
// REFINEMENT: Visual hierarchy, mobile responsive, institutional feel
// ═══════════════════════════════════════════════════════════════════════════════

// Industry configuration (from industry_skins.py)
interface IndustryCard {
  id: string
  name: string
  description: string
  domain: string
  icon: React.ReactNode
  color: string
  branches: string[]
  isActive: boolean
}

const INDUSTRIES: IndustryCard[] = [
  {
    id: 'transporte',
    name: 'Transporte',
    description: 'Repuestos y accesorios para motocicletas',
    domain: 'somosrepuestosmotos.com',
    icon: <Truck className="w-6 h-6" />,
    color: '#06B6D4',
    branches: ['Motos', 'Repuestos', 'Accesorios'],
    isActive: true,
  },
  {
    id: 'salud',
    name: 'Salud',
    description: 'Turismo dental, bruxismo y tricología',
    domain: 'matzudentalaesthetics.com',
    icon: <Heart className="w-6 h-6" />,
    color: '#14B8A6',
    branches: ['Dental', 'Bruxismo', 'Capilar'],
    isActive: true,
  },
  {
    id: 'entretenimiento',
    name: 'Entretenimiento',
    description: 'Turismo y experiencias',
    domain: 'En construcción',
    icon: <Sparkles className="w-6 h-6" />,
    color: '#EC4899',
    branches: ['Turismo', 'Eventos'],
    isActive: false,
  },
]

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTE: Header institucional
// REFINEMENT: Clean, balanced, professional
// ═══════════════════════════════════════════════════════════════════════════════

function Header() {
  return (
    <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-sm">
      <div className="max-w-6xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: '#EC489920', border: '1px solid #EC489940' }}
            >
              <Globe className="w-5 h-5 text-pink-400" />
            </div>
            <div>
              <div className="text-lg font-semibold text-white tracking-tight">CATRMU</div>
              <div className="text-xs text-slate-500">Canal Transversal</div>
            </div>
          </div>

          {/* Status */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700/50">
            <div className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-xs text-slate-400">Sistema Activo</span>
          </div>
        </div>
      </div>
    </header>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTE: Hero section
// REFINEMENT: Strong hierarchy, clear messaging, no decorative elements
// ═══════════════════════════════════════════════════════════════════════════════

function Hero() {
  return (
    <section className="py-16 md:py-24 px-6">
      <div className="max-w-3xl mx-auto text-center">
        <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-white leading-tight mb-6">
          Canal Transversal
          <span className="block text-pink-400">Multitemático</span>
        </h1>

        <p className="text-lg text-slate-400 leading-relaxed max-w-2xl mx-auto">
          ODI es un organismo digital industrial que opera en múltiples verticales.
          Una sola lógica, adaptada a cada industria.
        </p>
      </div>
    </section>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTE: Industry Card
// REFINEMENT: Icons ABOVE text, reduced size, clean spacing
// ═══════════════════════════════════════════════════════════════════════════════

function IndustryCardComponent({ industry }: { industry: IndustryCard }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        bg-slate-900/60 border border-slate-800/60 rounded-xl p-6
        ${industry.isActive ? 'hover:border-slate-700/80' : 'opacity-60'}
        transition-colors duration-200
      `}
    >
      {/* Icon ABOVE text */}
      <div
        className="w-12 h-12 rounded-lg flex items-center justify-center mb-4"
        style={{
          backgroundColor: `${industry.color}15`,
          border: `1px solid ${industry.color}30`
        }}
      >
        <div style={{ color: industry.color }}>
          {industry.icon}
        </div>
      </div>

      {/* Title */}
      <h3 className="text-lg font-semibold text-white mb-2">
        {industry.name}
      </h3>

      {/* Description */}
      <p className="text-sm text-slate-400 leading-relaxed mb-4">
        {industry.description}
      </p>

      {/* Branches */}
      <div className="flex flex-wrap gap-2 mb-4">
        {industry.branches.map((branch) => (
          <span
            key={branch}
            className="text-xs px-2 py-1 rounded bg-slate-800/60 text-slate-400"
          >
            {branch}
          </span>
        ))}
      </div>

      {/* Domain link */}
      {industry.isActive ? (
        <a
          href={`https://${industry.domain}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm text-slate-300 hover:text-white transition-colors"
        >
          {industry.domain}
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      ) : (
        <span className="text-sm text-slate-500">
          {industry.domain}
        </span>
      )}
    </motion.div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTE: Industries Grid
// REFINEMENT: Balanced grid, responsive stacking
// ═══════════════════════════════════════════════════════════════════════════════

function IndustriesSection() {
  return (
    <section className="py-12 px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-xl font-semibold text-white mb-8 text-center">
          Industrias Activas
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {INDUSTRIES.map((industry) => (
            <IndustryCardComponent key={industry.id} industry={industry} />
          ))}
        </div>
      </div>
    </section>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTE: Architecture diagram
// REFINEMENT: Clean, informational, no decorative graphics
// ═══════════════════════════════════════════════════════════════════════════════

function ArchitectureSection() {
  const platforms = [
    { name: 'ecosistema-adsi.com', label: 'Plataforma' },
    { name: 'liveodi.com', label: 'Interfaz' },
    { name: 'somosindustriasodi.com', label: 'Multi-industria' },
  ]

  return (
    <section className="py-12 px-6 border-t border-slate-800/50">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-xl font-semibold text-white mb-8 text-center">
          Arquitectura
        </h2>

        {/* CATRMU Node */}
        <div className="flex justify-center mb-8">
          <div className="px-6 py-3 bg-pink-500/10 border border-pink-500/30 rounded-lg">
            <span className="text-pink-400 font-medium">catrmu.com</span>
          </div>
        </div>

        {/* Connection line */}
        <div className="flex justify-center mb-8">
          <div className="w-px h-8 bg-slate-700" />
        </div>

        {/* Platform nodes */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          {platforms.map((platform) => (
            <div
              key={platform.name}
              className="text-center p-4 bg-slate-900/40 border border-slate-800/50 rounded-lg"
            >
              <div className="text-sm text-slate-300 mb-1">{platform.name}</div>
              <div className="text-xs text-slate-500">{platform.label}</div>
            </div>
          ))}
        </div>

        {/* Connection line */}
        <div className="flex justify-center mb-8">
          <div className="w-px h-8 bg-slate-700" />
        </div>

        {/* Industry nodes */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {INDUSTRIES.map((industry) => (
            <div
              key={industry.id}
              className="text-center p-4 rounded-lg"
              style={{
                backgroundColor: `${industry.color}08`,
                border: `1px solid ${industry.color}20`
              }}
            >
              <div className="text-sm font-medium" style={{ color: industry.color }}>
                {industry.name}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                {industry.branches.length} ramas
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTE: Contact section
// REFINEMENT: Separate operational from formal contacts, neutral presentation
// ═══════════════════════════════════════════════════════════════════════════════

function ContactSection() {
  return (
    <section className="py-12 px-6 border-t border-slate-800/50">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-xl font-semibold text-white mb-8 text-center">
          Contacto
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Formal contact */}
          <div className="p-6 bg-slate-900/40 border border-slate-800/50 rounded-lg">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center flex-shrink-0">
                <Mail className="w-5 h-5 text-slate-400" />
              </div>
              <div>
                <div className="text-sm font-medium text-white mb-1">Correo institucional</div>
                <a
                  href="mailto:info@catrmu.com"
                  className="text-sm text-slate-400 hover:text-slate-300 transition-colors"
                >
                  info@catrmu.com
                </a>
              </div>
            </div>
          </div>

          {/* Operational contact */}
          <div className="p-6 bg-slate-900/40 border border-slate-800/50 rounded-lg">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center flex-shrink-0">
                <Phone className="w-5 h-5 text-slate-400" />
              </div>
              <div>
                <div className="text-sm font-medium text-white mb-1">WhatsApp operativo</div>
                <a
                  href="https://wa.me/573225462101"
                  className="text-sm text-slate-400 hover:text-slate-300 transition-colors"
                >
                  +57 322 546 2101
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Location */}
        <div className="mt-6 p-4 bg-slate-900/20 border border-slate-800/30 rounded-lg">
          <div className="flex items-center justify-center gap-2 text-sm text-slate-500">
            <MapPin className="w-4 h-4" />
            <span>Pereira, Risaralda, Colombia</span>
          </div>
        </div>
      </div>
    </section>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTE: Footer
// REFINEMENT: Simplified, single line legal, clean and professional
// ═══════════════════════════════════════════════════════════════════════════════

function Footer() {
  return (
    <footer className="py-6 px-6 border-t border-slate-800/50">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <span>CATRMU — Canal Transversal Multitemático</span>
          <span>ODI v17.4 · La Roca Motorepuestos · NIT 10.776.560-1</span>
        </div>
      </div>
    </footer>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// PÁGINA PRINCIPAL
// ═══════════════════════════════════════════════════════════════════════════════

export default function CATRMUPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Background gradient - subtle, not decorative */}
      <div className="fixed inset-0 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 -z-10" />

      <Header />

      <main>
        <Hero />
        <IndustriesSection />
        <ArchitectureSection />
        <ContactSection />
      </main>

      <Footer />
    </div>
  )
}
