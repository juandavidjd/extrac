#!/bin/bash
#===============================================================================
#                    ODI PIPELINE DEPLOYMENT SCRIPT
#                  Auto-deploy and run ODI ingestion pipeline
#===============================================================================
#
# USAGE:
#   ./odi_deploy_pipeline.sh [command] [options]
#
# COMMANDS:
#   deploy      Deploy scripts to server
#   scan        Scan all companies
#   process     Process a specific company
#   all         Process all companies
#   status      Show current status
#
# EXAMPLES:
#   ./odi_deploy_pipeline.sh deploy           # Deploy scripts
#   ./odi_deploy_pipeline.sh scan             # Scan available companies
#   ./odi_deploy_pipeline.sh process Yokomar  # Process Yokomar
#   ./odi_deploy_pipeline.sh all              # Process all companies
#   ./odi_deploy_pipeline.sh all --dry-run    # Dry run all companies
#
#===============================================================================

set -e

# Configuration
REPO_DIR="/tmp/extrac"
SCRIPTS_DIR="/opt/odi/extractors"
DATA_DIR="/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data"
OUTPUT_DIR="/opt/odi/vision_output"
BRANCH="claude/load-repository-branches-Vokmq"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo ""
    echo "========================================================================"
    echo "              ODI PIPELINE DEPLOYMENT & EXECUTION"
    echo "                     Auto-Discovery Engine"
    echo "========================================================================"
    echo ""
}

