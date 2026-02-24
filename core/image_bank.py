#!/usr/bin/env python3
"""
V22 Cross-Store Image Bank
Module: /opt/odi/core/image_bank.py
Indexes all images from all empresas for cross-reference
"""

import os
import json
import re
from pathlib import Path
from typing import Optional, Dict, List

class ImageBank:
    IMG_ROOT = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Imagenes"
    INDEX_FILE = "/opt/odi/data/image_bank_index.json"
    
    EMPRESAS = ["Armotos", "Bara", "Cbi", "Dfg", "Duna", "Imbra", "Japan", 
                "Kaiqi", "Leo", "Mclmotos", "Oh_importaciones", "Store", 
                "Vaisand", "Vitton", "Yokomar"]
    
    def __init__(self):
        self.index = {}  # sku -> {path, empresa, filename}
        self.name_index = {}  # normalized_name -> [{path, empresa, sku}]
        
    def build_index(self) -> int:
        """Build index of all images across all empresas"""
        total = 0
        
        for empresa in self.EMPRESAS:
            img_dir = f"{self.IMG_ROOT}/{empresa}"
            if not os.path.exists(img_dir):
                continue
                
            for f in os.listdir(img_dir):
                if not f.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                    continue
                    
                filepath = os.path.join(img_dir, f)
                sku = self._extract_sku(f)
                name = self._normalize_name(f)
                
                # Index by SKU
                if sku:
                    self.index[sku.upper()] = {
                        "path": filepath,
                        "empresa": empresa,
                        "filename": f
                    }
                    
                # Index by normalized name
                if name:
                    if name not in self.name_index:
                        self.name_index[name] = []
                    self.name_index[name].append({
                        "path": filepath,
                        "empresa": empresa,
                        "sku": sku
                    })
                    
                total += 1
                
        print(f"ImageBank: indexed {total} images from {len(self.EMPRESAS)} empresas")
        print(f"  SKU index: {len(self.index)} entries")
        print(f"  Name index: {len(self.name_index)} entries")
        
        return total
        
    def _extract_sku(self, filename: str) -> Optional[str]:
        """Extract SKU from filename (usually at end before extension)"""
        name = Path(filename).stem.lower()
        parts = name.split("-")
        
        # Last part is often the SKU
        if parts:
            sku = parts[-1].strip()
            if len(sku) >= 3:
                return sku.upper()
                
        # Also try patterns like m110053, ket101844
        match = re.search(r"([a-z]{1,4}\d{4,8})", name, re.IGNORECASE)
        if match:
            return match.group(1).upper()
            
        return None
        
    def _normalize_name(self, filename: str) -> str:
        """Normalize filename for fuzzy matching"""
        name = Path(filename).stem.lower()
        # Remove numbers and special chars, keep words
        name = re.sub(r"[^a-z\s]", " ", name)
        name = " ".join(name.split())
        return name
        
    def find_by_sku(self, sku: str) -> Optional[Dict]:
        """Find image by exact SKU match"""
        return self.index.get(sku.upper())
        
    def find_by_partial_sku(self, sku: str) -> Optional[Dict]:
        """Find image by partial SKU match"""
        sku_upper = sku.upper()
        
        for idx_sku, data in self.index.items():
            if sku_upper in idx_sku or idx_sku in sku_upper:
                return data
                
        return None
        
    def find_by_name(self, product_name: str, empresa_priority: str = None) -> Optional[Dict]:
        """Find image by product name similarity"""
        norm_name = self._normalize_name(product_name)
        
        # Direct match
        if norm_name in self.name_index:
            matches = self.name_index[norm_name]
            # Prioritize same empresa
            if empresa_priority:
                for m in matches:
                    if m["empresa"].upper() == empresa_priority.upper():
                        return {"path": m["path"], "empresa": m["empresa"]}
            return {"path": matches[0]["path"], "empresa": matches[0]["empresa"]}
            
        # Partial match
        words = set(norm_name.split())
        best_match = None
        best_score = 0
        
        for idx_name, matches in self.name_index.items():
            idx_words = set(idx_name.split())
            common = len(words & idx_words)
            score = common / max(len(words), len(idx_words))
            
            if score > best_score and score >= 0.6:
                best_score = score
                if empresa_priority:
                    for m in matches:
                        if m["empresa"].upper() == empresa_priority.upper():
                            best_match = {"path": m["path"], "empresa": m["empresa"], "score": score}
                            break
                if not best_match:
                    best_match = {"path": matches[0]["path"], "empresa": matches[0]["empresa"], "score": score}
                    
        return best_match
        
    def save_index(self):
        """Save index to disk for persistence"""
        data = {"index": self.index, "name_index": self.name_index}
        with open(self.INDEX_FILE, "w") as f:
            json.dump(data, f)
        print(f"Index saved to {self.INDEX_FILE}")
        
    def load_index(self) -> bool:
        """Load index from disk"""
        if os.path.exists(self.INDEX_FILE):
            with open(self.INDEX_FILE) as f:
                data = json.load(f)
            self.index = data.get("index", {})
            self.name_index = data.get("name_index", {})
            print(f"Index loaded: {len(self.index)} SKUs, {len(self.name_index)} names")
            return True
        return False


# Singleton instance
_bank = None

def get_image_bank() -> ImageBank:
    global _bank
    if _bank is None:
        _bank = ImageBank()
        if not _bank.load_index():
            _bank.build_index()
            _bank.save_index()
    return _bank


if __name__ == "__main__":
    bank = ImageBank()
    bank.build_index()
    bank.save_index()
    
    # Test queries
    print("\n=== Test Queries ===")
    result = bank.find_by_sku("M110053")
    print(f"M110053: {result}")
