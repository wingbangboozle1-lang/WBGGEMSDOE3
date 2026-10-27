"""Shared, deterministic RFL audit banner for all root Pages renderers.

Same pattern as scripts/hce_banner.py: one module, exact bytes everywhere.
Records the 2026-10-27 (arena/bd44f94b) independent audit outcome after the
merge with the score-tomography lane on main: the skarpline veto is shared by
both gate systems, and main's cleared TDE-30k file also passes this session's
full-registry uniqueness audit.  Details: docs/rfl/index.html.
"""
from __future__ import annotations

RFL_BANNER = (
    '<div style="background:#3d2e04;color:#fff6e0;border-bottom:2px solid #d29922;'
    'padding:10px 20px;font-size:14px">'
    '<div style="max-width:1080px;margin:0 auto;display:flex;flex-wrap:wrap;gap:10px;align-items:center">'
    '<strong style="color:#ffd76a">INDEPENDENT AUDIT · 2026-10-27 (RFL lane)</strong>'
    '<span style="flex:1 1 300px">Skarpline is <b>not cleared</b> under either gate system (full-registry uniqueness: '
    '73.5% / 72.4% within 3&nbsp;px vs two registered rasters). This audit also re-checked the cleared TDE-30k file '
    'on the rebuilt 120-mask registry: <b>PASS</b> (max 63.1% within 3&nbsp;px). Per-site tables for GEMSDOE24–36, '
    'labelled estimates and exact submission steps are in the audit summary.</span>'
    '<a style="background:#d29922;color:#1a1200;font-weight:700;padding:7px 12px;border-radius:6px;'
    'text-decoration:none" href="rfl/index.html">Audit executive summary ↗</a>'
    '<a style="color:#ffe9b0;border:1px solid #9e7c2c;padding:7px 12px;border-radius:6px;'
    'text-decoration:none" href="downloads/wbggems3-tde30k-tomography-emission-20261027T1853Z-e756a162-zeros.tif" download>Cleared TIF (TDE-30k) ↓</a>'
    '</div></div>'
)
