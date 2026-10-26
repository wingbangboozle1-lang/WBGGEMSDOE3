"""Fetch GitHub repository HEAD identities, not scores or release approvals.

Scheduled workflow uploads this result as an audit artifact. It never rewrites
historical evidence or changes the dated executive decision automatically.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.request

def refresh(output):
    results=[]
    for number in (24,25,27,28,30,31,32,33,36):
        repo=f'buffedlizard55-lab/GEMSDOE{number}'
        try:
            request=urllib.request.Request(f'https://api.github.com/repos/{repo}/commits/main',headers={'User-Agent':'GEMS-evidence-audit'})
            with urllib.request.urlopen(request,timeout=30) as response:
                commit=json.load(response)
            results.append(dict(repo=repo,commit=commit['sha'],tree=commit['commit']['tree']['sha'],status='FETCHED'))
        except Exception as error:
            results.append(dict(repo=repo,status='FAILED',error=str(error)))
    report=dict(checked_at=datetime.now(timezone.utc).isoformat(),scope='GitHub HEAD identities only; no leaderboard, artifact or score validation',approved_for_submission=False,repositories=results)
    Path(output).write_text(json.dumps(report,indent=2)+'\n')
    return 0 if all(r['status']=='FETCHED' for r in results) else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='evidence/latest-upstream-check.json');a=p.parse_args()
    raise SystemExit(refresh(a.output))
