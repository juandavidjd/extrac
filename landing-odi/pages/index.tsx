import Head from 'next/head'
import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Brain,
  Zap,
  ShoppingCart,
  MessageSquare,
  BarChart3,
  Cog,
  ArrowRight,
  CheckCircle,
  Bot,
  Sparkles
} from 'lucide-react'

// Empresas del ecosistema ODI
const ECOSYSTEM_COMPANIES = [
  { name: 'KAIQI', industry: 'Repuestos Motos', products: '2,847' },
  { name: 'JAPAN', industry: 'Repuestos Motos', products: '1,523' },
  { name: 'ARMOTOS', industry: 'Repuestos Motos', products: '1,885' },
  { name: 'BARA', industry: 'Repuestos Motos', products: '956' },
  { name: 'DFG', industry: 'Repuestos Motos', products: '743' },
  { name: 'YOKOMAR', industry: 'Repuestos Motos', products: '612' },
  { name: 'VAISAND', industry: 'Repuestos Motos', products: '534' },
  { name: 'LEO', industry: 'Repuestos Motos', products: '421' },
  { name: 'DUNA', industry: 'Repuestos Motos', products: '389' },
  { name: 'IMBRA', industry: 'Repuestos Motos', products: '267' },
]

const CAPABILITIES = [
  {
    icon: Brain,
    title: 'Vision AI',
    description: 'Extrae productos de catálogos PDF usando GPT-4 Vision. Códigos, precios, descripciones automáticas.',
    color: 'from-cyan-500 to-blue-500'
  },
  {
    icon: Cog,
    title: 'SRM Pipeline',
    description: 'Procesamiento en 6 etapas: Ingesta → Extracción → Normalización → Unificación → Enriquecimiento → Ficha 360°',
    color: 'from-blue-500 to-indigo-500'
  },
  {
    icon: ShoppingCart,
    title: 'Multi-Tenant Shopify',
    description: '10+ tiendas Shopify sincronizadas. Push automático de productos con branding por cliente.',
    color: 'from-indigo-500 to-purple-500'
  },
  {
    icon: MessageSquare,
    title: 'WhatsApp Business',
    description: 'Tony Maestro narra resultados técnicos. Ramona Anfitriona acompaña al cliente. Dualidad narrativa.',
    color: 'from-purple-500 to-pink-500'
  },
  {
    icon: BarChart3,
    title: 'Vigia Mercado',
    description: 'Monitoreo de competencia con Playwright. Alertas de precio, nuevos productos, tendencias.',
    color: 'from-pink-500 to-red-500'
  },
  {
    icon: Zap,
    title: 'Event-Driven',
    description: 'Sistema nervioso de eventos en tiempo real. ODI percibe, procesa y actúa por eventos, no mensajes.',
    color: 'from-red-500 to-orange-500'
  }
]

const STATS = [
  { value: '10,540+', label: 'Productos Procesados' },
  { value: '10', label: 'Tiendas Activas' },
  { value: '6', label: 'Etapas Pipeline' },
  { value: '24/7', label: 'Operación Continua' },
]

