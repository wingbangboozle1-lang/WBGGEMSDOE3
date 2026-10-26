"""Temporary public-page schema diagnostic; prints no credentials."""
from html.parser import HTMLParser
import json
import sys
from pathlib import Path
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from refresh_feed import Rows, URL
req=urllib.request.Request(URL, headers={'User-Agent':'GEMS-evidence-monitor/1.0'})
with urllib.request.urlopen(req, timeout=20) as response:
    text=response.read(8000000).decode('utf-8',errors='replace')
class Title(HTMLParser):
    def __init__(self): super().__init__(); self.on=False; self.parts=[]; self.tables=0
    def handle_starttag(self,t,a):
        if t=='title': self.on=True
        if t=='table': self.tables+=1
    def handle_endtag(self,t):
        if t=='title': self.on=False
    def handle_data(self,d):
        if self.on: self.parts.append(d)
p=Rows();p.feed(text);t=Title();t.feed(text)
info={'title':' '.join(''.join(t.parts).split())[:120], 'tables':t.tables,
      'rows':len(p.rows), 'first_rows':[r[:5] for r in p.rows[:4]],
      'has_4437':'0.4437' in text, 'length':len(text)}
message=json.dumps(info,ensure_ascii=True).replace('%','%25').replace('\r','%0D').replace('\n','%0A')
print('::notice title=Leaderboard schema::'+message)
