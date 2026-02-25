#!/usr/bin/env python3
"""
odi_organismo_middleware.py - Sistema Nervioso Central de ODI v25

Correcciones V25.1:
- BLOQUEOS: Guardian naranja NO bloquea ficha/diagnostico/audit
- LATENCIA: batch_mode ChromaDB si total_productos > 50
- FRONTEND: defaults mode=build, voice=ramona, follow=None, from=""
"""

import os, json, hashlib, logging, requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger("odi.middleware")

ODI_ROOT = Path("/opt/odi")
PERSONALIDAD = ODI_ROOT / "personalidad"
GUARDIAN = ODI_ROOT / "guardian"
BILLING = ODI_ROOT / "billing"
DATA = ODI_ROOT / "data"
AUDIT_DIR = DATA / "audit" / "middleware"

OPERACIONES_COMERCIALES = {"merge", "activar_productos", "sync_shopify", "image_clean"}

class OrganismoMiddleware:
    _instance = None

    def __init__(self):
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        self._load_esencia()
        self._load_guardian()
        self._load_billing_config()
        self._prev_hash = None
        logger.info("OrganismoMiddleware v25 inicializado")

    def _load_yaml_file(self, path):
        if not path.exists():
            return {}
        try:
            with open(path) as f:
                content = f.read()
            if yaml:
                return yaml.safe_load(content) or {}
            return {}
        except:
            return {}

    def _load_esencia(self):
        self.adn = self._load_yaml_file(PERSONALIDAD / "adn.yaml")
        self.genes = self.adn.get("genes", {})
        self.frases_prohibidas = []
        prohibidas_data = self._load_yaml_file(PERSONALIDAD / "frases" / "prohibidas.yaml")
        for key, value in prohibidas_data.items():
            if isinstance(value, list):
                self.frases_prohibidas.extend(value)

    def _load_guardian(self):
        self.guardian_estado = {"color": "verde", "nivel": 0}
        estado_path = GUARDIAN / "estado_actual.json"
        if estado_path.exists():
            try:
                with open(estado_path) as f:
                    data = json.load(f)
                    self.guardian_estado = {
                        "color": data.get("color", data.get("estado", "verde")),
                        "nivel": data.get("nivel", 0)
                    }
            except:
                pass

    def _load_billing_config(self):
        self.billing_config = {"min_rate": 0.03, "max_rate": 0.07}

    def pre_operacion(self, contexto):
        resultado = {
            "permitido": True, "motivo": "", "enrichment": {},
            "score": 1.0, "gates": {}, "timestamp": datetime.utcnow().isoformat(),
            "batch_mode": contexto.get("total_productos", 0) > 50
        }

        g1 = self._guardian_check(contexto)
        resultado["gates"]["guardian"] = g1
        if not g1["pass"]:
            resultado["permitido"] = False
            resultado["motivo"] = "Guardian " + g1["color"] + ": " + g1["reason"]
            self._audit_log("PRE_BLOCKED", resultado)
            return resultado

        g2 = self._radar_anomaly_detect(contexto)
        resultado["gates"]["radar"] = g2
        if g2.get("anomaly_detected"):
            resultado["score"] *= 0.7

        g3 = self._esencia_criterio(contexto)
        resultado["gates"]["esencia"] = g3

        g4 = self._chromadb_enrich(contexto, resultado["batch_mode"])
        resultado["gates"]["chromadb"] = g4
        resultado["enrichment"] = g4.get("enrichment", {})

        if resultado["score"] < 0.5:
            resultado["permitido"] = False
            resultado["motivo"] = "Score bajo: " + str(resultado["score"])

        self._audit_log("PRE_OK" if resultado["permitido"] else "PRE_BLOCKED", resultado)
        return resultado

    def post_operacion(self, contexto):
        resultado = {"ok": True, "gates": {}, "timestamp": datetime.utcnow().isoformat()}
        resultado["gates"]["url"] = self._verificar_url_publica(contexto)
        resultado["gates"]["pattern"] = self._radar_pattern_learn(contexto)
        resultado["gates"]["billing"] = self._billing_registrar(contexto)
        resultado["gates"]["vivir"] = self._vivir_emit(contexto)
        resultado["gates"]["audit"] = self._cross_audit_trigger(contexto)
        self._audit_log("POST", resultado)
        return resultado

    def _guardian_check(self, ctx):
        self._load_guardian()
        color = self.guardian_estado.get("color", "verde")

        bloqueo_flag = GUARDIAN / "bloqueo_comercio.flag"
        if bloqueo_flag.exists():
            return {"pass": False, "color": "rojo", "reason": "bloqueo_comercio.flag activo"}

        if color in ("rojo", "negro"):
            return {"pass": False, "color": color, "reason": "Guardian en estado " + color}

        # CORRECCION V25.1: Naranja solo bloquea operaciones COMERCIALES
        if color == "naranja":
            op = ctx.get("operacion", "")
            tipo = ctx.get("tipo", "")
            if op in OPERACIONES_COMERCIALES or tipo in OPERACIONES_COMERCIALES:
                return {"pass": False, "color": color, "reason": "Operaciones comerciales bloqueadas en naranja"}
            logger.info("Guardian naranja permite operacion no-comercial: " + op)

        return {"pass": True, "color": color}

    def _radar_anomaly_detect(self, ctx):
        anomalies = []
        total = ctx.get("total_productos", 0)
        con_img = ctx.get("con_imagen", total)
        if total > 0 and con_img / total < 0.2:
            anomalies.append("Solo " + str(con_img) + "/" + str(total) + " con imagen")
        if ctx.get("precios_estimados", 0) > 0:
            anomalies.append("Precios estimados detectados")
        if total > 500 and not ctx.get("confirmado_humano"):
            anomalies.append("Operacion masiva sin confirmacion")
        return {"anomaly_detected": len(anomalies) > 0, "anomalies": anomalies}

    def _esencia_criterio(self, ctx):
        violations = []
        textos = [ctx.get("titulo", ""), ctx.get("descripcion", "")]
        beneficios = ctx.get("beneficios", [])
        if isinstance(beneficios, list):
            textos.extend(beneficios)
        for texto in textos:
            texto_lower = str(texto).lower()
            for frase in self.frases_prohibidas:
                if isinstance(frase, str) and frase.lower() in texto_lower:
                    violations.append("Frase prohibida: " + frase)
        return {"pass": len(violations) == 0, "violations": violations}

    def _chromadb_enrich(self, ctx, batch_mode=False):
        enrichment = {}
        empresa = ctx.get("empresa", "")
        # CORRECCION V25.1: batch_mode si total_productos > 50
        if batch_mode:
            titulos = ctx.get("titulos_muestra", [])
            query = " | ".join(titulos[:5]) if titulos else "productos " + empresa
        else:
            query = ctx.get("query_enrichment", ctx.get("titulo", ""))
        if not query:
            return {"enrichment": {}, "batch_mode": batch_mode}
        try:
            resp = requests.post("http://localhost:8803/search",
                json={"query": query, "empresa": empresa, "n_results": 5 if batch_mode else 3}, timeout=5)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    enrichment = {
                        "compatibilidad_sugerida": results[0].get("compatibilidad", ""),
                        "categoria_sugerida": results[0].get("categoria", ""),
                        "n_results": len(results), "batch_mode": batch_mode
                    }
        except Exception as e:
            enrichment = {"error": str(e), "batch_mode": batch_mode}
        return {"enrichment": enrichment, "batch_mode": batch_mode}

    def _verificar_url_publica(self, ctx):
        url = ctx.get("url_publica")
        if not url:
            return {"verificado": False, "reason": "sin URL"}
        try:
            resp = requests.get(url, timeout=10, allow_redirects=True)
            html = resp.text.lower()
            problemas = []
            for marker in ["you may also like", "join our email", "add to cart", "sold out"]:
                if marker in html:
                    problemas.append("Texto ingles: " + marker)
            return {"verificado": True, "status": resp.status_code, "problemas": problemas}
        except Exception as e:
            return {"verificado": False, "reason": str(e)}

    def _radar_pattern_learn(self, ctx):
        pattern = {"operacion": ctx.get("operacion"), "empresa": ctx.get("empresa"),
                   "resultado": ctx.get("resultado"), "productos": ctx.get("productos_procesados", 0),
                   "ts": datetime.utcnow().isoformat()}
        patterns_file = DATA / "radar" / "patterns.jsonl"
        patterns_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(patterns_file, "a") as f:
                f.write(json.dumps(pattern) + "\n")
            return {"learned": True}
        except:
            return {"learned": False}

    def _billing_registrar(self, ctx):
        if ctx.get("resultado") != "ok":
            return {"registered": False, "reason": "no exitoso"}
        productos = ctx.get("productos_procesados", 0)
        if productos == 0:
            return {"registered": False, "reason": "0 productos"}
        entry = {"operacion": ctx.get("operacion"), "empresa": ctx.get("empresa"),
                 "productos": productos, "timestamp": datetime.utcnow().isoformat(), "merito": True}
        ledger_path = BILLING / "ledger_odi.json"
        try:
            ledger = []
            if ledger_path.exists():
                with open(ledger_path) as f:
                    ledger = json.load(f)
            ledger.append(entry)
            with open(ledger_path, "w") as f:
                json.dump(ledger, f, indent=2, ensure_ascii=False)
            return {"registered": True}
        except Exception as e:
            return {"registered": False, "reason": str(e)}

    def _vivir_emit(self, ctx):
        try:
            requests.post("http://localhost:8765/emit",
                json={"type": "operacion", "empresa": ctx.get("empresa"), "operacion": ctx.get("operacion")}, timeout=2)
            return {"emitted": True}
        except:
            return {"emitted": False}

    def _cross_audit_trigger(self, ctx):
        empresa = ctx.get("empresa")
        if not empresa:
            return {"triggered": False}
        try:
            requests.post("http://localhost:8808/audit/empresa",
                json={"empresa": empresa, "operacion": ctx.get("operacion")}, timeout=2)
            return {"triggered": True}
        except:
            return {"triggered": False}

    def _audit_log(self, tipo, data):
        entry = {"tipo": tipo, "timestamp": datetime.utcnow().isoformat(), "prev_hash": self._prev_hash}
        entry_json = json.dumps(entry, sort_keys=True, default=str)
        entry["hash"] = hashlib.sha256(entry_json.encode()).hexdigest()
        self._prev_hash = entry["hash"]
        audit_file = AUDIT_DIR / ("middleware_" + datetime.utcnow().strftime("%Y%m%d") + ".jsonl")
        try:
            with open(audit_file, "a") as f:
                f.write(json.dumps({**entry, "data": data}, default=str) + "\n")
        except:
            pass

