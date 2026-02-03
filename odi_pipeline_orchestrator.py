#!/usr/bin/env python3
"""
==============================================================================
                    ODI PIPELINE ORCHESTRATOR v1.0
              Auto-Discovery & Execution Engine for ODI Ingestion
==============================================================================

DESCRIPTION:
    Scans company data directories, detects available files (PDF catalogs,
    price lists, XLSX, CSV), and automatically launches the appropriate
    ingestion pipeline for each company.

ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                    ODI PIPELINE ORCHESTRATOR                             │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                          │
    │  [DATA DIRECTORY]                                                        │
    │       │                                                                  │
    │       ├── Yokomar/                                                       │
    │       │    ├── CATALOGO ACTUALIZADO.pdf  → Vision Extractor             │
    │       │    ├── LISTA_DE_PRECIOS.pdf      → Price Processor              │
    │       │    ├── precios.xlsx              → Excel Parser                 │
    │       │    └── base_datos.csv            → CSV Parser                   │
    │       │                                                                  │
    │       ├── Vitton/                                                        │
    │       │    ├── catalogo.pdf              → Vision Extractor             │
    │       │    └── precios.csv               → CSV Parser                   │
    │       │                                                                  │
    │       └── ...                                                            │
    │                                                                          │
    │  DETECTION → CLASSIFICATION → PIPELINE EXECUTION → ENRICHMENT           │
    │                                                                          │
    └─────────────────────────────────────────────────────────────────────────┘

USAGE:
    # Scan all companies and show what would be processed
    python3 odi_pipeline_orchestrator.py --scan

    # Process a specific company
    python3 odi_pipeline_orchestrator.py --company Yokomar

    # Process all companies
    python3 odi_pipeline_orchestrator.py --all

    # Dry run (show what would be done without executing)
    python3 odi_pipeline_orchestrator.py --all --dry-run

AUTHOR: ODI Team
VERSION: 1.0
==============================================================================
"""

import os
import sys
import json
import re
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum


# ==============================================================================
# CONFIGURATION
# ==============================================================================

VERSION = "1.1"
SCRIPT_NAME = "ODI Pipeline Orchestrator"

# Default data directory
DEFAULT_DATA_DIR = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data"

# Output directory
DEFAULT_OUTPUT_DIR = "/opt/odi/vision_output"

# Scripts location
SCRIPTS_DIR = "/opt/odi/extractors"
FALLBACK_SCRIPTS_DIR = "/tmp/extrac"

# File classification patterns
CATALOG_PATTERNS = [
    r'catalogo',
    r'catalog',
    r'productos',
    r'products',
]

PRICE_LIST_PATTERNS = [
    r'lista.*precio',
    r'price.*list',
    r'precios',
    r'prices',
    r'tarifa',
]

# File extensions
PDF_EXTENSIONS = ['.pdf']
EXCEL_EXTENSIONS = ['.xlsx', '.xls']
CSV_EXTENSIONS = ['.csv']

# Size thresholds (bytes)
MIN_CATALOG_SIZE = 1_000_000  # 1MB - catalogs are usually large
MIN_PRICE_LIST_SIZE = 10_000  # 10KB - price lists can be smaller


# ==============================================================================
# ENUMS & DATA CLASSES
# ==============================================================================

class FileType(Enum):
    """Type of file detected."""
    CATALOG_PDF = "catalog_pdf"
    PRICE_LIST_PDF = "price_list_pdf"
    PRICE_LIST_XLSX = "price_list_xlsx"
    PRICE_LIST_CSV = "price_list_csv"
    DATA_CSV = "data_csv"
    DATA_XLSX = "data_xlsx"
    UNKNOWN = "unknown"


