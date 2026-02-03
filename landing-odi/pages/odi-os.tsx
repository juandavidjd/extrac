import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Brain,
  Mic,
  MessageSquare,
  Globe,
  BarChart3,
  Database,
  Zap,
  Eye,
  Cpu,
  Activity,
  CheckCircle,
  AlertCircle,
  Clock,
  Volume2,
  Send,
  Settings,
  Maximize2,
  X
} from 'lucide-react'

// ═══════════════════════════════════════════════════════════════════════════════
// ODI-OS: Sistema Operativo Cognitivo
// "ODI no responde. ODI procesa en voz alta."
// ═══════════════════════════════════════════════════════════════════════════════

// Estados cognitivos de ODI
type CognitiveState = 'idle' | 'listening' | 'thinking' | 'executing' | 'responding' | 'error'

const COGNITIVE_COLORS: Record<CognitiveState, string> = {
  idle: '#64748B',      // Gris
  listening: '#06B6D4', // Cyan
  thinking: '#3B82F6',  // Azul
  executing: '#F97316', // Naranja
  responding: '#10B981',// Verde
  error: '#EF4444',     // Rojo
}

const COGNITIVE_LABELS: Record<CognitiveState, string> = {
  idle: 'En espera',
  listening: 'Escuchando',
  thinking: 'Procesando',
  executing: 'Ejecutando',
  responding: 'Respondiendo',
  error: 'Error',
}