_middleware = None

def get_middleware():
    global _middleware
    if _middleware is None:
        _middleware = OrganismoMiddleware()
    return _middleware

# CORRECCION V25.1: Helpers para Chat API con defaults
def detect_mode(message, industry="", productos=None):
    if productos is None:
        productos = []
    msg = message.lower()
    if any(k in msg for k in ["solo", "mal", "triste", "ayuda"]):
        return "care"
    if productos:
        return "commerce"
    if industry.startswith("salud"):
        return "care"
    if any(k in msg for k in ["pagina", "web", "analizar"]):
        return "diagnose"
    if any(k in msg for k in ["trabajo", "empleo"]):
        return "empower"
    if any(k in msg for k in ["montar", "negocio", "tienda"]):
        return "build"
    if any(k in msg for k in ["excel", "automatizar"]):
        return "optimize"
    if any(k in msg for k in ["estudiar", "aprender"]):
        return "learn"
    return "build"  # default

def detect_voice(mode, has_products=False):
    if mode in ("care", "empower"):
        return "ramona"
    if mode == "commerce" and has_products:
        return "tony"
    if mode in ("diagnose", "optimize"):
        return "tony"
    return "ramona"  # default

def split_follow(text):
    if not text:
        return "", None
    sentences = text.split(". ")
    if len(sentences) >= 2:
        last = sentences[-1].strip()
        if last.endswith("?") or any(w in last.lower() for w in ["dime", "cuentame"]):
            return ". ".join(sentences[:-1]) + ".", last
    return text, None  # default follow=None

def enrich_productos_from(productos):
    for p in productos:
        if "from" not in p:
            p["from"] = p.get("vendor", p.get("empresa", ""))  # default from=""
    return productos

# CORRECCION V25.1: Defaults para Chat API
CHAT_DEFAULTS = {"mode": "build", "voice": "ramona", "follow": None, "from": ""}

if __name__ == "__main__":
    mw = get_middleware()
    print("ADN genes:", len(mw.genes))
    print("Frases prohibidas:", len(mw.frases_prohibidas))
    print("Guardian:", mw.guardian_estado)
    pre = mw.pre_operacion({"operacion": "ficha", "empresa": "TEST", "total_productos": 10})
    print("Pre-operacion ficha: permitido=", pre["permitido"])
