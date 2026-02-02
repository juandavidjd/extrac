#!/bin/bash
#===============================================================================
# Health check de todos los servicios ODI
#===============================================================================

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              ODI Health Check                                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local service=$1
    local status=$(systemctl is-active "$service" 2>/dev/null)

    if [ "$status" = "active" ]; then
        echo -e "  $service: ${GREEN}RUNNING${NC}"
        return 0
    else
        echo -e "  $service: ${RED}STOPPED${NC}"
        return 1
    fi
}

check_endpoint() {
    local name=$1
    local url=$2
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)

    if [ "$response" = "200" ]; then
        echo -e "  $name: ${GREEN}OK${NC} (HTTP $response)"
        return 0
    else
        echo -e "  $name: ${RED}FAIL${NC} (HTTP $response)"
        return 1
    fi
}

echo "[Services]"
check_service "odi-indexer"
check_service "odi-query"
check_service "odi-feedback"
check_service "redis-server"

echo ""
echo "[Endpoints]"
check_endpoint "Query API Health" "http://localhost:8000/health"
check_endpoint "Query API Stats" "http://localhost:8000/stats"

echo ""
echo "[Storage]"
EMBEDDINGS_SIZE=$(du -sh /opt/odi/embeddings 2>/dev/null | cut -f1 || echo "N/A")
LOGS_SIZE=$(du -sh /opt/odi/logs 2>/dev/null | cut -f1 || echo "N/A")
echo "  Embeddings: $EMBEDDINGS_SIZE"
echo "  Logs: $LOGS_SIZE"

echo ""
echo "[Redis]"
if redis-cli ping > /dev/null 2>&1; then
    QUERIES=$(redis-cli llen odi:queries 2>/dev/null || echo "0")
    FEEDBACKS=$(redis-cli llen odi:feedbacks 2>/dev/null || echo "0")
    echo -e "  Connection: ${GREEN}OK${NC}"
    echo "  Total queries: $QUERIES"
    echo "  Total feedbacks: $FEEDBACKS"
else
    echo -e "  Connection: ${RED}FAILED${NC}"
fi

echo ""
echo "[Profesion Volume]"
if [ -d "/mnt/volume_sfo3_01/profesion" ]; then
    FILE_COUNT=$(find /mnt/volume_sfo3_01/profesion -type f 2>/dev/null | wc -l)
    echo -e "  Mount: ${GREEN}OK${NC}"
    echo "  Files: $FILE_COUNT"
else
    echo -e "  Mount: ${YELLOW}NOT MOUNTED${NC}"
fi

echo ""
