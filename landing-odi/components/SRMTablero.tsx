import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Factory,
  Truck,
  Store,
  Wrench,
  GraduationCap,
  Package,
  ChevronRight,
  TrendingUp
} from 'lucide-react'

// ═══════════════════════════════════════════════════════════════════════════════
// TABLERO ELECTRÓNICO SRM – Noticias Rotativas por Rol
// ═══════════════════════════════════════════════════════════════════════════════

interface NewsItem {
  text: string
  highlight?: boolean
}

interface RoleNews {
  id: string
  name: string
  tagline: string
  icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>
  color: string
  bgColor: string
  news: NewsItem[]
}

const SRM_NEWS: RoleNews[] = [
  {
    id: 'fabricantes',
    name: 'FABRICANTES',
    tagline: 'Ingeniería que mueve al país',
    icon: Factory,
    color: '#E53B47',
    bgColor: 'from-red-500/20 to-red-600/10',
    news: [
      { text: 'Japan alcanza 10.000+ productos estandarizados en SRM, fortaleciendo la trazabilidad nacional.', highlight: true },
      { text: 'Leo consolida su línea premium con compatibilidades 360°, mejorando tiempos de diagnóstico técnico.' },
      { text: 'Fabricantes conectados a SRM reportan 42% menos devoluciones gracias a fichas verificadas.' },
      { text: 'Nueva línea de frenos cerámicos 2024 disponible con terminología SRM, lista para distribuidores y talleres.' },
      { text: 'Estudios SRM revelan que las marcas con ingeniería real ganan 3X más confianza en decisiones de compra.' },
      { text: 'Estandarización SRM reduce 70% de errores de identificación en piezas OEM nacionales.' },
      { text: 'Fabricantes SRM ahora incluyen fichas 360° para fuerza de ventas, acelerando el canal nacional.' },
      { text: 'Pronto: Programa de certificación para fabricantes en Academia SRM.', highlight: true },
    ]
  },
  {
    id: 'importadores',
    name: 'IMPORTADORES',
    tagline: 'Tecnología internacional que llega al mecánico colombiano',
    icon: Package,
    color: '#0090FF',
    bgColor: 'from-blue-500/20 to-blue-600/10',
    news: [
      { text: 'DFG incorpora transmisiones de alta gama 2025 compatibles con la nomenclatura colombiana vía SRM.', highlight: true },
      { text: 'Duna amplía catálogo digital con 5.000 referencias nuevas, totalmente mapeadas con fitment SRM.' },
      { text: 'Importadores SRM reportan 40% más eficiencia operativa tras homologación técnica.' },
      { text: 'SRM habilita traducción técnica automática para facilitar venta al por mayor.' },
      { text: 'Mapeo de compatibilidades cruzadas reduce hasta 60% devoluciones en importadores.' },
      { text: 'Yokomar integra catálogo con terminología SRM y supera 15.000 fichas técnicas.' },
      { text: 'Nuevas líneas de accesorios llegan a Colombia con compatibilidad 360° listas para distribuidores.' },
      { text: 'Academia SRM lanzará módulo: "Cómo importar con riesgo técnico controlado".', highlight: true },
    ]
  },
  {
    id: 'distribuidores',
    name: 'DISTRIBUIDORES',
    tagline: 'Red logística que mantiene el país encendido',
    icon: Truck,
    color: '#10B981',
    bgColor: 'from-emerald-500/20 to-emerald-600/10',
    news: [
      { text: 'SRM permite rotación optimizada por demanda regional, reduciendo sobreinventario.', highlight: true },
      { text: 'Distribuidores SRM ya conectan más de 8 ciudades principales con disponibilidad confirmada.' },
      { text: 'Inventario unificado con terminología SRM mejora tiempos de despacho en 37%.' },
      { text: 'Reportes SRM revelan aumento de 22% en cierre de ventas gracias a fichas verificadas.' },
      { text: 'Distribuidores ahora asignan prioridades por zonas con inteligencia SRM.' },
      { text: 'Lanzamiento: Fichas técnicas para fuerza de ventas, acelerando respuesta al cliente final.' },
      { text: 'SRM habilita conexión directa con almacenes certificados, mejorando tiempos de reposición.' },
      { text: 'Academia SRM prepara módulo: "Gestión del riesgo en distribución técnica".', highlight: true },
    ]
  },
  {
    id: 'almacenes',
    name: 'ALMACENES',
    tagline: 'Donde la industria se vuelve realidad',
    icon: Store,
    color: '#8B5CF6',
    bgColor: 'from-violet-500/20 to-violet-600/10',
    news: [
      { text: 'Casa China Motos inaugura nuevo punto de venta con certificación SRM.', highlight: true },
      { text: 'Almacenes SRM reducen 55% errores de mostrador con búsqueda inteligente.' },
      { text: 'SRM habilita historial técnico para vendedores, mejorando calidad de atención al mecánico.' },
      { text: 'Vendedores SRM ahora acceden a recomendaciones garantizadas, basadas en compatibilidad 360°.' },
      { text: 'Nueva actualización SRM permite mostrar variaciones por modelo/versión en tiempo real.' },
      { text: 'Almacenes certificados reportan incremento de 28% en ticket promedio gracias a fichas técnicas.' },
      { text: 'SRM añade opción de consultar rotación y tendencia por referencia, ideal para gerencia.' },
      { text: 'Academia SRM lanzará curso: "Psicología de la venta técnica para mostradores".', highlight: true },
    ]
  },
  {
    id: 'talleres',
    name: 'TALLERES',
    tagline: 'Los expertos que mantienen a Colombia rodando',
    icon: Wrench,
    color: '#F97316',
    bgColor: 'from-orange-500/20 to-orange-600/10',
    news: [
      { text: 'Taller Casa China Motos recibe certificación SRM, asegurando diagnóstico confiable.', highlight: true },
      { text: 'Talleres SRM reducen hasta 80% el tiempo de identificación, gracias al fitment automatizado.' },
      { text: 'SRM ahora guarda histórico técnico de reparaciones, útil para seguimiento del mecánico.' },
      { text: 'Nueva función: búsqueda por sistema o aplicación (motor, suspensión, eléctrico).' },
      { text: 'Mecánicos con SRM reportan 3X más confianza al recomendar repuestos al cliente final.' },
      { text: 'Fichas 360° guían montaje seguro pieza a pieza, reduciendo riesgos de error.' },
      { text: 'Talleres conectados a SRM ganan reputación técnica y fidelidad natural del motociclista.' },
      { text: 'Academia SRM lanzará curso: "Diagnóstico asistido + Fitment real".', highlight: true },
    ]
  },
  {
    id: 'academia',
    name: 'ACADEMIA SRM',
    tagline: 'Donde el conocimiento técnico se convierte en resultados',
    icon: GraduationCap,
    color: '#06B6D4',
    bgColor: 'from-cyan-500/20 to-cyan-600/10',
    news: [
      { text: 'Academia SRM abrirá sus primeros cursos certificados 2025: Fundamentos + Terminología.', highlight: true },
      { text: 'Nuevo módulo: Gestión de inventarios con lógica 360° para distribuidores y almacenes.' },
      { text: 'Se habilita programa de certificación para talleres con diagnóstico asistido SRM.' },
      { text: 'SRM prepara curso especializado para importadores: Riesgo técnico y compatibilidad.' },
      { text: 'Currículum SRM ya supera 40 lecciones estructuradas, listas para profesionales del sector.' },
      { text: 'Pronto: ruta de aprendizaje por roles – Mecánico, Vendedor, Jefe de Inventarios, Importador.' },
      { text: 'Publicación SRM: "Diccionario técnico de la industria" disponible como recurso gratuito.' },
      { text: 'Lanzamiento de SRM Podcast – Historias reales de la industria de motocicletas.', highlight: true },
    ]
  },
]

