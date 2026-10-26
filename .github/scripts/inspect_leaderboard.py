"""Temporary public-page schema diagnostic; prints no credentials."""
from html.parser import HTMLParser
import json
import re
import shutil
import sys
from pathlib import Path
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from refresh_feed import Rows, URL
req=urllib.request.Request(URL, headers={'User-Agent':'GEMS-evidence-monitor/1.0'})
with urllib.request.urlopen(req, timeout=20) as response:
    text=response.read(8000000).decode('utf-8',errors='replace')
class Tags(HTMLParser):
    def __init__(self): super().__init__(); self.scripts=[]; self.title=[]; self.on=False
    def handle_starttag(self,t,a):
        if t=='title': self.on=True
        if t=='script':
            d=dict(a)
            if d.get('src'): self.scripts.append(d['src'])
    def handle_endtag(self,t):
        if t=='title': self.on=False
    def handle_data(self,d):
        if self.on: self.title.append(d)
p=Rows();p.feed(text);t=Tags();t.feed(text)
snippets=[]
for m in re.finditer('leaderboard|api/|<iframe',text,re.I):
    part=' '.join(text[max(0,m.start()-90):m.end()+120].split())
    if part not in snippets: snippets.append(part[:220])
    if len(snippets)==8: break
info={'title':' '.join(''.join(t.title).split()),'rows':len(p.rows), 'scripts':t.scripts,
      'snippets':snippets,'browsers':{n:shutil.which(n) for n in ('google-chrome','chromium','chromium-browser')}}
message=json.dumps(info,ensure_ascii=True).replace('%','%25').replace('\r','%0D').replace('\n','%0A')
print('::notice title=Leaderboard schema::'+message)
