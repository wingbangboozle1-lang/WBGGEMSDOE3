"""Shared, deterministic HCE-1 lane banner for all root Pages renderers.

Kept in one module so the legacy renderer, the new evidence renderer, the site
builder shim and the tests all agree on the exact bytes.  Inline styles make it
independent of whichever stylesheet a page uses.
"""
from __future__ import annotations

HCE_BANNER = (
    '<div style="background:#0d3327;color:#e8fff5;border-bottom:2px solid #29c78a;'
    'padding:10px 20px;font-size:14px">'
    '<div style="max-width:1080px;margin:0 auto;display:flex;flex-wrap:wrap;gap:10px;align-items:center">'
    '<strong style="color:#7ff0bd">NEW · HCE-1 lane (2026-10-27)</strong>'
    '<span style="flex:1 1 260px">A unique, format-validated GeoTIFF is ready to download. '
    'The legacy audit keeps its own verdict; the new lane owns its decision.</span>'
    '<a style="background:#29c78a;color:#04231a;font-weight:700;padding:7px 12px;border-radius:6px;'
    'text-decoration:none" href="hce/downloads/wbggems3-hce1-latest.tif" download>Download TIF ↓</a>'
    '<a style="color:#bff7dd;border:1px solid #4b9e7c;padding:7px 12px;border-radius:6px;'
    'text-decoration:none" href="hce/index.html">Executive summary ↗</a>'
    '</div></div>'
)