// ═══════════════════════════════════════════════════════════════════════════════
// Componente: Ticker de noticias (marquee)
// ═══════════════════════════════════════════════════════════════════════════════

function NewsTicker({ news, color }: { news: NewsItem[]; color: string }) {
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % news.length)
    }, 5000)
    return () => clearInterval(interval)
  }, [news.length])

  return (
    <div className="overflow-hidden h-8 flex items-center">
      <AnimatePresence mode="wait">
        <motion.div
          key={currentIndex}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
          className="flex items-center gap-2"
        >
          {news[currentIndex].highlight && (
            <TrendingUp className="w-4 h-4 flex-shrink-0" style={{ color }} />
          )}
          <span className={`text-sm ${news[currentIndex].highlight ? 'font-medium' : ''}`}>
            {news[currentIndex].text}
          </span>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Componente: Card de Rol
// ═══════════════════════════════════════════════════════════════════════════════

function RoleCard({ role, isExpanded, onToggle }: {
  role: RoleNews
  isExpanded: boolean
  onToggle: () => void
}) {
  const Icon = role.icon

  return (
    <motion.div
      layout
      className={`rounded-xl border overflow-hidden transition-all ${
        isExpanded
          ? 'border-slate-600 bg-slate-800/50'
          : 'border-slate-700/50 bg-slate-900/50 hover:border-slate-600'
      }`}
      style={{
        boxShadow: isExpanded ? `0 0 30px ${role.color}20` : 'none'
      }}
    >
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full p-4 flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: `${role.color}20` }}
          >
            <Icon className="w-5 h-5" style={{ color: role.color }} />
          </div>
          <div className="text-left">
            <div className="font-semibold text-white">{role.name}</div>
            <div className="text-xs text-slate-500">{role.tagline}</div>
          </div>
        </div>
        <motion.div
          animate={{ rotate: isExpanded ? 90 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronRight className="w-5 h-5 text-slate-400" />
        </motion.div>
      </button>

      {/* Ticker (siempre visible) */}
      <div className="px-4 pb-2 text-slate-400">
        <NewsTicker news={role.news} color={role.color} />
      </div>

      {/* Expanded content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-2">
              {role.news.map((item, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-2 text-sm p-2 rounded-lg ${
                    item.highlight
                      ? 'bg-slate-800/50'
                      : ''
                  }`}
                >
                  <div
                    className="w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0"
                    style={{ backgroundColor: item.highlight ? role.color : '#64748B' }}
                  />
                  <span className={item.highlight ? 'text-white' : 'text-slate-400'}>
                    {item.text}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Componente Principal: SRM Tablero
// ═══════════════════════════════════════════════════════════════════════════════

export default function SRMTablero() {
  const [expandedRole, setExpandedRole] = useState<string | null>(null)

  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center px-4 py-2 rounded-full bg-red-500/10 border border-red-500/30 mb-4">
            <span className="text-sm text-red-400 font-medium">
              TABLERO SRM EN VIVO
            </span>
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Noticias del Ecosistema
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            Actualizaciones en tiempo real de fabricantes, importadores, distribuidores,
            almacenes, talleres y Academia SRM.
          </p>
        </div>

        {/* Marquee global */}
        <div className="mb-8 overflow-hidden bg-slate-800/30 rounded-lg border border-slate-700/50 py-3 px-4">
          <div className="flex items-center animate-marquee whitespace-nowrap">
            {SRM_NEWS.flatMap(role =>
              role.news.filter(n => n.highlight).map((news, i) => (
                <span key={`${role.id}-${i}`} className="mx-8 flex items-center gap-2">
                  <span style={{ color: role.color }}>●</span>
                  <span className="text-slate-300">{news.text}</span>
                </span>
              ))
            )}
          </div>
        </div>

        {/* Grid de roles */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {SRM_NEWS.map(role => (
            <RoleCard
              key={role.id}
              role={role}
              isExpanded={expandedRole === role.id}
              onToggle={() => setExpandedRole(
                expandedRole === role.id ? null : role.id
              )}
            />
          ))}
        </div>

        {/* Link a somosrepuestosmotos.com */}
        <div className="mt-12 text-center">
          <a
            href="https://somosrepuestosmotos.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-red-500 to-red-600 rounded-xl text-white font-medium hover:opacity-90 transition"
          >
            Visitar somosrepuestosmotos.com
            <ChevronRight className="w-5 h-5" />
          </a>
        </div>
      </div>

      {/* Estilos para marquee */}
      <style jsx>{`
        @keyframes marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-marquee {
          animation: marquee 60s linear infinite;
        }
      `}</style>
    </section>
  )
}
