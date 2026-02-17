#!/usr/bin/env python3
"""
ODI Image Highlighter - Smart Film Generator
Applies semi-transparent overlay to catalog images, highlighting specific product rows.
Part of V12 ARMOTOS Tienda Modelo pipeline.
"""
from PIL import Image, ImageDraw
from typing import Dict, Tuple, Optional
import os

class ImageHighlighter:
    """Generate smart film images for catalog products."""
    
    def __init__(self, overlay_color: str = 'black', alpha: int = 180):
        """
        Initialize highlighter.
        
        Args:
            overlay_color: 'black' or 'white'
            alpha: transparency (0-255), higher = more opaque
        """
        self.overlay_color = overlay_color
        self.alpha = alpha
    
    def highlight_product_row(
        self,
        image_path: str,
        bbox: Dict[str, float],
        output_path: str,
        full_width: bool = True
    ) -> bool:
        """
        Apply smart film overlay, leaving product row visible.
        
        Args:
            image_path: Path to catalog page image
            bbox: Bounding box dict with x, y, w, h as percentages (0-100)
            output_path: Where to save the result
            full_width: If True, highlight full row width (ignore bbox x/w)
        
        Returns:
            True if successful
        """
        if not os.path.exists(image_path):
            return False
        
        img = Image.open(image_path).convert('RGBA')
        width, height = img.size
        
        # Calculate row coordinates
        if full_width:
            # Full table width (2% to 98% margins)
            x1 = int(width * 0.02)
            x2 = int(width * 0.98)
        else:
            x1 = int(bbox.get('x', 0) * width / 100)
            x2 = int((bbox.get('x', 0) + bbox.get('w', 100)) * width / 100)
        
        y1 = int(bbox.get('y', 0) * height / 100)
        y2 = int((bbox.get('y', 0) + bbox.get('h', 10)) * height / 100)
        
        # Add small padding
        pad = int(height * 0.005)
        y1 = max(0, y1 - pad)
        y2 = min(height, y2 + pad)
        
        # Create overlay
        if self.overlay_color == 'white':
            fill = (255, 255, 255, self.alpha)
        else:
            fill = (0, 0, 0, self.alpha)
        
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Cover everything EXCEPT the product row
        draw.rectangle([0, 0, width, y1], fill=fill)  # Top
        draw.rectangle([0, y2, width, height], fill=fill)  # Bottom
        
        # Composite and save
        result = Image.alpha_composite(img, overlay)
        result.save(output_path, 'PNG')
        return True
    
    def batch_highlight(
        self,
        pages_dir: str,
        hotspots: Dict,
        output_dir: str
    ) -> Dict[str, int]:
        """
        Process multiple pages from hotspot map.
        
        Args:
            pages_dir: Directory containing page images
            hotspots: Hotspot map dict with page data
            output_dir: Where to save highlighted images
        
        Returns:
            Stats dict with success/fail counts
        """
        os.makedirs(output_dir, exist_ok=True)
        stats = {'success': 0, 'failed': 0}
        
        for page_key, page_data in hotspots.get('hotspots', {}).items():
            page_num = int(page_key.replace('page_', ''))
            products = page_data.get('products', [])
            
            for product in products:
                bbox = product.get('bbox', {})
                sku = product.get('codigo', product.get('sku', 'unknown'))
                
                if not bbox:
                    continue
                
                input_path = f'{pages_dir}/page_{page_num}.png'
                output_path = f'{output_dir}/page_{page_num:03d}_sku_{sku}.png'
                
                if self.highlight_product_row(input_path, bbox, output_path):
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
        
        return stats


def get_highlighter(mode: str = 'black') -> ImageHighlighter:
    """Factory function to get configured highlighter."""
    if mode == 'white':
        return ImageHighlighter(overlay_color='white', alpha=240)
    else:
        return ImageHighlighter(overlay_color='black', alpha=180)


if __name__ == '__main__':
    # Test
    import json
    
    highlighter = get_highlighter('black')
    
    with open('/opt/odi/data/ARMOTOS/hotspot_map_sample.json') as f:
        hotspots = json.load(f)
    
    # Test single image
    page_data = hotspots['hotspots'].get('page_10', {})
    if page_data.get('products'):
        product = page_data['products'][0]
        result = highlighter.highlight_product_row(
            '/opt/odi/data/ARMOTOS/hotspot_pages/page_10.png',
            product['bbox'],
            '/tmp/test_highlight.png'
        )
        print(f'Test result: {result}')