# Deploy scripts to server
deploy_scripts() {
    log_info "Deploying ODI scripts to server..."

    # Update repository
    if [ -d "$REPO_DIR" ]; then
        log_info "Updating repository..."
        cd "$REPO_DIR"
        git fetch origin "$BRANCH" || log_warning "Could not fetch from origin"
        git checkout "$BRANCH" || log_warning "Could not checkout branch"
        git pull origin "$BRANCH" || log_warning "Could not pull from origin"
    else
        log_info "Cloning repository..."
        git clone -b "$BRANCH" https://github.com/your-repo/extrac.git "$REPO_DIR" || {
            log_error "Failed to clone repository"
            return 1
        }
    fi

    # Create scripts directory
    mkdir -p "$SCRIPTS_DIR"

    # Copy scripts
    log_info "Copying scripts to $SCRIPTS_DIR..."
    cp "$REPO_DIR"/odi_vision_extractor_v3.py "$SCRIPTS_DIR/" 2>/dev/null || true
    cp "$REPO_DIR"/odi_price_list_processor.py "$SCRIPTS_DIR/" 2>/dev/null || true
    cp "$REPO_DIR"/odi_catalog_enricher.py "$SCRIPTS_DIR/" 2>/dev/null || true
    cp "$REPO_DIR"/odi_pipeline_orchestrator.py "$SCRIPTS_DIR/" 2>/dev/null || true
    cp "$REPO_DIR"/odi_semantic_normalizer.py "$SCRIPTS_DIR/" 2>/dev/null || true
    cp "$REPO_DIR"/odi_event_emitter.py "$SCRIPTS_DIR/" 2>/dev/null || true

    # Fix line endings
    log_info "Fixing line endings..."
    sed -i 's/\r$//' "$SCRIPTS_DIR"/*.py 2>/dev/null || true

    # Make executable
    chmod +x "$SCRIPTS_DIR"/*.py

    # Create output directory
    mkdir -p "$OUTPUT_DIR"

    log_success "Deployment complete!"
    log_info "Scripts location: $SCRIPTS_DIR"
    log_info "Output location: $OUTPUT_DIR"
}

# Load environment
load_env() {
    if [ -f "/opt/odi/.env" ]; then
        export $(grep -v '^#' /opt/odi/.env | xargs)
    fi
    export PYTHONPATH="$SCRIPTS_DIR:$PYTHONPATH"
}

# Scan companies
scan_companies() {
    log_info "Scanning companies in $DATA_DIR..."
    load_env

    python3 "$SCRIPTS_DIR/odi_pipeline_orchestrator.py" \
        --scan \
        --data-dir "$DATA_DIR" \
        --output-dir "$OUTPUT_DIR"
}

# Process specific company
process_company() {
    local company="$1"
    shift
    local extra_args="$@"

    if [ -z "$company" ]; then
        log_error "Company name required"
        echo "Usage: $0 process <company_name> [--dry-run]"
        return 1
    fi

    log_info "Processing company: $company"
    load_env

    python3 "$SCRIPTS_DIR/odi_pipeline_orchestrator.py" \
        --company "$company" \
        --data-dir "$DATA_DIR" \
        --output-dir "$OUTPUT_DIR" \
        $extra_args
}

# Process all companies
process_all() {
    local extra_args="$@"

    log_info "Processing all companies..."
    load_env

    python3 "$SCRIPTS_DIR/odi_pipeline_orchestrator.py" \
        --all \
        --data-dir "$DATA_DIR" \
        --output-dir "$OUTPUT_DIR" \
        $extra_args
}

# Show status
show_status() {
    echo ""
    echo "ODI Pipeline Status"
    echo "==================="
    echo ""

    # Check scripts
    echo "Scripts:"
    for script in odi_vision_extractor_v3.py odi_price_list_processor.py odi_catalog_enricher.py odi_semantic_normalizer.py odi_pipeline_orchestrator.py; do
        if [ -f "$SCRIPTS_DIR/$script" ]; then
            echo "  ✓ $script"
        else
            echo "  ✗ $script (missing)"
        fi
    done

    echo ""
    echo "Directories:"
    echo "  Data: $DATA_DIR"
    [ -d "$DATA_DIR" ] && echo "    ✓ exists" || echo "    ✗ not found"

    echo "  Output: $OUTPUT_DIR"
    [ -d "$OUTPUT_DIR" ] && echo "    ✓ exists" || echo "    ✗ not found"

    echo ""
    echo "Environment:"
    [ -n "$OPENAI_API_KEY" ] && echo "  ✓ OPENAI_API_KEY set" || echo "  ✗ OPENAI_API_KEY not set"

    # List company folders
    if [ -d "$DATA_DIR" ]; then
        echo ""
        echo "Company Folders:"
        ls -1 "$DATA_DIR" 2>/dev/null | while read dir; do
            if [ -d "$DATA_DIR/$dir" ]; then
                file_count=$(find "$DATA_DIR/$dir" -maxdepth 1 -type f \( -name "*.pdf" -o -name "*.xlsx" -o -name "*.csv" \) 2>/dev/null | wc -l)
                echo "  • $dir ($file_count files)"
            fi
        done
    fi
}

# List files for a company
list_company_files() {
    local company="$1"

    if [ -z "$company" ]; then
        log_error "Company name required"
        return 1
    fi

    echo ""
    echo "Files for $company:"
    echo "==================="

    ls -la "$DATA_DIR/$company/" 2>/dev/null || {
        log_error "Company directory not found: $DATA_DIR/$company"
        return 1
    }
}

# Main
print_banner

case "$1" in
    deploy)
        deploy_scripts
        ;;
    scan)
        scan_companies
        ;;
    process)
        shift
        process_company "$@"
        ;;
    all)
        shift
        process_all "$@"
        ;;
    status)
        show_status
        ;;
    ls|list)
        shift
        list_company_files "$@"
        ;;
    -h|--help|help)
        echo "Usage: $0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  deploy              Deploy scripts to server"
        echo "  scan                Scan all companies and show report"
        echo "  process <company>   Process a specific company"
        echo "  all                 Process all companies"
        echo "  status              Show current status"
        echo "  ls <company>        List files for a company"
        echo ""
        echo "Options:"
        echo "  --dry-run           Show what would be done without executing"
        echo ""
        echo "Examples:"
        echo "  $0 deploy"
        echo "  $0 scan"
        echo "  $0 process Yokomar"
        echo "  $0 all --dry-run"
        echo "  $0 ls Yokomar"
        ;;
    *)
        # If no command, show help
        if [ -z "$1" ]; then
            show_status
            echo ""
            echo "Run '$0 --help' for usage information"
        else
            log_error "Unknown command: $1"
            echo "Run '$0 --help' for usage information"
            exit 1
        fi
        ;;
esac
