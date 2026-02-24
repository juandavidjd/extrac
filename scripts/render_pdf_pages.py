#!/usr/bin/env python3
import fitz
import os
import sys

pdf_path = '/opt/odi/data/ARMOTOS/catalogo/CATALOGO NOVIEMBRE V01-2025 NF.pdf'
output_dir = '/opt/odi/data/ARMOTOS/pages'
DPI = 300
ZOOM = DPI / 72

doc = fitz.open(pdf_path)
total = doc.page_count
print(f'Renderizando {total} páginas a {DPI} DPI', flush=True)

existing = set(f for f in os.listdir(output_dir) if f.endswith('.png'))
rendered = 0
skipped = 0

for i in range(total):
    filename = f'page_{i+1:03d}.png'
    filepath = os.path.join(output_dir, filename)
    
    if filename in existing:
        skipped += 1
        continue
    
    page = doc[i]
    mat = fitz.Matrix(ZOOM, ZOOM)
    pix = page.get_pixmap(matrix=mat)
    pix.save(filepath)
    rendered += 1
    
    if (i + 1) % 20 == 0:
        print(f'  [{i+1}/{total}] renderizadas', flush=True)

doc.close()
print(f'COMPLETADO: {rendered} renderizadas, {skipped} saltadas', flush=True)
