"""Shared, deterministic RFL correction banner for all root Pages renderers.

Same pattern as scripts/hce_banner.py: one module, exact bytes everywhere.
States the 2026-10-27 (arena/bd44f94b) selector correction: the skarpline
"SUBMIT" decision below was audited against the full rebuilt registry and is
superseded.  The skarpline lane keeps its own run card; this banner is the
current repository decision.
"""
from __future__ import annotations

RFL_BANNER = (
    '<div style="background:#3d2e04;color:#fff6e0;border-bottom:2px solid #d29922;'
    'padding:10px 20px;font-size:14px">'
    '<div style="max-width:1080px;margin:0 auto;display:flex;flex-wrap:wrap;gap:10px;align-items:center">'
    '<strong style="color:#ffd76a">CORRECTED DECISION · 2026-10-27 audit</strong>'
    '<span style="flex:1 1 300px">The skarpline file below FAILS the project uniqueness gate against the full '
    'rebuilt registry (73.5% and 72.4% of its dots lie within 3&nbsp;px of two registered rasters; limit 70%) and has '
    'no fold-local holdout. It is <b>not cleared</b>. The only file passing every gate is HCE-1 — see the '
    'current executive summary for evidence, estimates and exact submission steps.</span>'
    '<a style="background:#d29922;color:#1a1200;font-weight:700;padding:7px 12px;border-radius:6px;'
    'text-decoration:none" href="rfl/index.html">Current executive summary ↗</a>'
    '<a style="color:#ffe9b0;border:1px solid #9e7c2c;padding:7px 12px;border-radius:6px;'
    'text-decoration:none" href="hce/downloads/wbggems3-hce1-latest.tif" download>Download gated TIF ↓</a>'
    '</div></div>'
)