class PipelineStatus(Enum):
    """Status of pipeline execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DetectedFile:
    """Information about a detected file."""
    path: Path
    name: str
    file_type: FileType
    size_bytes: int
    size_mb: float
    extension: str
    is_catalog: bool = False
    is_price_list: bool = False
    confidence: float = 0.0

    def __post_init__(self):
        self.size_mb = round(self.size_bytes / (1024 * 1024), 2)


@dataclass
class CompanyData:
    """Data structure for a company's detected files."""
    name: str
    path: Path
    prefix: str
    catalogs: List[DetectedFile] = field(default_factory=list)
    price_lists: List[DetectedFile] = field(default_factory=list)
    data_files: List[DetectedFile] = field(default_factory=list)
    total_files: int = 0
    has_catalog: bool = False
    has_prices: bool = False
    ready_for_pipeline: bool = False

    def __post_init__(self):
        self.prefix = self._generate_prefix()

    def _generate_prefix(self) -> str:
        """Generate a prefix from company name."""
        name = self.name.upper()
        # Remove special characters
        name = re.sub(r'[^A-Z0-9]', '', name)
        return name[:10] if len(name) > 10 else name


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    company: str
    status: PipelineStatus
    catalog_extracted: bool = False
    products_count: int = 0
    prices_loaded: int = 0
    enriched: bool = False
    normalized: bool = False
    duplicates_found: int = 0
    families_created: int = 0
    output_file: str = ""
    error: str = ""
    duration_seconds: float = 0.0


# ==============================================================================
# LOGGER
# ==============================================================================

class Logger:
    """Logger with colors and formatting."""

    COLORS = {
        "info": "\033[94m",      # Blue
        "success": "\033[92m",   # Green
        "warning": "\033[93m",   # Yellow
        "error": "\033[91m",     # Red
        "debug": "\033[90m",     # Gray
        "header": "\033[95m",    # Magenta
        "bold": "\033[1m",
        "reset": "\033[0m"
    }

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def log(self, message: str, level: str = "info"):
        color = self.COLORS.get(level, "")
        reset = self.COLORS["reset"]
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {color}{message}{reset}")

    def header(self, title: str):
        bold = self.COLORS["bold"]
        reset = self.COLORS["reset"]
        print(f"\n{bold}{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}{reset}\n")

    def section(self, title: str):
        print(f"\n{self.COLORS['header']}▸ {title}{self.COLORS['reset']}")

    def item(self, text: str, indent: int = 2):
        spaces = " " * indent
        print(f"{spaces}• {text}")

log = Logger()


# ==============================================================================
# FILE CLASSIFIER
# ==============================================================================

class FileClassifier:
    """Classifies files based on name, extension, and size."""

    def __init__(self):
        self.catalog_patterns = [re.compile(p, re.IGNORECASE) for p in CATALOG_PATTERNS]
        self.price_patterns = [re.compile(p, re.IGNORECASE) for p in PRICE_LIST_PATTERNS]

    def classify(self, file_path: Path) -> DetectedFile:
        """Classify a single file."""
        name = file_path.name
        ext = file_path.suffix.lower()
        size = file_path.stat().st_size if file_path.exists() else 0

        file_type = FileType.UNKNOWN
        is_catalog = False
        is_price_list = False
        confidence = 0.0

        # Check name patterns
        name_lower = name.lower()

        # Catalog detection
        for pattern in self.catalog_patterns:
            if pattern.search(name_lower):
                is_catalog = True
                confidence += 0.4
                break

        # Price list detection
        for pattern in self.price_patterns:
            if pattern.search(name_lower):
                is_price_list = True
                confidence += 0.4
                break

        # Extension-based classification
        if ext in PDF_EXTENSIONS:
            if is_catalog and size >= MIN_CATALOG_SIZE:
                file_type = FileType.CATALOG_PDF
                confidence += 0.3
            elif is_price_list:
                file_type = FileType.PRICE_LIST_PDF
                confidence += 0.3
            elif size >= MIN_CATALOG_SIZE:
                # Large PDF without clear name pattern - likely catalog
                file_type = FileType.CATALOG_PDF
                is_catalog = True
                confidence += 0.2
            else:
                file_type = FileType.PRICE_LIST_PDF
                is_price_list = True
                confidence += 0.1

        elif ext in EXCEL_EXTENSIONS:
            if is_price_list:
                file_type = FileType.PRICE_LIST_XLSX
                confidence += 0.3
            else:
                file_type = FileType.DATA_XLSX
                confidence += 0.2

        elif ext in CSV_EXTENSIONS:
            if is_price_list:
                file_type = FileType.PRICE_LIST_CSV
                confidence += 0.3
            else:
                file_type = FileType.DATA_CSV
                confidence += 0.2

        return DetectedFile(
            path=file_path,
            name=name,
            file_type=file_type,
            size_bytes=size,
            size_mb=0,
            extension=ext,
            is_catalog=is_catalog,
            is_price_list=is_price_list,
            confidence=min(confidence, 1.0)
        )


