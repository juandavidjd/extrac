#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# Test Tourism Endpoints — Smoke Test para módulo Industria Turismo
# ═══════════════════════════════════════════════════════════════════════════════
# Uso: bash scripts/tests/test_tourism_endpoints.sh [host]
# Default: http://localhost:8800

set -euo pipefail

HOST="${1:-http://localhost:8800}"
PASS=0
FAIL=0

green() { printf "\033[0;32m%s\033[0m\n" "$1"; }
red()   { printf "\033[0;31m%s\033[0m\n" "$1"; }
bold()  { printf "\033[1m%s\033[0m\n" "$1"; }

check() {
    local name="$1"
    local code="$2"
    if [ "$code" -ge 200 ] && [ "$code" -lt 300 ]; then
        green "  ✓ $name (HTTP $code)"
        PASS=$((PASS + 1))
    else
        red   "  ✗ $name (HTTP $code)"
        FAIL=$((FAIL + 1))
    fi
}

bold "═══════════════════════════════════════════════════════"
bold " ODI Tourism Module — Smoke Tests"
bold " Target: $HOST"
bold "═══════════════════════════════════════════════════════"
echo ""

# ── 1. Health Check ───────────────────────────────────────────────────────
bold "[1/6] Health Check"
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HOST/tourism/health")
check "GET /tourism/health" "$CODE"
echo ""

# ── 2. Clinic Capacity ───────────────────────────────────────────────────
bold "[2/6] Clinic Capacity"
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HOST/tourism/capacity/matzu_001")
check "GET /tourism/capacity/matzu_001" "$CODE"
echo ""

# ── 3. Assign Doctor ─────────────────────────────────────────────────────
bold "[3/6] Assign Doctor (SLA)"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$HOST/tourism/assign" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "matzu_001",
    "procedure_id": "carillas_porcelana"
  }')
CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | head -n -1)
check "POST /tourism/assign" "$CODE"
echo "  Response: $(echo "$BODY" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f"doctor={d.get(\"assigned_doctor_id\",\"?\")}, reason={d.get(\"reason\",\"?\")}") ' 2>/dev/null || echo "$BODY")"
echo ""

# ── 4. Create Tourism Plan (Miami → Pereira, Carillas) ──────────────────
bold "[4/6] Create Full Tourism Plan"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$HOST/tourism/plan" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "matzu_001",
    "procedure_id": "carillas_porcelana",
    "origin_city": "Miami, FL",
    "budget_tier": "premium",
    "arrival_date": "2026-03-10",
    "stay_days": 5,
    "lead_id": "test_lead_001"
  }')
CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | head -n -1)
check "POST /tourism/plan" "$CODE"
echo "  Response: $(echo "$BODY" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f"txn={d.get(\"transaction_id\",\"?\")}, status={d.get(\"status\",\"?\")}, priority={d.get(\"priority\",\"?\")}") ' 2>/dev/null || echo "$BODY")"
echo ""

# ── 5. Create Plan sin vuelos (paciente local) ──────────────────────────
bold "[5/6] Create Plan (Local, sin vuelos)"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$HOST/tourism/plan" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "matzu_001",
    "procedure_id": "implantes_dentales",
    "budget_tier": "economy",
    "stay_days": 7
  }')
check "POST /tourism/plan (local)" "$CODE"
echo ""

# ── 6. Lead Scoring ──────────────────────────────────────────────────────
bold "[6/6] Lead Scoring"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$HOST/tourism/score" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "matzu_001",
    "procedure_id": "diseno_sonrisa",
    "origin_city": "JFK",
    "budget_tier": "premium",
    "arrival_date": "2026-02-20"
  }')
CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | head -n -1)
check "POST /tourism/score" "$CODE"
echo "  Response: $(echo "$BODY" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f"priority={d.get(\"priority_label\",\"?\")}, reasons={len(d.get(\"reasons\",[]))} items") ' 2>/dev/null || echo "$BODY")"
echo ""

# ── RESUMEN ──────────────────────────────────────────────────────────────
bold "═══════════════════════════════════════════════════════"
bold " RESULTADO: $PASS passed, $FAIL failed"
bold "═══════════════════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
