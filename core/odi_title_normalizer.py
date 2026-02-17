#!/usr/bin/env python3
"""
ODI Title Normalizer - Clean and normalize product titles
Removes store suffixes, limits length, standardizes format.
Part of V12 ARMOTOS Tienda Modelo pipeline.
"""
import re
from typing import List, Dict, Optional


class TitleNormalizer:
    """Normalize product titles for Shopify."""
    
    def __init__(self, store: str, max_length: int = 60):
        """
        Initialize normalizer.
        
        Args:
            store: Store name to remove from titles
            max_length: Maximum title length (default 60)
        """
        self.store = store.upper()
        self.max_length = max_length
        
        # Patterns to remove
        self.remove_patterns = [
            rf'\s*-\s*{self.store}\s*$',  # "- ARMOTOS" at end
            rf'\s*{self.store}\s*$',       # "ARMOTOS" at end
            r'\s*-\s*$',                   # Trailing dash
            r'\s{2,}',                     # Multiple spaces
        ]
    
    def normalize(self, title: str) -> str:
        """
        Normalize a single title.
        
        Args:
            title: Original product title
        
        Returns:
            Cleaned title
        """
        if not title:
            return title
        
        result = title.strip()
        
        # Apply removal patterns
        for pattern in self.remove_patterns:
            result = re.sub(pattern, ' ', result, flags=re.IGNORECASE)
        
        result = result.strip()
        
        # Truncate if needed
        if len(result) > self.max_length:
            result = result[:self.max_length - 3].strip() + '...'
        
        return result
    
    def normalize_batch(self, products: List[Dict]) -> List[Dict]:
        """
        Normalize titles for a list of products.
        
        Args:
            products: List of product dicts with 'title' field
        
        Returns:
            Products with normalized titles
        """
        for product in products:
            original = product.get('title', '')
            normalized = self.normalize(original)
            
            if normalized != original:
                product['title_original'] = original
                product['title'] = normalized
        
        return products
    
    def preview_changes(self, products: List[Dict]) -> List[Dict]:
        """
        Preview title changes without modifying.
        
        Returns:
            List of dicts with 'sku', 'original', 'normalized' fields
        """
        changes = []
        
        for product in products:
            original = product.get('title', '')
            normalized = self.normalize(original)
            
            if normalized != original:
                changes.append({
                    'sku': product.get('sku', ''),
                    'original': original,
                    'normalized': normalized
                })
        
        return changes


def get_normalizer(store: str, max_length: int = 60) -> TitleNormalizer:
    """Factory function to get normalizer for store."""
    return TitleNormalizer(store, max_length)


if __name__ == '__main__':
    # Test
    normalizer = get_normalizer('ARMOTOS', max_length=60)
    
    test_titles = [
        'Filtro de Aceite Motor Yamaha BWS 125 - Armotos',
        'Abrazadera Manguera Gasolina 8mm Acero Inoxidable - ARMOTOS',
        'Espejo Retrovisor Universal Negro Mate Deportivo Para Moto',
    ]
    
    for title in test_titles:
        normalized = normalizer.normalize(title)
        print(f'Original:   {title}')
        print(f'Normalized: {normalized}')
        print()
