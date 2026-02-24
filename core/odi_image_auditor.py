#!/usr/bin/env python3
import os, json, base64, random
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict
from datetime import datetime

# Load env
with open('/opt/odi/.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k,v = line.strip().split('=',1)
            os.environ[k] = v

from openai import OpenAI
client = OpenAI()

@dataclass
class ImageAuditResult:
    file_path: str
    file_name: str
    store: str = ''
    has_any_watermark: bool = False
    has_any_logo: bool = False
    has_any_text: bool = False
    has_engraved_name: bool = False
    has_dirty_background: bool = False
    has_multiple_products: bool = False
    product_visible: bool = True
    good_resolution: bool = True
    own_store_ok: bool = True
    cross_store_ok: bool = False
    notes: str = ''

class ImageAuditor:
    
    PROMPT_CROSS_STORE = 'Analyze product image for NEUTRAL status (no branding). Detect: ANY_WATERMARK (any store watermark), ANY_LOGO (any visible logo), ANY_TEXT (promo text/prices), ENGRAVED_NAME (store name on product), DIRTY_BG (unprofessional background), MULTI_PROD (multiple different products), PRODUCT_VISIBLE (product clearly visible), GOOD_RESOLUTION (not pixelated). Image is CROSS_STORE_OK only if: NO watermark, NO logo, NO text, NO engraved name, product visible, good resolution. Reply JSON only: {any_watermark:bool,any_logo:bool,any_text:bool,engraved_name:bool,dirty_bg:bool,multi_prod:bool,product_visible:bool,good_resolution:bool,cross_store_ok:bool,notes:brief}'

    def __init__(self):
        self.results_path = Path('/opt/odi/data/audit_results')
        self.results_path.mkdir(parents=True, exist_ok=True)
    
    def audit_image(self, image_path, store=''):
        path = Path(image_path)
        result = ImageAuditResult(file_path=str(path), file_name=path.name, store=store)
        try:
            with open(path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = path.suffix.lower()
            mt = 'image/jpeg' if ext in ['.jpg','.jpeg'] else 'image/png' if ext=='.png' else 'image/webp'
            resp = client.chat.completions.create(model='gpt-4o', messages=[{'role':'user','content':[{'type':'text','text':self.PROMPT_CROSS_STORE},{'type':'image_url','image_url':{'url':f'data:{mt};base64,{b64}'}}]}], max_tokens=300)
            content = resp.choices[0].message.content
            if '{' in content:
                data = json.loads(content[content.find('{'):content.rfind('}')+1])
                result.has_any_watermark = data.get('any_watermark', False)
                result.has_any_logo = data.get('any_logo', False)
                result.has_any_text = data.get('any_text', False)
                result.has_engraved_name = data.get('engraved_name', False)
                result.has_dirty_background = data.get('dirty_bg', False)
                result.has_multiple_products = data.get('multi_prod', False)
                result.product_visible = data.get('product_visible', True)
                result.good_resolution = data.get('good_resolution', True)
                result.cross_store_ok = data.get('cross_store_ok', False)
                result.notes = data.get('notes', '')
                result.own_store_ok = result.product_visible and result.good_resolution
        except Exception as e:
            result.notes = str(e)
        return result
    
    def audit_store_for_cross(self, store, images_path, sample_size=20):
        path = Path(images_path)
        images = list(path.glob('*.jpg'))+list(path.glob('*.jpeg'))+list(path.glob('*.png'))+list(path.glob('*.webp'))
        if not images:
            return {'store':store,'total':0,'sampled':0,'cross_store_ok':0,'own_store_ok':0}
        sample = random.sample(images, min(sample_size, len(images)))
        cross_ok = own_ok = 0
        details = []
        for img in sample:
            r = self.audit_image(str(img), store)
            if r.cross_store_ok: cross_ok += 1
            if r.own_store_ok: own_ok += 1
            details.append(asdict(r))
        result = {'store':store,'total':len(images),'sampled':len(sample),'cross_store_ok':cross_ok,'cross_store_pct':round(cross_ok*100/len(sample)),'own_store_ok':own_ok,'own_store_pct':round(own_ok*100/len(sample)),'estimated_cross_total':int(len(images)*cross_ok/len(sample)),'details':details}
        with open(self.results_path/f'{store}_cross_audit.json','w') as f:
            json.dump(result,f,indent=2)
        return result

if __name__=='__main__':
    print('ImageAuditor v2 ready')
