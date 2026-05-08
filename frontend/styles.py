"""Design tokens and global CSS injected on every Streamlit script run.

Lifted from the design's React/Babel prototype so the Streamlit-native rebuild
keeps visual parity with the design source. Includes the full sidebar, topbar,
table-row, gradient agent-ready, dark thinking-panel, verdict-hero with
decorative corner, and checks-card treatments from the original mockup.

Why inject on every run rather than once: Streamlit re-executes the script
on every interaction (rerun) and diffs the resulting element tree against
the previous render. Elements not produced in the current run are dropped
from the DOM. Guarding inject() with a session flag means the CSS survives
the first render but disappears on every subsequent screen transition.
"""

from __future__ import annotations

import re

import streamlit as st

FONTS_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    "family=Inter+Tight:wght@400;500;600;700"
    "&family=JetBrains+Mono:wght@400;500;600"
    "&family=Instrument+Serif"
    '&display=swap" rel="stylesheet">'
)

CSS = """
:root {
  --bg: #f4f7fa;
  --surface: #ffffff;
  --surface-2: #f8fafc;
  --line: #e3e9ef;
  --line-strong: #cbd5e1;
  --ink: #0b1a2b;
  --ink-2: #334256;
  --ink-3: #6b7a8c;
  --ink-4: #9aa5b3;
  --brand: #1763d1;
  --brand-ink: #0a3b86;
  --brand-bg: #eaf2fd;
  --good: #0e8a5f;
  --good-bg: #e6f5ee;
  --good-ink: #064830;
  --warn: #b07206;
  --warn-bg: #fdf3dc;
  --warn-ink: #5e3c00;
  --bad: #c0392b;
  --bad-bg: #fbe8e5;
  --bad-ink: #6e1c12;
  --radius: 14px;
  --radius-sm: 8px;
  --shadow-sm: 0 1px 0 rgba(15,30,55,.04), 0 1px 2px rgba(15,30,55,.04);
  --shadow: 0 1px 0 rgba(15,30,55,.04), 0 8px 24px -12px rgba(15,30,55,.12);
  --mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  --sans: "Inter Tight", ui-sans-serif, system-ui, -apple-system, sans-serif;
  --serif: "Instrument Serif", "Cambria", "Georgia", serif;
}

/* ===== STREAMLIT BASE OVERRIDES ===== */
html, body, [class*="st-"], .stApp {
  font-family: var(--sans) !important;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
.stApp { background: var(--bg); }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, .stDeployButton, [data-testid="stToolbar"] { display: none !important; }
.block-container {
  padding-top: 1.5rem !important;
  padding-bottom: 2rem !important;
  max-width: 1240px !important;
}

/* ===== SIDEBAR (dark navy clinical nav) ===== */
section[data-testid="stSidebar"] {
  background: #0b1a2b !important;
  width: 260px !important;
  min-width: 260px !important;
  border-right: 1px solid #1c2d47 !important;
}
section[data-testid="stSidebar"] > div { background: #0b1a2b !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
  padding: 22px 18px !important;
  background: #0b1a2b !important;
}
section[data-testid="stSidebar"] * { color: #c8d4e4 !important; }
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown div { color: #c8d4e4 !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.06) !important; }
button[kind="header"][data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarCollapsedControl"] {
  color: #c8d4e4 !important;
  background: transparent !important;
}
.side-brand { display: flex; align-items: center; gap: 10px; margin-bottom: 24px; }
.side-brand .mark {
  width: 32px; height: 32px;
  border-radius: 8px;
  background: linear-gradient(140deg, #1763d1, #4ea3ff);
  display: grid; place-items: center;
  color: white !important;
  flex-shrink: 0;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.25);
}
.side-brand .name { font-weight: 600; color: #fff !important; font-size: 14px; letter-spacing: -0.01em; }
.side-brand .sub  { font-size: 11px; color: #6b7a90 !important; margin-top: 1px; }
.side-sect {
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em;
  color: #5d6c82 !important; margin: 4px 0 8px 8px;
}
.side-list { display: flex; flex-direction: column; gap: 2px; margin-bottom: 22px; }
.side-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 7px;
  color: #aab8cb !important; font-size: 13px;
}
a.side-item { text-decoration: none; cursor: pointer; }
a.side-item:hover { background: rgba(255,255,255,.04); color: #fff !important; }
.side-item.active { background: rgba(255,255,255,.06); color: #fff !important; font-weight: 500; }
.side-item.disabled { cursor: default; opacity: .55; }
.side-item svg { opacity: .85; flex-shrink: 0; }
.side-item.active svg { opacity: 1; }
.side-item .count {
  margin-left: auto;
  font-size: 11px;
  color: #5d6c82 !important;
  background: rgba(255,255,255,.05);
  padding: 1px 6px; border-radius: 4px;
  font-variant-numeric: tabular-nums;
}
.side-foot {
  margin-top: 18px; padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,.06);
  display: flex; align-items: center; gap: 10px;
}
.side-foot .avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: linear-gradient(135deg, #4ea3ff, #1763d1);
  display: grid; place-items: center;
  color: white !important; font-weight: 600; font-size: 11px; flex-shrink: 0;
}
.side-foot .who  { font-size: 12px; color: #fff !important; }
.side-foot .role { font-size: 11px; color: #6b7a90 !important; }

/* ===== TOPBAR ===== */
.topbar {
  display: flex; align-items: center; gap: 14px;
  padding: 6px 0 16px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--line);
  flex-wrap: wrap;
}
.crumb {
  font-size: 12px; color: var(--ink-3);
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
}
.crumb b { color: var(--ink); font-weight: 500; }
.crumb .sep { color: var(--ink-4); }
.crumb .mono { font-family: var(--mono); }
.topbar .spacer { flex: 1; }
.pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 99px;
  font-size: 11px; font-weight: 500;
  background: var(--brand-bg); color: var(--brand-ink);
}
.pill .dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--brand);
  box-shadow: 0 0 0 3px rgba(23,99,209,.2);
}
.pill.live .dot {
  background: var(--good);
  box-shadow: 0 0 0 3px rgba(14,138,95,.2);
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(14,138,95,.2); }
  50%      { box-shadow: 0 0 0 6px rgba(14,138,95,.05); }
}
.icon-btn {
  width: 32px; height: 32px;
  display: inline-grid; place-items: center;
  border-radius: 7px;
  background: transparent;
  color: var(--ink-3);
  border: 1px solid transparent;
}
.topbar-avatar {
  width: 30px; height: 30px; border-radius: 50%;
  background: linear-gradient(135deg, #4ea3ff, #1763d1);
  display: grid; place-items: center;
  color: white; font-weight: 600; font-size: 11px; flex-shrink: 0;
}

/* ===== TYPOGRAPHY ===== */
.page-h1 {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.015em;
  color: var(--ink);
  line-height: 1.2;
  margin: 0;
}
.page-sub { color: var(--ink-3); font-size: 13px; margin-top: 4px; }
.eyebrow {
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--ink-3); font-weight: 500;
}

/* ===== CARDS ===== */
.card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}
.card-h {
  padding: 14px 18px;
  border-bottom: 1px solid var(--line);
  display: flex; align-items: center; gap: 10px;
}
.card-h h3 { font-size: 13px; font-weight: 600; margin: 0; color: var(--ink); }
.card-h .meta {
  color: var(--ink-3); font-size: 12px; margin-left: auto;
  font-variant-numeric: tabular-nums; display: inline-flex; align-items: center; gap: 4px;
}
.card-b { padding: 18px; }

/* ===== BADGES ===== */
.badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 8px; border-radius: 6px;
  font-size: 11px; font-weight: 500; white-space: nowrap;
}
.badge.good    { background: var(--good-bg); color: var(--good-ink); }
.badge.warn    { background: var(--warn-bg); color: var(--warn-ink); }
.badge.bad     { background: var(--bad-bg);  color: var(--bad-ink); }
.badge.neutral { background: #e9eef4;        color: var(--ink-2); }
.badge.brand   { background: var(--brand-bg);color: var(--brand-ink); }

/* ===== STAT TILES (with icon square) ===== */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 18px;
}
@media (max-width: 900px) { .stat-grid { grid-template-columns: repeat(2, 1fr); } }
.stat-tile {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 16px;
  display: flex; align-items: center; gap: 12px;
  box-shadow: var(--shadow-sm);
}
.stat-tile .ico-sq {
  width: 36px; height: 36px;
  border-radius: 9px;
  display: grid; place-items: center;
  flex-shrink: 0;
}
.stat-tile.brand .ico-sq { background: var(--brand-bg); color: var(--brand); }
.stat-tile.good  .ico-sq { background: var(--good-bg);  color: var(--good); }
.stat-tile.bad   .ico-sq { background: var(--bad-bg);   color: var(--bad); }
.stat-tile.warn  .ico-sq { background: var(--warn-bg);  color: var(--warn); }
.stat-tile .label { font-size: 12px; color: var(--ink-3); }
.stat-tile .value {
  font-size: 22px; font-weight: 600; margin-top: 2px;
  letter-spacing: -0.02em; color: var(--ink);
  font-variant-numeric: tabular-nums; line-height: 1;
}

/* ===== INBOX TABLE (Bandeja) ===== */
.inbox-head, .inbox-row {
  display: grid;
  grid-template-columns: 90px 1.6fr 1.4fr 100px 110px 130px 36px;
  gap: 8px;
  padding: 10px 18px;
  align-items: center;
}
.inbox-head {
  font-size: 11px;
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-bottom: 1px solid var(--line);
  background: var(--surface-2);
}
.inbox-row {
  padding: 14px 18px;
  border-bottom: 1px solid var(--line);
  font-size: 13.5px;
  background: var(--surface);
  transition: background .12s;
}
.inbox-row:last-of-type { border-bottom: none; }
.inbox-row .id { font-family: var(--mono); font-size: 12px; font-weight: 500; color: var(--ink-2); }
.inbox-row .primary { font-weight: 500; font-size: 13.5px; color: var(--ink); }
.inbox-row .sub { font-size: 12px; color: var(--ink-3); margin-top: 2px; }
.inbox-row .sub .mono { font-family: var(--mono); }
.inbox-row .sub .dot-sep { color: var(--ink-4); margin: 0 6px; }
.inbox-row .chev { display: grid; place-items: end; color: var(--ink-4); }

/* The entire row is wrapped in <a class='inbox-row-link'> so the whole
   row is one clickable element. Click navigates via ?open=<id> query
   param, captured at the top of bandeja.render(). */
.inbox-row-link {
  display: block;
  text-decoration: none;
  color: inherit;
}
.inbox-row-link:hover .inbox-row { background: var(--surface-2); }
.inbox-row-link:hover .inbox-row .chev { color: var(--brand); }
.inbox-row-link:focus { outline: none; }
.inbox-row-link:focus-visible .inbox-row {
  outline: 2px solid var(--brand);
  outline-offset: -2px;
}

/* ===== Inline ghost buttons in page-header trailing slot (Filtrar / Exportar)
   Belt-and-suspenders flex layout because browser <button> defaults vary on
   how flex children are arranged, and Streamlit's host stylesheet has rules
   that touch every <button> on the page. */
.hdr-btn {
  display: inline-flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 6px !important;
  padding: 7px 12px !important;
  background: var(--surface) !important;
  color: var(--ink) !important;
  border: 1px solid var(--line-strong) !important;
  border-radius: 8px !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  font-family: var(--sans) !important;
  white-space: nowrap !important;
  cursor: not-allowed !important;
  opacity: 0.85;
  box-shadow: var(--shadow-sm) !important;
  height: 34px !important;
  line-height: 1 !important;
  width: auto !important;
  flex-shrink: 0;
}
.hdr-btn > svg { width: 14px !important; height: 14px !important; flex-shrink: 0; }
.hdr-btn > span { display: inline !important; line-height: 1 !important; }
.hdr-btn:hover { background: var(--surface-2) !important; }

/* Streamlit chevron button (per-row open). The Streamlit button container
   is targeted by key="open_INF-..." which becomes part of the data-testid. */
.row-chev .stButton > button {
  background: transparent !important;
  border: 1px solid transparent !important;
  box-shadow: none !important;
  color: var(--ink-4) !important;
  font-size: 18px !important;
  font-weight: 400 !important;
  padding: 6px !important;
  min-height: 0 !important;
  height: 36px;
}
.row-chev .stButton > button:hover {
  background: var(--surface-2) !important;
  border-color: var(--line) !important;
  color: var(--brand) !important;
}
.row-chev .stButton > button p,
.row-chev .stButton > button span,
.row-chev .stButton > button div {
  font-size: 18px !important;
  color: inherit !important;
}

/* ===== KV BLOCKS (Detalle) ===== */
.kv-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}
@media (max-width: 700px) { .kv-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.kv .label {
  font-size: 11px; color: var(--ink-3);
  text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px;
}
.kv .value { font-size: 13.5px; color: var(--ink); }
.kv .value.mono { font-family: var(--mono); font-weight: 500; }
.kv .sub { font-size: 12px; color: var(--ink-3); margin-top: 2px; }

/* ===== AGENTE LISTO (gradient brand card) ===== */
.agent-ready {
  background: linear-gradient(165deg, #ffffff 0%, var(--brand-bg) 100%);
  border: 1px solid rgba(23,99,209,.18);
  border-radius: var(--radius);
  padding: 18px;
  box-shadow: var(--shadow-sm);
  display: flex; flex-direction: column; gap: 14px;
}
.agent-ready .head { display: flex; align-items: center; gap: 10px; }
.agent-ready .head .sq {
  width: 36px; height: 36px; border-radius: 9px;
  background: var(--brand); color: white;
  display: grid; place-items: center;
  box-shadow: 0 4px 12px rgba(23,99,209,.3);
  flex-shrink: 0;
}
.agent-ready .head .title  { font-weight: 600; font-size: 14px; color: var(--ink); }
.agent-ready .head .sub    { font-size: 12px; color: var(--ink-3); }
.agent-ready .steps { display: flex; flex-direction: column; gap: 8px; font-size: 12.5px; color: var(--ink-2); }
.agent-ready .step { display: flex; align-items: flex-start; gap: 8px; line-height: 1.4; }
.agent-ready .step .num { width: 18px; flex-shrink: 0; text-align: center; color: var(--brand); font-weight: 600; }
.agent-ready .foot { font-size: 11px; color: var(--ink-3); text-align: center; }

/* ===== DOC CHIP ===== */
.doc-row { display: flex; flex-wrap: wrap; gap: 8px; }
.doc-chip {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 6px 10px;
  background: var(--good-bg);
  color: var(--good-ink);
  border: 1px solid rgba(14,138,95,.2);
  border-radius: 7px;
  font-size: 12.5px;
}
.doc-chip.miss {
  background: var(--surface-2);
  color: var(--ink-3);
  border-color: var(--line);
}
.doc-chip.warn {
  background: #fff;
  border-color: rgba(176,114,6,.4);
  color: var(--warn-ink);
}
.tag-doc {
  font-size: 11px; padding: 3px 7px; border-radius: 5px;
  background: var(--surface-2); border: 1px solid var(--line);
  color: var(--ink-2);
}

/* ===== PROCESANDO TIMELINE ===== */
.timeline-wrap { padding: 18px 18px 8px; position: relative; }
.timeline-line {
  position: absolute;
  left: calc(18px + 16px - 0.5px);
  top: 50px; bottom: 18px;
  width: 1px; background: var(--line);
  z-index: 0;
}
.tl-step {
  display: flex; gap: 14px; position: relative;
  margin-bottom: 14px;
}
.tl-step .dot-wrap { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; }
.tl-step .dot {
  width: 32px; height: 32px; border-radius: 50%;
  display: grid; place-items: center;
  transition: all .25s;
  position: relative; z-index: 1; flex-shrink: 0;
}
.tl-step.idle .dot   { background: var(--surface);  border: 2px solid var(--line);  color: var(--ink-4); }
.tl-step.active .dot { background: #fff;            border: 2px solid var(--brand); color: var(--brand);
                       box-shadow: 0 0 0 6px rgba(23,99,209,.12); }
.tl-step.done .dot   { background: var(--good-bg); border: 2px solid var(--good); color: var(--good); }
.tl-step.fail .dot   { background: var(--bad-bg);  border: 2px solid var(--bad);  color: var(--bad); }
.tl-step .pulse-dot {
  width: 10px; height: 10px; border-radius: 50%; background: var(--brand);
  animation: pulse-dot 1.2s infinite;
}
.tl-step .small-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--ink-4); opacity: .6; }
@keyframes pulse-dot { 0%,100% { transform: scale(1); } 50% { transform: scale(1.35); } }
.tl-step .body {
  flex: 1; min-width: 0;
  border-radius: 10px;
  padding: 12px 14px;
  transition: all .25s;
}
.tl-step.idle .body   { background: var(--surface-2); border: 1px solid var(--line);  opacity: .55; }
.tl-step.active .body { background: var(--surface);   border: 1px solid var(--brand);
                        box-shadow: 0 4px 14px -6px rgba(23,99,209,.25); }
.tl-step.done .body   { background: var(--surface);   border: 1px solid var(--line); }
.tl-step.fail .body   { background: var(--surface);   border: 1px solid var(--bad); }
.tl-step .row1 { display: flex; align-items: flex-start; gap: 10px; }
.tl-step .ico-tool { margin-top: 3px; flex-shrink: 0; color: var(--ink-4); }
.tl-step.active .ico-tool { color: var(--brand); }
.tl-step.done .ico-tool   { color: var(--good); }
.tl-step.fail .ico-tool   { color: var(--bad); }
.tl-step .meta-line { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tl-step .idx { font-size: 11px; color: var(--ink-4); font-variant-numeric: tabular-nums; }
.tl-step .name { font-weight: 500; font-size: 13.5px; color: var(--ink); min-width: 0; }
.tl-step .source-line {
  font-size: 11.5px; color: var(--ink-3); margin-top: 4px;
  font-family: var(--mono); word-break: break-word;
}
.tl-step .source-line .source-tag { color: var(--ink-4); }

/* ===== DARK THINKING PANEL ===== */
.thinking {
  background: linear-gradient(165deg, #0b1a2b 0%, #14233b 100%);
  color: #cbe2ff;
  border: 1px solid #1c2d47;
  border-radius: var(--radius);
  padding: 18px;
  box-shadow: var(--shadow-sm);
  display: flex; flex-direction: column; gap: 14px;
}
.thinking .head { display: flex; align-items: center; gap: 10px; }
.thinking .head .sq {
  width: 32px; height: 32px; border-radius: 8px;
  background: linear-gradient(140deg,#4ea3ff,#1763d1);
  color: white; display: grid; place-items: center;
  flex-shrink: 0;
}
.thinking .head .title { font-weight: 600; font-size: 13px; color: #fff; }
.thinking .head .sub   { font-size: 11px; color: #7e93b3; }
.thinking .transcript {
  max-height: 220px; overflow-y: auto;
  display: flex; flex-direction: column; gap: 10px;
  font-size: 12.5px; line-height: 1.55;
}
.thinking .transcript .line { opacity: .8; }
.thinking .transcript .line.active { opacity: 1; }
.thinking .transcript .gt { color: #7e93b3; font-family: var(--mono); font-size: 10.5px; margin-right: 6px; }
.thinking .transcript .cursor {
  display: inline-block; width: 7px; height: 13px;
  background: #4ea3ff; margin-left: 3px; vertical-align: -2px;
  animation: blink 1s infinite;
}
@keyframes blink { 0%,49% { opacity: 1; } 50%,100% { opacity: 0; } }

/* ===== TELEMETRY TILES ===== */
.telem-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.telem .label {
  font-size: 11px; color: var(--ink-3);
  text-transform: uppercase; letter-spacing: 0.06em;
}
.telem .value {
  font-variant-numeric: tabular-nums;
  font-size: 20px; font-weight: 600; margin-top: 2px;
  letter-spacing: -0.02em; color: var(--ink);
}
.telem .value .suffix { font-size: 13px; color: var(--ink-3); font-weight: 400; margin-left: 2px; }

/* ===== NEURO-SYMBOLIC NOTE ===== */
.neuro-note {
  background: var(--surface);
  border: 1px solid rgba(23,99,209,.18);
  border-radius: var(--radius);
  padding: 18px;
  display: flex; gap: 12px; align-items: flex-start;
  box-shadow: var(--shadow-sm);
}
.neuro-note .ico { color: var(--brand); margin-top: 2px; flex-shrink: 0; }
.neuro-note .body { font-size: 12.5px; color: var(--ink-2); line-height: 1.55; }
.neuro-note .body b { color: var(--ink); display: block; margin-bottom: 2px; }

/* ===== VERDICT HERO (Resultado) ===== */
.verdict-hero {
  border-radius: 14px;
  padding: 22px;
  position: relative;
  overflow: hidden;
  border: 1px solid;
  box-shadow: var(--shadow-sm);
}
.verdict-hero .corner-circle {
  position: absolute; right: -30px; top: -30px;
  width: 160px; height: 160px;
  border-radius: 50%;
  opacity: 0.06;
}
.verdict-hero .row { display: flex; align-items: center; gap: 14px; position: relative; }
.verdict-hero .emblem {
  width: 54px; height: 54px; border-radius: 14px;
  display: grid; place-items: center;
  color: white; flex-shrink: 0;
}
.verdict-hero .eyebrow {
  font-size: 11px; letter-spacing: 0.12em;
  font-weight: 600; opacity: .7;
}
.verdict-hero .label-big {
  font-size: 30px; font-weight: 600;
  letter-spacing: -0.02em; margin-top: 2px;
  font-family: var(--serif);
}
.verdict-hero .summary {
  font-size: 13px; color: var(--ink-2); margin-top: 4px;
}
.verdict-hero .summary .mono { font-family: var(--mono); }
.verdict-hero .glass {
  margin-top: 18px; padding: 14px;
  background: rgba(255,255,255,.7);
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,.9);
}
.verdict-hero .glass .label {
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--ink-3); margin-bottom: 6px;
}
.verdict-hero .glass p {
  margin: 0; font-size: 14px; line-height: 1.6; color: var(--ink);
}
.verdict-hero .clausula {
  margin-top: 14px; display: flex; gap: 14px;
  align-items: center; font-size: 11.5px; color: var(--ink-3);
  flex-wrap: wrap;
}
.verdict-hero .clausula .sep { color: var(--ink-4); }
.verdict-hero .clausula .mono { font-family: var(--mono); }
.verdict-hero.good { background: linear-gradient(165deg, #fff 0%, var(--good-bg) 100%); border-color: rgba(14,138,95,.2); }
.verdict-hero.good .corner-circle { background: var(--good); }
.verdict-hero.good .emblem { background: var(--good); box-shadow: 0 8px 24px -8px var(--good); }
.verdict-hero.good .eyebrow,
.verdict-hero.good .label-big { color: var(--good-ink); }
.verdict-hero.bad { background: linear-gradient(165deg, #fff 0%, var(--bad-bg) 100%); border-color: rgba(192,57,43,.2); }
.verdict-hero.bad .corner-circle { background: var(--bad); }
.verdict-hero.bad .emblem { background: var(--bad); box-shadow: 0 8px 24px -8px var(--bad); }
.verdict-hero.bad .eyebrow,
.verdict-hero.bad .label-big { color: var(--bad-ink); }
.verdict-hero.warn { background: linear-gradient(165deg, #fff 0%, var(--warn-bg) 100%); border-color: rgba(176,114,6,.2); }
.verdict-hero.warn .corner-circle { background: var(--warn); }
.verdict-hero.warn .emblem { background: var(--warn); box-shadow: 0 8px 24px -8px var(--warn); }
.verdict-hero.warn .eyebrow,
.verdict-hero.warn .label-big { color: var(--warn-ink); }

/* ===== CHECKS CARD ===== */
.check-row {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--line);
}
.check-row:last-child { border-bottom: none; }
.check-row .ico-sq {
  width: 24px; height: 24px; border-radius: 7px;
  display: grid; place-items: center; flex-shrink: 0;
}
.check-row.ok  .ico-sq { background: var(--good-bg); color: var(--good); }
.check-row.bad .ico-sq { background: var(--bad-bg);  color: var(--bad); }
.check-row.na  .ico-sq { background: var(--surface-2); color: var(--ink-4); }
.check-row .body { flex: 1; min-width: 0; }
.check-row .label { font-size: 13.5px; font-weight: 500; color: var(--ink); }
.check-row .detail { font-size: 12px; color: var(--ink-3); margin-top: 2px; }

/* ===== TRACE MINI (Resultado side) ===== */
.trace-mini {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 4px;
  border-bottom: 1px dashed var(--line);
}
.trace-mini:last-child { border-bottom: none; }
.trace-mini .idx {
  font-size: 10px; color: var(--ink-4);
  width: 18px; text-align: right;
  font-variant-numeric: tabular-nums;
}
.trace-mini .ico { color: var(--ink-3); flex-shrink: 0; }
.trace-mini .label { font-size: 12.5px; flex: 1; color: var(--ink); }
.trace-mini .check { color: var(--good); }

/* ===== REGISTRO ROW ===== */
.reg-row {
  display: flex; justify-content: space-between; gap: 14px;
  font-size: 12.5px; align-items: baseline;
  padding: 6px 0;
}
.reg-row .k { color: var(--ink-3); flex-shrink: 0; }
.reg-row .v { color: var(--ink); font-weight: 500; text-align: right; min-width: 0; word-break: break-word; }
.reg-row .v.mono { font-family: var(--mono); font-weight: 400; }

/* ===== UTIL ===== */
.row-flex { display: flex; align-items: center; gap: 12px; }
.col-flex { display: flex; flex-direction: column; gap: 12px; }
.mono { font-family: var(--mono); }
.num  { font-variant-numeric: tabular-nums; }
.scroll-thin { scrollbar-width: thin; scrollbar-color: var(--line-strong) transparent; }
.spacer { flex: 1; }

/* ===== Streamlit button polish — force consistent light look regardless of theme */
.stButton > button {
  background: var(--surface) !important;
  color: var(--ink) !important;
  border: 1px solid var(--line-strong) !important;
  border-radius: 8px !important;
  font-family: var(--sans) !important;
  font-weight: 500 !important;
  font-size: 13px !important;
  box-shadow: var(--shadow-sm) !important;
  padding: 8px 14px !important;
  white-space: nowrap !important;
}
.stButton > button:hover {
  background: var(--surface-2) !important;
  border-color: var(--ink-4) !important;
  color: var(--ink) !important;
}
.stButton > button p,
.stButton > button span,
.stButton > button div {
  color: var(--ink) !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid*="primary"] {
  background: var(--brand) !important;
  border-color: var(--brand) !important;
  color: white !important;
  box-shadow: 0 1px 0 rgba(255,255,255,.15) inset, 0 1px 2px rgba(23,99,209,.3) !important;
  padding: 10px 18px !important;
  font-size: 14px !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid*="primary"]:hover {
  background: var(--brand-ink) !important;
  border-color: var(--brand-ink) !important;
}
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span,
.stButton > button[kind="primary"] div,
.stButton > button[data-testid*="primary"] p,
.stButton > button[data-testid*="primary"] span,
.stButton > button[data-testid*="primary"] div {
  color: white !important;
}

/* Streamlit expander */
[data-testid="stExpander"] {
  border: 1px solid var(--line) !important;
  border-radius: var(--radius) !important;
  background: var(--surface) !important;
}
[data-testid="stExpander"] summary { padding: 12px 16px !important; }
"""


