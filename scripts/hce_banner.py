"""Repository-wide status banner shared by the main dashboard.

The HCE lane remains a useful research record, but its own card reports a
literal-registry failure.  It cannot override the repository-level release
card or make an upload safe.
"""

HCE_BANNER = """<div style="background:#3a1719;color:#ffe8e8;border-bottom:2px solid #e56b70;padding:10px 20px;font-size:14px"><div style="max-width:1080px;margin:0 auto;display:flex;flex-wrap:wrap;gap:10px;align-items:center"><strong style="color:#ffb9bc">GLOBAL GATE · DO NOT SUBMIT</strong><span style="flex:1 1 260px">Parallel HCE-1 and skarpline artifacts are research-only. Their local checks do not override the literal registry stop, missing global selector approval, or the governing negative run card.</span><a style="color:#ffe8e8;border:1px solid #e56b70;padding:7px 12px;border-radius:6px;text-decoration:none" href="hce/index.html">Review HCE evidence ↗</a></div></div>"""
