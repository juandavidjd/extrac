#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# HARDENING v1.9 — ODI Server Security
# ═══════════════════════════════════════════════════════════════════════════════
# Servidor: 64.23.170.118
# Ejecutar como: sudo bash hardening-v1.9.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "HARDENING v1.9 — ODI Server Security"
echo "═══════════════════════════════════════════════════════════════════════════════"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok() { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Verificar root
if [ "$EUID" -ne 0 ]; then
    fail "Ejecutar como root: sudo bash hardening-v1.9.sh"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# FASE 1: Crear usuario odi
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[1/8] Creando usuario odi..."

if id "odi" &>/dev/null; then
    ok "Usuario odi ya existe"
else
    adduser --disabled-password --gecos "ODI System User" odi
    usermod -aG sudo odi
    ok "Usuario odi creado"
fi

# Verificar grupos
if groups odi | grep -q sudo; then
    ok "Usuario odi en grupo sudo"
else
    fail "Usuario odi NO está en grupo sudo"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# FASE 2: Configurar SSH keys
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[2/8] Configurando SSH keys..."

mkdir -p /home/odi/.ssh
chmod 700 /home/odi/.ssh
touch /home/odi/.ssh/authorized_keys
chmod 600 /home/odi/.ssh/authorized_keys
chown -R odi:odi /home/odi/.ssh

# Copiar keys de root si existen
if [ -f /root/.ssh/authorized_keys ]; then
    cat /root/.ssh/authorized_keys >> /home/odi/.ssh/authorized_keys
    sort -u /home/odi/.ssh/authorized_keys -o /home/odi/.ssh/authorized_keys
    ok "Keys copiadas de root a odi"
else
    warn "No hay keys en /root/.ssh/authorized_keys"
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════════════╗"
    echo "║ ACCIÓN MANUAL REQUERIDA:                                                  ║"
    echo "║ Pega tu llave pública SSH en: /home/odi/.ssh/authorized_keys              ║"
    echo "║ Comando: nano /home/odi/.ssh/authorized_keys                              ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════╝"
    echo ""
    read -p "Presiona ENTER cuando hayas pegado la llave..."
fi

# ═══════════════════════════════════════════════════════════════════════════════
# FASE 3: Test SSH antes de cerrar root
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[3/8] Verificación SSH..."
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║ VERIFICACIÓN CRÍTICA:                                                     ║"
echo "║ Abre OTRA terminal y ejecuta: ssh odi@64.23.170.118                       ║"
echo "║ Debe entrar SIN pedir password.                                           ║"
echo "║ Luego ejecuta: sudo whoami (debe responder 'root')                        ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""
read -p "¿Funciona ssh odi@64.23.170.118? (s/n): " SSH_OK

if [ "$SSH_OK" != "s" ]; then
    fail "NO continuar sin verificar SSH. Corregir keys primero."
fi
ok "SSH verificado por operador"

# ═══════════════════════════════════════════════════════════════════════════════
# FASE 4: Endurecer sshd_config
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[4/8] Endureciendo SSH..."

# Backup
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%F_%H%M)
ok "Backup de sshd_config creado"

# Modificar configuración
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#*ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' /etc/ssh/sshd_config

# Verificar que las líneas existen
grep -q "^PermitRootLogin no" /etc/ssh/sshd_config || echo "PermitRootLogin no" >> /etc/ssh/sshd_config
grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config || echo "PasswordAuthentication no" >> /etc/ssh/sshd_config
grep -q "^PubkeyAuthentication yes" /etc/ssh/sshd_config || echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config

# Validar sintaxis
sshd -t || fail "Error en sshd_config"

# Reiniciar SSH
systemctl restart ssh
ok "SSH endurecido (root login deshabilitado)"

# ═══════════════════════════════════════════════════════════════════════════════
# FASE 5: Instalar y configurar Fail2Ban
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[5/8] Configurando Fail2Ban..."

apt-get update -qq
apt-get install -y fail2ban

cat >/etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
maxretry = 5
findtime = 10m
bantime = 1h
EOF

systemctl enable fail2ban
systemctl restart fail2ban

if fail2ban-client status sshd &>/dev/null; then
    ok "Fail2Ban activo (ban 1h después de 5 intentos)"
else
    warn "Fail2Ban instalado pero jail sshd no activo"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# FASE 6: Endurecer permisos ODI
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[6/8] Endureciendo permisos /opt/odi..."

chown -R odi:odi /opt/odi