def _sanitize_css_for_markdown(css: str) -> str:
    """Strip CSS comments and neutralize every ``*`` so markdown leaves the
    style block intact.

    Streamlit's markdown processor parses ``<style>`` content as markdown
    instead of raw HTML, so any ``*`` is consumed as an italic marker and
    silently truncates the rest of the block. We rewrite the three places
    we use ``*`` into asterisk-free equivalents:

    1. ``/* ... */`` comments — stripped entirely (purely cosmetic).
    2. ``[class*="st-"]`` — substring attribute selector. Streamlit's
       emotion classes start with ``st-emotion-cache-…`` so the
       prefix-match ``[class^="st-"]`` is equivalent for our purposes.
    3. ``[data-testid*="primary"]`` — Streamlit primary buttons carry
       ``data-testid="stBaseButton-primary"``, so end-match
       ``[data-testid$="primary"]`` is equivalent.
    4. ``section[...] *`` universal descendant — expanded to an explicit
       list of element selectors (div, span, p, a, button) which covers
       every text node in the sidebar.
    """
    # 1. Strip block comments
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    # 2. Substring class selector → prefix
    css = css.replace('[class*="st-"]', '[class^="st-"]')
    # 3. Substring data-testid → suffix (Streamlit primary button)
    css = css.replace('[data-testid*="primary"]', '[data-testid$="primary"]')
    # 4. Universal descendant → explicit element selectors
    css = css.replace(
        'section[data-testid="stSidebar"] *',
        'section[data-testid="stSidebar"] div, '
        'section[data-testid="stSidebar"] span, '
        'section[data-testid="stSidebar"] p, '
        'section[data-testid="stSidebar"] a, '
        'section[data-testid="stSidebar"] button, '
        'section[data-testid="stSidebar"] svg',
    )
    # Sanity guard: any remaining `*` would re-trigger the truncation.
    # Raise loudly instead of silently stripping — silent removal would
    # corrupt future selectors like `[role*='dialog']` (substring match)
    # into exact-match `[role='dialog']` with no error signal.
    if "*" in css:
        # Find the first remaining occurrence so the dev can diagnose.
        idx = css.find("*")
        snippet = css[max(0, idx - 40): idx + 40].replace("\n", " ")
        raise RuntimeError(
            "CSS sanitizer found an unhandled `*` after rewrites. "
            "Add a rule to _sanitize_css_for_markdown for this pattern. "
            f"Context: ...{snippet}..."
        )
    # 5. CommonMark closes HTML type-1 blocks (<style>, <script>, <pre>)
    # at the first blank line. Our CSS has many blank lines between rule
    # groups; collapse them so markdown sees one continuous block.
    css = re.sub(r"\n\s*\n+", "\n", css)
    return css


def inject() -> None:
    """Inject fonts + CSS into the Streamlit page on every script run.

    Three non-obvious choices live here:

    1. ``st.markdown(unsafe_allow_html=True)`` rather than ``st.html`` because
       in Streamlit 1.39 ``st.html`` runs DOMPurify with a config that strips
       ``<style>`` tag content (the tag survives but is empty), while
       ``st.markdown`` preserves it. This is the canonical Streamlit CSS
       injection pattern (see discuss.streamlit.io/t/.../33428).
    2. We pre-process the CSS to strip comments and rewrite attribute
       selectors that use ``*`` — Streamlit's markdown processor parses
       ``<style>`` content as markdown, consuming ``*`` chars as italic
       markers and silently truncating the rest of the CSS at the first
       unmatched comment delimiter.
    3. No session-state guard. Streamlit's element-tree diff removes elements
       that are not re-emitted on the current run, so guarding the call would
       cause the ``<style>`` element to vanish on the second screen.
    """
    safe_css = _sanitize_css_for_markdown(CSS)
    st.markdown(FONTS_LINK + f"<style>{safe_css}</style>", unsafe_allow_html=True)