# ==============================================================================
# COMPANY SCANNER
# ==============================================================================

class CompanyScanner:
    """Scans company directories for processable files."""

    SUPPORTED_EXTENSIONS = PDF_EXTENSIONS + EXCEL_EXTENSIONS + CSV_EXTENSIONS

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)
        self.classifier = FileClassifier()

    def scan_directory(self, company_path: Path) -> CompanyData:
        """Scan a single company directory."""
        company = CompanyData(
            name=company_path.name,
            path=company_path,
            prefix=""
        )

        if not company_path.exists() or not company_path.is_dir():
            return company

        # Scan all files in directory
        files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            files.extend(company_path.glob(f"*{ext}"))
            files.extend(company_path.glob(f"*{ext.upper()}"))

        company.total_files = len(files)

        # Classify each file
        for file_path in files:
            if not file_path.is_file():
                continue

            detected = self.classifier.classify(file_path)

            if detected.file_type == FileType.CATALOG_PDF:
                company.catalogs.append(detected)
                company.has_catalog = True

            elif detected.file_type in [FileType.PRICE_LIST_PDF,
                                         FileType.PRICE_LIST_XLSX,
                                         FileType.PRICE_LIST_CSV]:
                company.price_lists.append(detected)
                company.has_prices = True

            elif detected.file_type in [FileType.DATA_XLSX, FileType.DATA_CSV]:
                company.data_files.append(detected)
                # Data files might contain prices
                company.has_prices = True

        # Determine if ready for pipeline
        company.ready_for_pipeline = company.has_catalog or company.has_prices

        return company

    def scan_all(self) -> List[CompanyData]:
        """Scan all company directories."""
        if not self.data_dir.exists():
            log.log(f"Data directory not found: {self.data_dir}", "error")
            return []

        companies = []

        for entry in sorted(self.data_dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith('.'):
                company = self.scan_directory(entry)
                if company.total_files > 0:
                    companies.append(company)

        return companies

    def print_scan_report(self, companies: List[CompanyData]):
        """Print a detailed scan report."""
        log.header("ODI PIPELINE ORCHESTRATOR - SCAN REPORT")

        print(f"Data Directory: {self.data_dir}")
        print(f"Companies Found: {len(companies)}")

        ready_count = sum(1 for c in companies if c.ready_for_pipeline)
        print(f"Ready for Pipeline: {ready_count}")
        print()

        for company in companies:
            status = "✓" if company.ready_for_pipeline else "○"
            color = "\033[92m" if company.ready_for_pipeline else "\033[90m"
            reset = "\033[0m"

            print(f"{color}{status} {company.name} [{company.prefix}]{reset}")
            print(f"    Path: {company.path}")
            print(f"    Total Files: {company.total_files}")

            if company.catalogs:
                print(f"    📕 Catalogs ({len(company.catalogs)}):")
                for cat in company.catalogs:
                    print(f"       - {cat.name} ({cat.size_mb}MB)")

            if company.price_lists:
                print(f"    💰 Price Lists ({len(company.price_lists)}):")
                for pl in company.price_lists:
                    print(f"       - {pl.name} ({cat.size_mb}MB) [{pl.file_type.value}]")

            if company.data_files:
                print(f"    📊 Data Files ({len(company.data_files)}):")
                for df in company.data_files:
                    print(f"       - {df.name} [{df.file_type.value}]")

            print()

        # Summary
        log.section("SUMMARY")
        print(f"  Companies with catalogs: {sum(1 for c in companies if c.has_catalog)}")
        print(f"  Companies with prices: {sum(1 for c in companies if c.has_prices)}")
        print(f"  Ready for full pipeline: {ready_count}")


# ==============================================================================
# PIPELINE EXECUTOR
# ==============================================================================

class PipelineExecutor:
    """Executes the ODI ingestion pipeline for companies."""

    def __init__(self, output_dir: str = DEFAULT_OUTPUT_DIR,
                 scripts_dir: str = SCRIPTS_DIR,
                 dry_run: bool = False):
        self.output_dir = Path(output_dir)
        self.scripts_dir = Path(scripts_dir)
        self.dry_run = dry_run

        # Find scripts
        self._locate_scripts()

    def _locate_scripts(self):
        """Locate the required scripts."""
        self.vision_extractor = None
        self.price_processor = None
        self.catalog_enricher = None
        self.semantic_normalizer = None

        # Try primary location
        for scripts_path in [self.scripts_dir, Path(FALLBACK_SCRIPTS_DIR)]:
            if scripts_path.exists():
                vision = scripts_path / "odi_vision_extractor_v3.py"
                price = scripts_path / "odi_price_list_processor.py"
                enricher = scripts_path / "odi_catalog_enricher.py"
                normalizer = scripts_path / "odi_semantic_normalizer.py"

                if vision.exists():
                    self.vision_extractor = vision
                if price.exists():
                    self.price_processor = price
                if enricher.exists():
                    self.catalog_enricher = enricher
                if normalizer.exists():
                    self.semantic_normalizer = normalizer

                if self.vision_extractor:
                    break

        # Also check current directory
        cwd = Path.cwd()
        if not self.vision_extractor and (cwd / "odi_vision_extractor_v3.py").exists():
            self.vision_extractor = cwd / "odi_vision_extractor_v3.py"
            self.price_processor = cwd / "odi_price_list_processor.py"
            self.catalog_enricher = cwd / "odi_catalog_enricher.py"
            self.semantic_normalizer = cwd / "odi_semantic_normalizer.py"

    def execute_company(self, company: CompanyData) -> PipelineResult:
        """Execute the full pipeline for a company."""
        result = PipelineResult(
            company=company.name,
            status=PipelineStatus.PENDING
        )

        start_time = datetime.now()

        log.header(f"PROCESSING: {company.name}")
        log.log(f"Prefix: {company.prefix}")
        log.log(f"Path: {company.path}")

        # Create output directory
        company_output = self.output_dir / company.name
        if not self.dry_run:
            company_output.mkdir(parents=True, exist_ok=True)

        try:
            result.status = PipelineStatus.RUNNING

            # Step 1: Extract catalog if available
            if company.catalogs and self.vision_extractor:
                log.section("STEP 1: Catalog Extraction")

                # Use the largest catalog (most likely the main one)
                main_catalog = max(company.catalogs, key=lambda x: x.size_bytes)
                log.log(f"Processing: {main_catalog.name} ({main_catalog.size_mb}MB)")

                if not self.dry_run:
                    success, products = self._run_vision_extractor(
                        main_catalog.path,
                        company.prefix,
                        company_output
                    )
                    result.catalog_extracted = success
                    result.products_count = products
                else:
                    log.log(f"[DRY RUN] Would extract catalog: {main_catalog.name}")
                    result.catalog_extracted = True

            # Step 2: Process price lists
            if company.price_lists and self.price_processor:
                log.section("STEP 2: Price List Processing")

                for price_file in company.price_lists:
                    log.log(f"Processing: {price_file.name}")

                    if not self.dry_run:
                        prices = self._run_price_processor(
                            price_file.path,
                            company.prefix,
                            company_output
                        )
                        result.prices_loaded += prices
                    else:
                        log.log(f"[DRY RUN] Would process: {price_file.name}")
                        result.prices_loaded += 100  # Simulated

            # Step 3: Process additional data files
            if company.data_files:
                log.section("STEP 3: Additional Data Files")

                for data_file in company.data_files:
                    log.log(f"Found: {data_file.name} [{data_file.file_type.value}]")
                    # These will be picked up by the enricher

            # Step 4: Enrich catalog with prices
            if result.catalog_extracted and (result.prices_loaded > 0 or company.data_files):
                log.section("STEP 4: Catalog Enrichment")

                catalog_csv = company_output / f"{company.prefix}_catalogo.csv"

                if not self.dry_run:
                    if catalog_csv.exists():
                        enriched = self._run_catalog_enricher(
                            catalog_csv,
                            company.path,
                            company_output
                        )
                        result.enriched = enriched
                        if enriched:
                            result.output_file = str(
                                company_output / f"{company.prefix}_catalogo_enriched.csv"
                            )
                else:
                    log.log(f"[DRY RUN] Would enrich catalog")
                    result.enriched = True
                    result.output_file = str(
                        company_output / f"{company.prefix}_catalogo_enriched.csv"
                    )

            # Step 5: Semantic Normalization
            if result.enriched and self.semantic_normalizer:
                log.section("STEP 5: Semantic Normalization")

                enriched_csv = company_output / f"{company.prefix}_catalogo_enriched.csv"

                if not self.dry_run:
                    if enriched_csv.exists():
                        normalized, duplicates, families = self._run_semantic_normalizer(
                            enriched_csv,
                            company_output
                        )
                        result.normalized = normalized
                        result.duplicates_found = duplicates
                        result.families_created = families
                        if normalized:
                            result.output_file = str(
                                company_output / f"{company.prefix}_catalogo_enriched_normalized.csv"
                            )
                else:
                    log.log(f"[DRY RUN] Would run semantic normalization")
                    result.normalized = True

            result.status = PipelineStatus.COMPLETED

        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.error = str(e)
            log.log(f"Pipeline failed: {e}", "error")

        result.duration_seconds = (datetime.now() - start_time).total_seconds()

        # Print result summary
        self._print_result_summary(result)

        return result

    def _run_vision_extractor(self, pdf_path: Path, prefix: str,
                               output_dir: Path) -> Tuple[bool, int]:
        """Run the vision extractor script."""
        if not self.vision_extractor or not self.vision_extractor.exists():
            log.log("Vision extractor not found", "warning")
            return False, 0

        cmd = [
            "python3", str(self.vision_extractor),
            str(pdf_path),
            "all",
            "--prefix", prefix,
            "--output", str(output_dir),
            "--enrich"
        ]

        log.log(f"Running: {' '.join(cmd[:4])}...")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                # Try to extract product count from output
                match = re.search(r'(\d+)\s+productos', result.stdout)
                products = int(match.group(1)) if match else 0
                log.log(f"Extraction completed: {products} products", "success")
                return True, products
            else:
                log.log(f"Extraction failed: {result.stderr[:200]}", "error")
                return False, 0

        except subprocess.TimeoutExpired:
            log.log("Extraction timed out", "error")
            return False, 0
        except Exception as e:
            log.log(f"Extraction error: {e}", "error")
            return False, 0

    def _run_price_processor(self, file_path: Path, prefix: str,
                              output_dir: Path) -> int:
        """Run the price list processor."""
        if not self.price_processor or not self.price_processor.exists():
            log.log("Price processor not found", "warning")
            return 0

        output_file = output_dir / f"{prefix}_precios.csv"

        cmd = [
            "python3", str(self.price_processor),
            str(file_path),
            "--prefix", prefix,
            "--output", str(output_file)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 min timeout
            )

            if result.returncode == 0:
                # Try to extract price count
                match = re.search(r'(\d+)\s+precios', result.stdout)
                prices = int(match.group(1)) if match else 0
                log.log(f"Prices extracted: {prices}", "success")
                return prices
            else:
                log.log(f"Price processing failed", "warning")
                return 0

        except Exception as e:
            log.log(f"Price processing error: {e}", "error")
            return 0

    def _run_catalog_enricher(self, catalog_path: Path, data_dir: Path,
                               output_dir: Path) -> bool:
        """Run the catalog enricher."""
        if not self.catalog_enricher or not self.catalog_enricher.exists():
            log.log("Catalog enricher not found", "warning")
            return False

        output_file = catalog_path.with_stem(catalog_path.stem + "_enriched")

        cmd = [
            "python3", str(self.catalog_enricher),
            str(catalog_path),
            str(data_dir),
            "--output", str(output_file)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 min timeout
            )

            if result.returncode == 0:
                log.log(f"Catalog enriched successfully", "success")
                return True
            else:
                log.log(f"Enrichment failed", "warning")
                return False

        except Exception as e:
            log.log(f"Enrichment error: {e}", "error")
            return False

    def _run_semantic_normalizer(self, catalog_path: Path,
                                  output_dir: Path) -> Tuple[bool, int, int]:
        """Run the semantic normalizer."""
        if not self.semantic_normalizer or not self.semantic_normalizer.exists():
            log.log("Semantic normalizer not found", "warning")
            return False, 0, 0

        output_file = catalog_path.with_stem(catalog_path.stem + "_normalized")

        cmd = [
            "python3", str(self.semantic_normalizer),
            str(catalog_path),
            "-o", str(output_file)
        ]

        log.log(f"Running semantic normalization...")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 min timeout (embeddings can be slow)
            )

            if result.returncode == 0:
                # Extract stats from output
                duplicates = 0
                families = 0

                dup_match = re.search(r'Duplicados detectados:\s*(\d+)', result.stdout)
                if dup_match:
                    duplicates = int(dup_match.group(1))

                fam_match = re.search(r'Familias creadas:\s*(\d+)', result.stdout)
                if fam_match:
                    families = int(fam_match.group(1))

                log.log(f"Normalization completed: {duplicates} duplicates, {families} families", "success")
                return True, duplicates, families
            else:
                log.log(f"Normalization failed: {result.stderr[:200]}", "warning")
                return False, 0, 0

        except subprocess.TimeoutExpired:
            log.log("Normalization timed out", "error")
            return False, 0, 0
        except Exception as e:
            log.log(f"Normalization error: {e}", "error")
            return False, 0, 0

    def _print_result_summary(self, result: PipelineResult):
        """Print a summary of the pipeline result."""
        log.section("RESULT SUMMARY")

        status_colors = {
            PipelineStatus.COMPLETED: "\033[92m",
            PipelineStatus.FAILED: "\033[91m",
            PipelineStatus.SKIPPED: "\033[93m",
        }

        color = status_colors.get(result.status, "\033[0m")
        reset = "\033[0m"

        print(f"  Status: {color}{result.status.value.upper()}{reset}")
        print(f"  Catalog Extracted: {'Yes' if result.catalog_extracted else 'No'}")
        print(f"  Products Found: {result.products_count}")
        print(f"  Prices Loaded: {result.prices_loaded}")
        print(f"  Enriched: {'Yes' if result.enriched else 'No'}")
        print(f"  Normalized: {'Yes' if result.normalized else 'No'}")
        if result.normalized:
            print(f"  Duplicates Found: {result.duplicates_found}")
            print(f"  Families Created: {result.families_created}")
        print(f"  Duration: {result.duration_seconds:.1f}s")

        if result.output_file:
            print(f"  Output: {result.output_file}")

        if result.error:
            print(f"  Error: {result.error}")