# Credentials
if [ -d /opt/odi/credentials ]; then
    chmod 700 /opt/odi/credentials
    chmod 600 /opt/odi/credentials/*.json 2>/dev/null || true
    ok "Permisos credentials: 700/600"
else
    mkdir -p /opt/odi/credentials
    chmod 700 /opt/odi/credentials
    chown odi:odi /opt/odi/credentials
    warn "Directorio credentials creado"
fi

# .env
if [ -f /opt/odi/.env ]; then
    chmod 600 /opt/odi/.env
    ok "Permisos .env: 600"
else
    warn ".env no encontrado"
fi

# Logs
mkdir -p /opt/odi/logs
chown -R odi:odi /opt/odi/logs
chmod 750 /opt/odi/logs
ok "Permisos logs: 750"

# ═══════════════════════════════════════════════════════════════════════════════
# FASE 7: Instalar security_guard y pii_redactor
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[7/8] Instalando módulos de seguridad..."

# Verificar que los archivos existen
if [ -f /opt/odi/core/security_guard.py ]; then
    ok "security_guard.py presente"
else
    fail "security_guard.py NO encontrado. Ejecutar git pull primero."
fi

if [ -f /opt/odi/core/pii_redactor.py ]; then
    ok "pii_redactor.py presente"
else
    fail "pii_redactor.py NO encontrado. Ejecutar git pull primero."
fi

# Inyectar en odi_core.py si existe
if [ -f /opt/odi/core/odi_core.py ]; then
    if grep -q "enforce_sovereignty" /opt/odi/core/odi_core.py; then
        ok "enforce_sovereignty ya inyectado en odi_core.py"
    else
        # Insertar después de los imports
        sed -i '/^from dotenv/a\\nfrom core.security_guard import enforce_sovereignty\nenforce_sovereignty()' /opt/odi/core/odi_core.py 2>/dev/null || \
        sed -i '1a\from core.security_guard import enforce_sovereignty\nenforce_sovereignty()' /opt/odi/core/odi_core.py
        ok "enforce_sovereignty inyectado en odi_core.py"
    fi
else
    warn "odi_core.py no encontrado. Inyectar enforce_sovereignty manualmente."
fi

# ═══════════════════════════════════════════════════════════════════════════════
# FASE 8: Verificación final
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[8/8] Verificación final..."
echo ""

REPORT=""

# Test 1: Permisos .env
if [ -f /opt/odi/.env ]; then
    PERM=$(stat -c %a /opt/odi/.env)
    if [ "$PERM" = "600" ]; then
        REPORT="${REPORT}1. .env permisos 600: ${GREEN}OK${NC}\n"
    else
        REPORT="${REPORT}1. .env permisos $PERM: ${RED}FAIL${NC}\n"
    fi
else
    REPORT="${REPORT}1. .env: ${YELLOW}NO EXISTE${NC}\n"
fi

# Test 2: Permisos credentials
if [ -d /opt/odi/credentials ]; then
    PERM=$(stat -c %a /opt/odi/credentials)
    if [ "$PERM" = "700" ]; then
        REPORT="${REPORT}2. credentials/ permisos 700: ${GREEN}OK${NC}\n"
    else
        REPORT="${REPORT}2. credentials/ permisos $PERM: ${RED}FAIL${NC}\n"
    fi
else
    REPORT="${REPORT}2. credentials/: ${YELLOW}NO EXISTE${NC}\n"
fi

# Test 3: Fail2Ban
if fail2ban-client status sshd &>/dev/null; then
    REPORT="${REPORT}3. Fail2Ban sshd: ${GREEN}OK${NC}\n"
else
    REPORT="${REPORT}3. Fail2Ban sshd: ${RED}FAIL${NC}\n"
fi

# Test 4: SSH root disabled
if grep -q "^PermitRootLogin no" /etc/ssh/sshd_config; then
    REPORT="${REPORT}4. PermitRootLogin no: ${GREEN}OK${NC}\n"
else
    REPORT="${REPORT}4. PermitRootLogin: ${RED}FAIL${NC}\n"
fi

# Test 5: Password auth disabled
if grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config; then
    REPORT="${REPORT}5. PasswordAuth no: ${GREEN}OK${NC}\n"
else
    REPORT="${REPORT}5. PasswordAuth: ${RED}FAIL${NC}\n"
fi

# Test 6: security_guard presente
if [ -f /opt/odi/core/security_guard.py ]; then
    REPORT="${REPORT}6. security_guard.py: ${GREEN}OK${NC}\n"
else
    REPORT="${REPORT}6. security_guard.py: ${RED}FAIL${NC}\n"
fi

# Test 7: pii_redactor presente
if [ -f /opt/odi/core/pii_redactor.py ]; then
    REPORT="${REPORT}7. pii_redactor.py: ${GREEN}OK${NC}\n"
else
    REPORT="${REPORT}7. pii_redactor.py: ${RED}FAIL${NC}\n"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "REPORTE HARDENING v1.9"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo -e "$REPORT"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}FORTALEZA v1.9 SELLADA${NC}"
echo ""
echo "Próximo paso: v1.9.1 (backups GPG + snapshots + restore drill)"
echo ""
