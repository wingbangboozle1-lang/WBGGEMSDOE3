"""Temporary public-fragment diagnostic; emits a score, not account data."""
from html.parser import HTMLParser
import json
import sys
from pathlib import Path
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from refresh_feed import Rows, PARTIAL_URL, parse_first_place
req=urllib.request.Request(PARTIAL_URL,headers={'User-Agent':'GEMS-evidence-monitor/1.0','HX-Request':'true'})
with urllib.request.urlopen(req, timeout=20) as response:
    target=response.geturl();text=response.read(8000000).decode('utf-8',errors='replace')
p=Rows();p.feed(text)
try: score=parse_first_place(text)
except ValueError as e: score=str(e)
info={'target':target,'rows':len(p.rows),'first_rows':[r[:5] for r in p.rows[:3]],'score':score}
message=json.dumps(info,ensure_ascii=True).replace('%','%25').replace('\r','%0D').replace('\n','%0A')
print('::notice title=HTMX fragment parser::'+message)
