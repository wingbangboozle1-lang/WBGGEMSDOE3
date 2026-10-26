"""Temporary public-page HTMX endpoint diagnostic; prints no credentials."""
from html.parser import HTMLParser
import json
import sys
from pathlib import Path
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from refresh_feed import URL
req=urllib.request.Request(URL, headers={'User-Agent':'GEMS-evidence-monitor/1.0'})
with urllib.request.urlopen(req, timeout=20) as response:
    text=response.read(8000000).decode('utf-8',errors='replace')
class Tags(HTMLParser):
    def __init__(self): super().__init__(); self.htmx=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if any(k.startswith('hx-') for k in d):
            self.htmx.append({'tag':tag, 'attrs':{k:v for k,v in d.items() if k.startswith('hx-') or k in ('id','class')}})
p=Tags();p.feed(text)
message=json.dumps(p.htmx[:12],ensure_ascii=True).replace('%','%25').replace('\r','%0D').replace('\n','%0A')
print('::notice title=HTMX endpoint::'+message)
