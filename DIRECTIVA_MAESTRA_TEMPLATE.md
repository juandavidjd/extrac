# DIRECTIVA DE IMPLEMENTACION

**Fecha:** YYYY-MM-DD
**Origen:** Debate Claude.ai / ChatGPT 5.2 / Gemini
**Prioridad:** Alta | Media | Baja
**Tipo:** Feature | Bugfix | Refactor | Integracion

---

## 1. CONTEXTO DEL PROYECTO (Claude.ai)

> Claude.ai tiene el proyecto indexado. Esta seccion describe QUE archivos
> existen y DONDE estan. Claude Code debe respetar estas rutas, no inventar otras.

**Archivos a modificar:**
- `ruta/exacta/archivo1.py` — descripcion del cambio
- `ruta/exacta/archivo2.jsx` — descripcion del cambio

**Archivos de referencia (solo lectura):**
- `ruta/archivo_contexto.py` — por que es relevante

**Dependencias criticas:**
- (Ej: FastAPI Pydantic v2, React Context API, Django ORM)

---

## 2. LOGICA DE NEGOCIO (ChatGPT 5.2)

> ChatGPT genera el script o algoritmo solido. Este codigo debe trasladarse
> TAL CUAL a los archivos destino. Claude Code NO debe interpretarlo ni
> "mejorarlo" — debe integrarlo.

```python
# Pegar aqui el codigo exacto generado por ChatGPT
# Incluir imports, clases, funciones completas
# No fragmentos — codigo ejecutable completo
```

**Restriccion:** No permitir variaciones en esta logica. El calculo/flujo
debe ser exactamente como esta escrito arriba.

---

## 3. RESTRICCIONES Y PROYECCION (Gemini)

> Gemini analiza riesgos, proyecta escalabilidad y define lo que NO debe pasar.

**Restricciones:**
- (Ej: "No acoplar el nuevo endpoint al modulo de pagos")
- (Ej: "Asegurar que el schema Django sea compatible con migracion futura")
- (Ej: "No usar useEffect para esta logica — usar useMemo")

**Proyeccion de impacto:**
- (Ej: "Este cambio afecta 3 endpoints existentes")
- (Ej: "Requiere migracion de base de datos")

---

## 4. CRITERIO DE EXITO (Consenso del debate)

**Tests que deben pasar:**
- [ ] Descripcion del test 1
- [ ] Descripcion del test 2

**Verificacion visual:**
- [ ] URL o ruta donde verificar el cambio
- [ ] Que debe verse/responder

**Comando de validacion:**
```bash
# Comando exacto para verificar que funciono
# Ej: pytest tests/test_endpoint.py -v
# Ej: curl -s http://localhost:8813/health | jq .
```

---

## 5. INSTRUCCION PARA GATEKEEPER

> Copiar esta linea tal cual para ejecutar el pipeline:

```bash
./gatekeeper.sh "Descripcion corta de la tarea"
```

**Instruccion para Claude Code (si no se usa gatekeeper):**

> "Lee CLAUDE.md primero. Ignora tus propias sugerencias de mejora.
> Tu unica mision es integrar la logica de la Seccion 2 en las rutas
> de la Seccion 1, respetando las restricciones de la Seccion 3.
> Despues de editar, lee los archivos modificados y muestrame las lineas
> exactas que cambiaste. No me resumas — muestrame el codigo en disco."

---

## NOTAS PARA JUAN DAVID

- Este template se llena ANTES de abrir Claude Code en la terminal
- El debate en la web (Claude.ai + ChatGPT + Gemini) produce la Directiva
- Claude Code en la terminal EJECUTA la Directiva, no la discute
- Si Claude Code propone algo diferente, prevalece la Directiva