# ==============================================================================
# MAIN ORCHESTRATOR
# ==============================================================================

class ODIPipelineOrchestrator:
    """Main orchestrator for the ODI ingestion pipeline."""

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR,
                 output_dir: str = DEFAULT_OUTPUT_DIR,
                 dry_run: bool = False):
        self.scanner = CompanyScanner(data_dir)
        self.executor = PipelineExecutor(output_dir, dry_run=dry_run)
        self.dry_run = dry_run

    def scan(self) -> List[CompanyData]:
        """Scan all companies and print report."""
        companies = self.scanner.scan_all()
        self.scanner.print_scan_report(companies)
        return companies

    def process_company(self, company_name: str) -> Optional[PipelineResult]:
        """Process a specific company by name."""
        companies = self.scanner.scan_all()

        # Find company (case insensitive)
        company = None
        for c in companies:
            if c.name.lower() == company_name.lower():
                company = c
                break

        if not company:
            log.log(f"Company not found: {company_name}", "error")
            log.log("Available companies:")
            for c in companies:
                log.item(c.name)
            return None

        if not company.ready_for_pipeline:
            log.log(f"Company {company_name} has no processable files", "warning")
            return None

        return self.executor.execute_company(company)

    def process_all(self, only_ready: bool = True) -> List[PipelineResult]:
        """Process all companies."""
        companies = self.scanner.scan_all()

        if only_ready:
            companies = [c for c in companies if c.ready_for_pipeline]

        log.header(f"PROCESSING {len(companies)} COMPANIES")

        results = []
        for i, company in enumerate(companies, 1):
            log.log(f"\n[{i}/{len(companies)}] Processing {company.name}...")
            result = self.executor.execute_company(company)
            results.append(result)

        # Final summary
        self._print_final_summary(results)

        return results

    def _print_final_summary(self, results: List[PipelineResult]):
        """Print final summary of all processed companies."""
        log.header("FINAL SUMMARY")

        completed = sum(1 for r in results if r.status == PipelineStatus.COMPLETED)
        failed = sum(1 for r in results if r.status == PipelineStatus.FAILED)
        total_products = sum(r.products_count for r in results)
        total_prices = sum(r.prices_loaded for r in results)
        total_duplicates = sum(r.duplicates_found for r in results)
        total_families = sum(r.families_created for r in results)
        total_time = sum(r.duration_seconds for r in results)

        print(f"  Companies Processed: {len(results)}")
        print(f"  Completed: {completed}")
        print(f"  Failed: {failed}")
        print(f"  Total Products: {total_products}")
        print(f"  Total Prices: {total_prices}")
        print(f"  Total Duplicates Found: {total_duplicates}")
        print(f"  Total Families Created: {total_families}")
        print(f"  Total Time: {total_time:.1f}s")

        print("\n  Details:")
        for r in results:
            status = "✓" if r.status == PipelineStatus.COMPLETED else "✗"
            color = "\033[92m" if r.status == PipelineStatus.COMPLETED else "\033[91m"
            reset = "\033[0m"
            norm_info = f", {r.duplicates_found} dups, {r.families_created} fam" if r.normalized else ""
            print(f"    {color}{status}{reset} {r.company}: {r.products_count} products, {r.prices_loaded} prices{norm_info}")