export default function Home() {
  const [email, setEmail] = useState('')

  return (
    <>
      <Head>
        <title>ODI - Organismo Digital Industrial | ADSI</title>
        <meta name="description" content="Sistema cognitivo industrial que convierte catálogos PDF en productos vendibles. Powered by ADSI." />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
        {/* Header */}
        <header className="fixed top-0 w-full z-50 bg-slate-950/80 backdrop-blur-lg border-b border-slate-800">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <div>
                  <span className="text-xl font-bold text-white">ODI</span>
                  <span className="text-xs text-slate-400 block -mt-1">Organismo Digital</span>
                </div>
              </div>
              <nav className="hidden md:flex items-center space-x-8">
                <a href="#capabilities" className="text-slate-300 hover:text-white transition">Capacidades</a>
                <a href="#ecosystem" className="text-slate-300 hover:text-white transition">Ecosistema</a>
                <a href="#contact" className="text-slate-300 hover:text-white transition">Contacto</a>
                <a
                  href="https://n8n.odi-server.com"
                  target="_blank"
                  className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-lg text-white font-medium hover:opacity-90 transition"
                >
                  Dashboard
                </a>
              </nav>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              className="text-center"
            >
              {/* ADSI Badge */}
              <div className="inline-flex items-center px-4 py-2 rounded-full bg-slate-800/50 border border-slate-700 mb-8">
                <Sparkles className="w-4 h-4 text-cyan-400 mr-2" />
                <span className="text-sm text-slate-300">
                  Powered by <span className="text-cyan-400 font-semibold">ADSI</span> - Análisis | Diseño | Desarrollo
                </span>
              </div>

              <h1 className="text-5xl md:text-7xl font-bold text-white mb-6">
                <span className="bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500 bg-clip-text text-transparent">
                  Organismo Digital
                </span>
                <br />
                <span className="text-white">Industrial</span>
              </h1>

              <p className="text-xl text-slate-400 max-w-3xl mx-auto mb-8">
                No soy un chatbot. Soy un <span className="text-cyan-400">sistema cognitivo</span> que convierte
                catálogos PDF en productos vendibles. Percibo, proceso y actúo — todo por eventos.
              </p>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
                <a
                  href="#contact"
                  className="px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl text-white font-semibold text-lg hover:opacity-90 transition flex items-center"
                >
                  Activar ODI para tu negocio
                  <ArrowRight className="w-5 h-5 ml-2" />
                </a>
                <a
                  href="#capabilities"
                  className="px-8 py-4 bg-slate-800 border border-slate-700 rounded-xl text-white font-semibold text-lg hover:bg-slate-700 transition"
                >
                  Ver capacidades
                </a>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
                {STATS.map((stat, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 + index * 0.1 }}
                    className="text-center"
                  >
                    <div className="text-3xl md:text-4xl font-bold text-white mb-1">{stat.value}</div>
                    <div className="text-sm text-slate-500">{stat.label}</div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>
        </section>

        {/* Capabilities Section */}
        <section id="capabilities" className="py-20 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                Capacidades del Organismo
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                ODI opera en 6 dimensiones cognitivas para transformar datos industriales en valor comercial.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {CAPABILITIES.map((cap, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                  className="p-6 rounded-2xl bg-slate-800/50 border border-slate-700 hover:border-slate-600 transition group"
                >
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${cap.color} flex items-center justify-center mb-4 group-hover:scale-110 transition`}>
                    <cap.icon className="w-6 h-6 text-white" />
                  </div>
                  <h3 className="text-xl font-semibold text-white mb-2">{cap.title}</h3>
                  <p className="text-slate-400">{cap.description}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Pipeline Visualization */}
        <section className="py-20 px-4 sm:px-6 lg:px-8 bg-slate-900/50">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                Pipeline SRM v4.0
              </h2>
              <p className="text-slate-400">De PDF a producto publicado en 6 etapas</p>
            </div>

            <div className="flex flex-wrap justify-center items-center gap-4">
              {['Ingesta', 'Extracción', 'Normalización', 'Unificación', 'Enriquecimiento', 'Ficha 360°'].map((step, index) => (
                <div key={index} className="flex items-center">
                  <div className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/30">
                    <span className="text-cyan-400 font-mono text-sm">{index + 1}.</span>
                    <span className="text-white ml-2">{step}</span>
                  </div>
                  {index < 5 && <ArrowRight className="w-5 h-5 text-slate-600 mx-2" />}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Ecosystem Section */}
        <section id="ecosystem" className="py-20 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                Ecosistema Multi-Tenant
              </h2>
              <p className="text-slate-400">10+ empresas conectadas a ODI</p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {ECOSYSTEM_COMPANIES.map((company, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.05 }}
                  className="p-4 rounded-xl bg-slate-800/50 border border-slate-700 text-center hover:border-cyan-500/50 transition"
                >
                  <div className="text-lg font-bold text-white mb-1">{company.name}</div>
                  <div className="text-sm text-cyan-400">{company.products} productos</div>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Contact Section */}
        <section id="contact" className="py-20 px-4 sm:px-6 lg:px-8 bg-slate-900/50">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Activa ODI para tu negocio
            </h2>
            <p className="text-slate-400 mb-8">
              ¿Tienes catálogos PDF que quieres convertir en una tienda online?
              ODI lo hace automático.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <input
                type="email"
                placeholder="tu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="px-6 py-4 rounded-xl bg-slate-800 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition"
              />
              <button className="px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl text-white font-semibold hover:opacity-90 transition">
                Solicitar demo
              </button>
            </div>

            <div className="mt-8 flex items-center justify-center space-x-6 text-slate-500">
              <div className="flex items-center">
                <CheckCircle className="w-5 h-5 text-green-500 mr-2" />
                Sin código
              </div>
              <div className="flex items-center">
                <CheckCircle className="w-5 h-5 text-green-500 mr-2" />
                Setup en 24h
              </div>
              <div className="flex items-center">
                <CheckCircle className="w-5 h-5 text-green-500 mr-2" />
                Multi-idioma
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="py-12 px-4 sm:px-6 lg:px-8 border-t border-slate-800">
          <div className="max-w-7xl mx-auto">
            <div className="flex flex-col md:flex-row justify-between items-center">
              <div className="flex items-center space-x-3 mb-4 md:mb-0">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <div>
                  <span className="text-lg font-bold text-white">ODI</span>
                  <span className="text-xs text-slate-500 block">Powered by ADSI</span>
                </div>
              </div>

              <div className="text-slate-500 text-sm">
                © 2025 ADSI - Análisis, Diseño y Desarrollo de Sistemas de Información
              </div>
            </div>
          </div>
        </footer>
      </main>
    </>
  )
}
