# ODI Landing Page - ADSI Ecosystem

Landing page para **ODI (Organismo Digital Industrial)** con branding ADSI.

## 🚀 Despliegue en Vercel

### Opción 1: Deploy automático (recomendado)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/juandavidjd/extrac/tree/main/landing-odi)

### Opción 2: Deploy manual

1. **Instalar Vercel CLI:**
```bash
npm i -g vercel
```

2. **Clonar y desplegar:**
```bash
cd landing-odi
npm install
vercel
```

3. **Seguir prompts:**
   - Link to existing project? → No
   - What's your project's name? → odi-landing
   - In which directory is your code located? → ./
   - Want to modify settings? → No

4. **Configurar dominio personalizado (opcional):**
```bash
vercel domains add odi.adsi.co
```

## 🔧 Desarrollo local

```bash
# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev

# Build para producción
npm run build
```

## 📁 Estructura

```
landing-odi/
├── pages/
│   ├── _app.tsx        # App wrapper
│   └── index.tsx       # Página principal
├── styles/
│   └── globals.css     # Estilos globales + Tailwind
├── public/             # Assets estáticos
├── package.json
├── tailwind.config.js
├── vercel.json         # Configuración Vercel
└── tsconfig.json
```

## 🎨 Personalización

### Colores ADSI

Los colores de marca están en `tailwind.config.js`:

```js
colors: {
  adsi: {
    cyan: '#06B6D4',    // Principal
    blue: '#3B82F6',    // Secundario
    indigo: '#6366F1',  // Acento
    purple: '#8B5CF6',  // Destacado
  },
}
```

### Empresas del ecosistema

Editar el array `ECOSYSTEM_COMPANIES` en `pages/index.tsx`:

```typescript
const ECOSYSTEM_COMPANIES = [
  { name: 'KAIQI', industry: 'Repuestos Motos', products: '2,847' },
  // ... más empresas
]
```

### Logo y favicon

Reemplazar archivos en `public/`:
- `favicon.ico` - Favicon del sitio
- `logo.png` - Logo ODI/ADSI

## 🌐 Variables de entorno

Crear `.env.local` para desarrollo:

```env
NEXT_PUBLIC_SITE_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=https://api.odi-server.com
```

En Vercel, configurar en Settings → Environment Variables.

## 📱 Responsive

La landing es completamente responsive:
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

## 🔗 Enlaces importantes

- **Dashboard n8n:** https://n8n.odi-server.com
- **API ODI:** https://api.odi-server.com
- **Documentación:** /docs

## 📄 Licencia

© 2025 ADSI - Análisis, Diseño y Desarrollo de Sistemas de Información