# ==============================================================================
# CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ODI Pipeline Orchestrator - Auto-discovery and execution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan all companies
  %(prog)s --scan

  # Process a specific company
  %(prog)s --company Yokomar

  # Process all companies
  %(prog)s --all

  # Dry run (show what would be done)
  %(prog)s --all --dry-run

  # Custom data directory
  %(prog)s --scan --data-dir /path/to/data
        """
    )

    # Mode arguments
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--scan', action='store_true',
                           help='Scan and report all available companies')
    mode_group.add_argument('--company', '-c', metavar='NAME',
                           help='Process a specific company')
    mode_group.add_argument('--all', action='store_true',
                           help='Process all companies with available files')

    # Options
    parser.add_argument('--data-dir', '-d', default=DEFAULT_DATA_DIR,
                       help=f'Data directory (default: {DEFAULT_DATA_DIR})')
    parser.add_argument('--output-dir', '-o', default=DEFAULT_OUTPUT_DIR,
                       help=f'Output directory (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without executing')

    args = parser.parse_args()

    # Print banner
    print(f"""
{'='*70}
     ODI PIPELINE ORCHESTRATOR v{VERSION}
     Auto-Discovery & Execution Engine
{'='*70}
    """)

    # Create orchestrator
    orchestrator = ODIPipelineOrchestrator(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run
    )

    # Execute mode
    if args.scan:
        orchestrator.scan()

    elif args.company:
        result = orchestrator.process_company(args.company)
        if result:
            sys.exit(0 if result.status == PipelineStatus.COMPLETED else 1)
        else:
            sys.exit(1)

    elif args.all:
        results = orchestrator.process_all()
        failed = sum(1 for r in results if r.status == PipelineStatus.FAILED)
        sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