// Simulación de proceso cognitivo
interface CognitiveStep {
  stage: string
  message: string
  progress: number
  timestamp: string
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTE: ODI Core Orb (Centro del sistema)
// ═══════════════════════════════════════════════════════════════════════════════

function ODICoreOrb({ state, currentStep }: { state: CognitiveState; currentStep: string }) {
  const color = COGNITIVE_COLORS[state]

  return (
    <div className="relative flex flex-col items-center justify-center">
      {/* Anillos orbitales */}
      <div className="absolute w-64 h-64 rounded-full border border-slate-700/30 animate-spin-slow" />
      <div className="absolute w-48 h-48 rounded-full border border-slate-600/40" />

      {/* Orbe principal */}
      <motion.div
        animate={{
          boxShadow: `0 0 60px ${color}40, 0 0 120px ${color}20`,
          scale: state === 'executing' ? [1, 1.05, 1] : 1,
        }}
        transition={{
          duration: state === 'executing' ? 0.5 : 0.3,
          repeat: state === 'executing' ? Infinity : 0,
        }}
        className="relative w-32 h-32 rounded-full flex items-center justify-center"
        style={{ backgroundColor: `${color}20`, border: `2px solid ${color}` }}
      >
        {/* Icono central */}
        <Brain className="w-12 h-12" style={{ color }} />

        {/* Indicador de estado */}
        <motion.div
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full flex items-center justify-center"
          style={{ backgroundColor: color }}
        >
          {state === 'listening' && <Mic className="w-3 h-3 text-white" />}
          {state === 'thinking' && <Cpu className="w-3 h-3 text-white" />}
          {state === 'executing' && <Zap className="w-3 h-3 text-white" />}
          {state === 'responding' && <CheckCircle className="w-3 h-3 text-white" />}
          {state === 'error' && <AlertCircle className="w-3 h-3 text-white" />}
          {state === 'idle' && <Clock className="w-3 h-3 text-white" />}
        </motion.div>
      </motion.div>

      {/* Estado actual */}
      <div className="mt-4 text-center">
        <div className="text-sm font-medium" style={{ color }}>
          {COGNITIVE_LABELS[state]}
        </div>
        <div className="text-xs text-slate-500 mt-1 max-w-[200px] truncate">
          {currentStep || 'Listo para procesar'}
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTE: Ventana flotante OS
// ═══════════════════════════════════════════════════════════════════════════════

interface FloatingWindowProps {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
  color?: string
  className?: string
}

function FloatingWindow({ title, icon, children, color = '#06B6D4', className = '' }: FloatingWindowProps) {
  const [isMinimized, setIsMinimized] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-slate-900/80 backdrop-blur-xl rounded-xl border border-slate-700/50 overflow-hidden ${className}`}
      style={{ boxShadow: `0 0 20px ${color}10` }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2 border-b border-slate-700/50"
        style={{ backgroundColor: `${color}10` }}
      >
        <div className="flex items-center gap-2">
          <div style={{ color }}>{icon}</div>
          <span className="text-sm font-medium text-white">{title}</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-1 hover:bg-slate-700/50 rounded transition"
          >
            {isMinimized ? <Maximize2 className="w-3 h-3 text-slate-400" /> : <X className="w-3 h-3 text-slate-400" />}
          </button>
        </div>
      </div>

      {/* Content */}
      <AnimatePresence>
        {!isMinimized && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            className="overflow-hidden"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTE: Terminal de Logs
// ═══════════════════════════════════════════════════════════════════════════════

function LogsTerminal({ logs }: { logs: CognitiveStep[] }) {
  return (
    <div className="p-3 font-mono text-xs max-h-48 overflow-y-auto">
      {logs.map((log, i) => (
        <div key={i} className="flex gap-2 py-1">
          <span className="text-slate-600">{log.timestamp}</span>
          <span className="text-cyan-400">[{log.stage}]</span>
          <span className="text-slate-300">{log.message}</span>
        </div>
      ))}
      {logs.length === 0 && (
        <div className="text-slate-600">Esperando actividad...</div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTE: Voice Input
// ═══════════════════════════════════════════════════════════════════════════════

function VoiceInput({ onSubmit, isListening }: { onSubmit: (text: string) => void; isListening: boolean }) {
  const [input, setInput] = useState('')

  const handleSubmit = () => {
    if (input.trim()) {
      onSubmit(input)
      setInput('')
    }
  }

  return (
    <div className="p-3">
      {/* Waveform visualization */}
      {isListening && (
        <div className="flex items-center justify-center gap-1 mb-3">
          {[...Array(12)].map((_, i) => (
            <motion.div
              key={i}
              animate={{ height: [8, 24, 8] }}
              transition={{ duration: 0.5, delay: i * 0.05, repeat: Infinity }}
              className="w-1 bg-cyan-400 rounded-full"
            />
          ))}
        </div>
      )}

      {/* Text input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder="Escribe o habla..."
          className="flex-1 bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition"
        />
        <button
          onClick={handleSubmit}
          className="p-2 bg-cyan-500/20 border border-cyan-500/50 rounded-lg hover:bg-cyan-500/30 transition"
        >
          <Send className="w-4 h-4 text-cyan-400" />
        </button>
        <button className="p-2 bg-slate-800/50 border border-slate-700 rounded-lg hover:bg-slate-700/50 transition">
          <Mic className="w-4 h-4 text-slate-400" />
        </button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTE: Metrics Dashboard
// ═══════════════════════════════════════════════════════════════════════════════

function MetricsDashboard() {
  return (
    <div className="p-3 grid grid-cols-2 gap-3">
      <div className="bg-slate-800/50 rounded-lg p-3">
        <div className="text-xs text-slate-500 mb-1">Latencia</div>
        <div className="text-lg font-bold text-white">1.2s</div>
        <div className="text-xs text-green-400">↓ 15%</div>
      </div>
      <div className="bg-slate-800/50 rounded-lg p-3">
        <div className="text-xs text-slate-500 mb-1">Precisión</div>
        <div className="text-lg font-bold text-white">94%</div>
        <div className="text-xs text-cyan-400">→ estable</div>
      </div>
      <div className="bg-slate-800/50 rounded-lg p-3">
        <div className="text-xs text-slate-500 mb-1">Fuentes</div>
        <div className="text-lg font-bold text-white">3</div>
        <div className="text-xs text-slate-400">consultadas</div>
      </div>
      <div className="bg-slate-800/50 rounded-lg p-3">
        <div className="text-xs text-slate-500 mb-1">Tareas Hoy</div>
        <div className="text-lg font-bold text-white">47</div>
        <div className="text-xs text-green-400">98% éxito</div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTE: Web Agent Preview
// ═══════════════════════════════════════════════════════════════════════════════

function WebAgentPreview({ isActive }: { isActive: boolean }) {
  return (
    <div className="p-3">
      <div className="bg-slate-950 rounded-lg overflow-hidden">
        {/* Browser chrome */}
        <div className="flex items-center gap-2 px-3 py-2 bg-slate-800 border-b border-slate-700">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500/60" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
            <div className="w-3 h-3 rounded-full bg-green-500/60" />
          </div>
          <div className="flex-1 bg-slate-900 rounded px-3 py-1 text-xs text-slate-400">
            somosrepuestosmotos.com
          </div>
        </div>

        {/* Browser content */}
        <div className="h-32 flex items-center justify-center">
          {isActive ? (
            <div className="text-center">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              >
                <Globe className="w-8 h-8 text-orange-400 mx-auto" />
              </motion.div>
              <div className="text-xs text-orange-400 mt-2">Extrayendo datos...</div>
            </div>
          ) : (
            <div className="text-center">
              <Globe className="w-8 h-8 text-slate-600 mx-auto" />
              <div className="text-xs text-slate-600 mt-2">Web Agent en espera</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// PÁGINA PRINCIPAL: ODI-OS Dashboard
// ═══════════════════════════════════════════════════════════════════════════════

export default function ODIOSDashboard() {
  const [cognitiveState, setCognitiveState] = useState<CognitiveState>('idle')
  const [currentStep, setCurrentStep] = useState('')
  const [logs, setLogs] = useState<CognitiveStep[]>([])

  // Simular proceso cognitivo
  const simulateProcess = async (input: string) => {
    const steps = [
      { state: 'listening' as CognitiveState, message: `Recibiendo: "${input}"`, stage: 'INPUT' },
      { state: 'thinking' as CognitiveState, message: 'Normalizando intención...', stage: 'NLP' },
      { state: 'thinking' as CognitiveState, message: 'Consultando embeddings...', stage: 'KB' },
      { state: 'executing' as CognitiveState, message: 'Ejecutando Playwright...', stage: 'WEB' },
      { state: 'executing' as CognitiveState, message: 'Extrayendo productos...', stage: 'SRM' },
      { state: 'responding' as CognitiveState, message: 'Generando respuesta...', stage: 'OUTPUT' },
    ]

    for (const step of steps) {
      setCognitiveState(step.state)
      setCurrentStep(step.message)

      const newLog: CognitiveStep = {
        stage: step.stage,
        message: step.message,
        progress: 100,
        timestamp: new Date().toLocaleTimeString(),
      }
      setLogs(prev => [...prev.slice(-20), newLog])

      await new Promise(resolve => setTimeout(resolve, 1500))
    }

    setCognitiveState('idle')
    setCurrentStep('Proceso completado')
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white overflow-hidden">
      {/* Fondo ADSI (gradientes y partículas) */}
      <div className="fixed inset-0 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(6,182,212,0.1),transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_80%,rgba(59,130,246,0.1),transparent_50%)]" />
      </div>

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between px-6 py-4 border-b border-slate-800/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="text-lg font-bold">ODI-OS</div>
            <div className="text-xs text-slate-500">Sistema Operativo Cognitivo v8.2</div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700">
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <span className="text-xs text-slate-400">ADSI Conectado</span>
          </div>
          <button className="p-2 hover:bg-slate-800 rounded-lg transition">
            <Settings className="w-5 h-5 text-slate-400" />
          </button>
        </div>
      </header>

      {/* Main Dashboard */}
      <main className="relative z-10 p-6 grid grid-cols-12 gap-4 h-[calc(100vh-80px)]">
        {/* Columna izquierda: Métricas y Voice */}
        <div className="col-span-3 flex flex-col gap-4">
          <FloatingWindow
            title="VOZ / INPUT"
            icon={<Mic className="w-4 h-4" />}
            color="#06B6D4"
          >
            <VoiceInput
              onSubmit={simulateProcess}
              isListening={cognitiveState === 'listening'}
            />
          </FloatingWindow>

          <FloatingWindow
            title="MÉTRICAS"
            icon={<BarChart3 className="w-4 h-4" />}
            color="#10B981"
          >
            <MetricsDashboard />
          </FloatingWindow>

          <FloatingWindow
            title="FUENTES ACTIVAS"
            icon={<Database className="w-4 h-4" />}
            color="#8B5CF6"
          >
            <div className="p-3 space-y-2">
              {['Catálogo SRM', 'KB Embeddings', 'Fitment M6.2'].map((source, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-green-400" />
                  <span className="text-slate-300">{source}</span>
                </div>
              ))}
            </div>
          </FloatingWindow>
        </div>

        {/* Centro: ODI Core */}
        <div className="col-span-6 flex flex-col items-center justify-center">
          <ODICoreOrb state={cognitiveState} currentStep={currentStep} />

          {/* Pipeline visual */}
          <div className="mt-8 flex items-center gap-2">
            {['INPUT', 'NLP', 'KB', 'WEB', 'SRM', 'OUTPUT'].map((stage, i) => {
              const isActive = logs.some(l => l.stage === stage)
              const isCurrent = logs[logs.length - 1]?.stage === stage

              return (
                <div key={stage} className="flex items-center">
                  <div
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all ${
                      isCurrent
                        ? 'bg-cyan-500/30 border border-cyan-500 text-cyan-400'
                        : isActive
                        ? 'bg-slate-800 border border-slate-600 text-slate-300'
                        : 'bg-slate-900/50 border border-slate-800 text-slate-600'
                    }`}
                  >
                    {stage}
                  </div>
                  {i < 5 && (
                    <div className={`w-4 h-px mx-1 ${isActive ? 'bg-cyan-500/50' : 'bg-slate-700'}`} />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Columna derecha: Web Agent y Logs */}
        <div className="col-span-3 flex flex-col gap-4">
          <FloatingWindow
            title="WEB AGENT"
            icon={<Globe className="w-4 h-4" />}
            color="#F97316"
          >
            <WebAgentPreview isActive={cognitiveState === 'executing'} />
          </FloatingWindow>

          <FloatingWindow
            title="LOGS / TERMINAL"
            icon={<Activity className="w-4 h-4" />}
            color="#06B6D4"
            className="flex-1"
          >
            <LogsTerminal logs={logs} />
          </FloatingWindow>
        </div>
      </main>

      {/* Footer status bar */}
      <footer className="fixed bottom-0 left-0 right-0 z-10 px-6 py-2 bg-slate-900/80 backdrop-blur border-t border-slate-800/50">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-4">
            <span>CPU: 23%</span>
            <span>MEM: 1.2GB</span>
            <span>Uptime: 4d 12h</span>
          </div>
          <div className="flex items-center gap-2">
            <span>ADSI Ecosystem</span>
            <span>•</span>
            <span>SRM v4.0</span>
            <span>•</span>
            <span className="text-cyan-400">ODI-OS v8.2</span>
          </div>
        </div>
      </footer>

      {/* Estilo para animación lenta */}
      <style jsx global>{`
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin-slow {
          animation: spin-slow 20s linear infinite;
        }
      `}</style>
    </div>
  )
}
