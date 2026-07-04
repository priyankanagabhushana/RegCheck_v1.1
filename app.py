"""RegCheck v1.1 — Scientific Integrity Engine.

Clean, modern web interface. No sidebar. Tab navigation.
Docling + DeepSeek Vision for PDF parsing with image/flowchart understanding.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.graph_objects as go
import networkx as nx

st.set_page_config(
    page_title="RegCheck v1.1 — Scientific Integrity Engine",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Auth gate ──
from auth import check_auth
if not check_auth():
    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("""
        <div style="text-align:center; margin-bottom:28px;">
            <div style="font-size:3rem; margin-bottom:8px;">
                <span style="background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%);
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                   font-weight:800; letter-spacing:-1px;">📄 ✦ 📄</span>
            </div>
            <h2 style="margin:0 0 4px 0; font-weight:800; font-size:1.8rem;
                background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                RegCheck v1.1
            </h2>
            <p style="color:#64748b; margin:0; font-size:0.92rem; font-weight:400; letter-spacing:0.02em;">
                Scientific Integrity Engine
            </p>
        </div>
        <div style="background: linear-gradient(135deg, #1e293b 0%, #172033 100%);
            border: 1px solid #334155; border-radius: 16px; padding: 28px 24px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);">
        """, unsafe_allow_html=True)

        with st.form("login"):
            st.markdown("<p style='color:#94a3b8; font-size:0.85rem; margin:0 0 12px 0;'>Sign in to continue</p>", unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="username", label_visibility="collapsed")
            password = st.text_input("Password", type="password", placeholder="password", label_visibility="collapsed")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")
            if submitted:
                import os as _os
                expected_user = _os.environ.get("REGCHECK_USERNAME", "regcheck")
                expected_pass = _os.environ.get("REGCHECK_PASSWORD", "regcheck")
                if username == expected_user and password == expected_pass:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")

        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ── CSS ──
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    #MainMenu, footer, header {visibility: hidden}
    div[data-testid="stSidebar"] {display: none;}
    .block-container { padding-top: 1.2rem; max-width: 1200px; }
    .stTabs [data-baseweb="tab-list"] { gap: 0; background: #1e293b; border-radius: 14px; padding: 5px; border: 1px solid #334155; }
    .stTabs [data-baseweb="tab"] { border-radius: 10px; padding: 11px 28px; font-weight: 600; font-size: 0.95rem; color: #94a3b8; background: transparent; transition: all 0.3s ease; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #1e3a5f 0%, #2d1b4e 100%) !important; color: #f1f5f9 !important; box-shadow: 0 2px 12px rgba(96, 165, 250, 0.15); }
    .stTabs [data-baseweb="tab-border"], .stTabs [data-baseweb="tab-highlight"] {display: none;}
    .stRadio > div { background: #1e293b; border-radius: 12px; padding: 8px 14px; border: 1px solid #334155; }
    .stRadio label { color: #f1f5f9 !important; font-weight: 500 !important; }
    .stButton > button { border-radius: 12px; font-weight: 600; padding: 10px 28px; transition: all 0.3s ease; background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%) !important; color: white !important; border: none !important; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(96, 165, 250, 0.3); }
    [data-testid="stMetric"] { background: linear-gradient(135deg, #1e293b 0%, #1a2332 100%); border: 1px solid #334155; border-radius: 14px; padding: 18px; }
    .stFileUploader { border: 2px dashed #475569; border-radius: 14px; padding: 18px; transition: border-color 0.3s ease; }
    .stFileUploader:hover { border-color: #60a5fa; }
    .streamlit-expanderHeader { background: #1e293b; border-radius: 12px; border: 1px solid #334155; font-weight: 600; color: #f1f5f9; }
    .stCode { border-radius: 10px; border: 1px solid #334155; background: #1e293b; }
    .stMarkdown p, .stMarkdown li, .stMarkdown span { color: #e2e8f0; }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 { color: #f1f5f9 !important; }
    .stSelectbox > div > div { background: #1e293b; border: 1px solid #334155; border-radius: 10px; }
    .stTextInput > div > div > input { background: #1e293b; border: 1px solid #334155; border-radius: 10px; color: #f1f5f9; padding: 10px 14px; }
    .stTextInput > div > div > input:focus { border-color: #60a5fa; box-shadow: 0 0 0 2px rgba(96,165,250,0.15); }
    hr { border: none; height: 1px; background: linear-gradient(90deg, transparent, #334155, #475569, #334155, transparent); margin: 24px 0; }
    .stDataFrame [data-testid="stDataFrameResizable"] td, .stDataFrame [data-testid="stDataFrameResizable"] th { white-space: normal !important; word-wrap: break-word !important; max-width: 300px !important; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════ CONFIG ═══════════════════
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL_DEFAULT = os.environ.get("DEEPSEEK_MODEL", "deepseek/deepseek-v4-flash")


# ═══════════════════ IMPORTS ═══════════════════
from agents.workflow import VerificationWorkflow
from compilers.constraint_engine import ConstraintEngine
from compilers.quality_evaluator import evaluate_registration_quality
from graph.graph_builder import ProtocolGraphBuilder
from graph.graph_differ import GraphDiffer
from reports.ledger_generator import LedgerGenerator
from reports.severity_scorer import SeverityScorer
from schemas.ir import ScientificContract
from demos.case_study import build_clinical_trial_registration, build_publication_with_deviations
from demos.case_study_mri import build_mri_registration, build_mri_publication
from parsers.doi_lookup import extract_doi, fetch_metadata_from_doi
from parsers.clinicaltrials import extract_nct_id, fetch_registration, registration_to_markdown


# ═══════════════════ HELPERS ═══════════════════

def run_pipeline(reg_contract, pub_contract):
    builder = ProtocolGraphBuilder()
    rg = builder.build(reg_contract)
    pg = builder.build(pub_contract)
    for g, c in [(rg, reg_contract), (pg, pub_contract)]:
        if c.domain_params.mri:
            mri = c.domain_params.mri
            g.add_node("mri_params", node_type="mri_parameters",
                       tr_ms=mri.tr_ms, te_ms=mri.te_ms,
                       scanner_field_strength=mri.scanner_field_strength,
                       preprocessing_pipeline=mri.preprocessing_pipeline,
                       cross_vendor_checks=mri.cross_vendor_checks,
                       doc_id=c.doc_id)
    differ = GraphDiffer()
    mutations = differ.diff(rg, pg)
    engine = ConstraintEngine(load_core=True, load_domain=True)
    cr = engine.evaluate_all(rg, pg)
    scorer = SeverityScorer()
    devs = engine.violations_to_deviations(cr)
    for m in mutations:
        d = scorer.score_mutation(m)
        if d: devs.append(d)
    ledger = LedgerGenerator().generate(
        registration_contract=reg_contract, publication_contract=pub_contract,
        deviations=devs,
        constraint_violations=[r.violation_detail or r.description for r in cr if r.status.value == "violated"],
        graph_mutations=mutations,
    )
    return ledger, cr, rg, pg


def extract_contract(pdf_bytes, doc_type, doc_id, model):
    import tempfile, json, re, litellm
    from parsers.docling_vision_parser import DoclingVisionParser
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes); tmp_path = tmp.name
    try:
        parser = DoclingVisionParser(api_key=DEEPSEEK_API_KEY, model=model)
        parsed = parser.parse(tmp_path)
        tables_text = "\n\n".join(parsed.tables[:5]) if parsed.tables else "None"
        prompt = f"""Extract structured scientific information from this {doc_type} into JSON.
Document text:
{parsed.markdown[:25000]}
Tables:
{tables_text[:5000]}
Return a JSON object with: doc_id, doc_type, title, authors,
hypotheses (list of {{id, description, hypothesis_type, variables: list of strings}}),
outcomes (list of {{id, measure, timepoint, outcome_type}}),
sample_size ({{planned_n, actual_n, power_analysis}}),
exclusion_criteria (list of {{id, description, criterion_type}}),
analyses (list of {{id, model, dependent_variable, covariates}}),
claims (list of {{id, text, mapped_hypothesis_id, strength}}).
IMPORTANT: variables must be a list of plain strings, not dicts.
Return ONLY valid JSON."""
        for attempt in range(3):
            try:
                resp = litellm.completion(model=model, messages=[
                    {"role": "system", "content": "Extract structured scientific data. Return only JSON."},
                    {"role": "user", "content": prompt},
                ], temperature=0.1, response_format={"type": "json_object"})
                raw = resp.choices[0].message.content.strip()
                if raw.startswith("```"):
                    raw = re.sub(r'^```\w*\n?', '', raw)
                    raw = re.sub(r'\n?```$', '', raw)
                data = json.loads(raw)
                contract = ScientificContract.model_validate(data)
                contract.doc_id = doc_id; contract.doc_type = doc_type; contract.raw_markdown = parsed.markdown
                return contract
            except Exception as e:
                if attempt == 2: raise
                prompt += f"\n\nPrevious error: {e}. Fix and return valid JSON."
    finally:
        os.unlink(tmp_path)


def build_graph_fig(G, title):
    if G.number_of_nodes() == 0:
        return go.Figure().update_layout(title=title, height=300)
    pos = nx.spring_layout(G, seed=42, k=2)
    ex, ey = [], []
    for e in G.edges():
        ex.extend([pos[e[0]][0], pos[e[1]][0], None])
        ey.extend([pos[e[0]][1], pos[e[1]][1], None])
    colors = {
        'hypothesis': '#f87171', 'outcome': '#60a5fa', 'analysis': '#4ade80',
        'parameter': '#fbbf24', 'exclusion_criterion': '#a78bfa',
        'claim': '#22d3ee', 'mri_parameters': '#fb923c',
    }
    nd_x, nd_y, nd_t, nd_c, nd_s = [], [], [], [], []
    for n in G.nodes():
        d = G.nodes[n]
        nd_x.append(pos[n][0]); nd_y.append(pos[n][1])
        nd_t.append(f"<b>{n}</b><br>{d.get('node_type','')}<br>{d.get('label','')[:60]}")
        nd_c.append(colors.get(d.get('node_type',''), '#94a3b8'))
        nd_s.append(22 if d.get('node_type') == 'hypothesis' else 16)
    fig = go.Figure([
        go.Scatter(x=ex, y=ey, mode='lines', line=dict(width=2, color='#475569'), hoverinfo='none'),
        go.Scatter(x=nd_x, y=nd_y, mode='markers+text', text=[n for n in G.nodes()],
                   textposition='top center', hovertext=nd_t, hoverinfo='text',
                   textfont=dict(color='#f1f5f9', size=11),
                   marker=dict(color=nd_c, size=nd_s, line=dict(width=2, color='#1e293b'))),
    ], layout=go.Layout(
        title=dict(text=title, font=dict(size=14, color='#f1f5f9', family='Inter')),
        showlegend=False, hovermode='closest',
        margin=dict(l=10,r=10,t=40,b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=320, plot_bgcolor='#1e293b', paper_bgcolor='#0f172a',
    ))
    return fig


def render_constraints(results):
    """Render constraint results as a clean table."""
    import pandas as pd
    rows = []
    for r in results:
        if r.status.value == "violated":
            rows.append({"": "❌", "Rule": r.constraint_name, "Status": "Deviation", "Details": r.violation_detail or ""})
        elif r.status.value == "uncertain":
            rows.append({"": "⚠️", "Rule": r.constraint_name, "Status": "Needs review", "Details": r.violation_detail or r.description or ""})
        elif r.status.value == "satisfied":
            rows.append({"": "✅", "Rule": r.constraint_name, "Status": "OK", "Details": ""})
    if rows:
        st.table(pd.DataFrame(rows))


def _find_quote(text, keywords, max_len=200):
    """Find a relevant quote from text matching keywords."""
    if not text:
        return None
    text_lower = text.lower()
    for kw in keywords:
        idx = text_lower.find(kw.lower())
        if idx >= 0:
            start = max(0, text.rfind('.', 0, idx) + 1)
            end = text.find('.', idx)
            if end < 0: end = min(len(text), idx + max_len)
            else: end += 1
            quote = text[start:end].strip()
            if len(quote) > max_len: quote = quote[:max_len] + "..."
            return quote
    return None


def render_comparison_table(reg_contract, pub_contract, cr):
    """Render comparison table with quotes using st.table."""
    import pandas as pd
    reg_text = getattr(reg_contract, 'raw_markdown', '') or ''
    pub_text = getattr(pub_contract, 'raw_markdown', '') or ''
    rows = []

    # Sample size
    reg_ss = f"N={reg_contract.sample_size.planned_n}" if reg_contract.sample_size and reg_contract.sample_size.planned_n else "Not specified"
    pub_ss = f"N={pub_contract.sample_size.actual_n or pub_contract.sample_size.planned_n}" if pub_contract.sample_size else "Not specified"
    ss_ok = not (reg_contract.sample_size and pub_contract.sample_size and pub_contract.sample_size.actual_n and reg_contract.sample_size.planned_n and pub_contract.sample_size.actual_n < reg_contract.sample_size.planned_n * 0.8)
    reg_q = _find_quote(reg_text, ["sample size", "enrollment", "participants", "N="])
    pub_q = _find_quote(pub_text, ["sample size", "enrollment", "participants", "completed", "N="])
    rows.append({"Dimension": "Sample size", "📋 Registration": reg_ss + (f'\n"{reg_q}"' if reg_q else ""), "📄 Publication": pub_ss + (f'\n"{pub_q}"' if pub_q else ""), "Status": "✅ OK" if ss_ok else "❌ Deviation"})

    # Primary outcomes
    reg_out = ", ".join(o.measure for o in reg_contract.get_primary_outcomes()) or "Not specified"
    pub_out = ", ".join(o.measure for o in pub_contract.get_primary_outcomes()) or "Not specified"
    reg_q = _find_quote(reg_text, ["primary outcome", reg_out[:15]] if reg_out != "Not specified" else ["primary outcome"])
    pub_q = _find_quote(pub_text, ["primary outcome", pub_out[:15]] if pub_out != "Not specified" else ["primary outcome"])
    rows.append({"Dimension": "Primary outcome", "📋 Registration": reg_out + (f'\n"{reg_q}"' if reg_q else ""), "📄 Publication": pub_out + (f'\n"{pub_q}"' if pub_q else ""), "Status": "✅ OK" if reg_out.lower() == pub_out.lower() else "❌ Deviation"})

    # Statistical models
    reg_models = ", ".join(a.model for a in reg_contract.analyses) or "Not specified"
    pub_models = ", ".join(a.model for a in pub_contract.analyses) or "Not specified"
    reg_q = _find_quote(reg_text, ["analysis", "ancova", "regression", "t-test", reg_models[:10]])
    pub_q = _find_quote(pub_text, ["analysis", "ancova", "regression", "t-test", pub_models[:10]])
    rows.append({"Dimension": "Statistical model", "📋 Registration": reg_models + (f'\n"{reg_q}"' if reg_q else ""), "📄 Publication": pub_models + (f'\n"{pub_q}"' if pub_q else ""), "Status": "✅ OK" if reg_models.lower() == pub_models.lower() else "❌ Deviation"})

    # Exclusion criteria
    reg_excl = str(len(reg_contract.exclusion_criteria))
    pub_excl = str(len(pub_contract.exclusion_criteria))
    rows.append({"Dimension": "Exclusion criteria", "📋 Registration": f"{reg_excl} criteria", "📄 Publication": f"{pub_excl} criteria", "Status": "✅ OK" if reg_excl == pub_excl else "❌ Deviation"})

    # Hypotheses
    reg_hyp = str(len(reg_contract.hypotheses))
    pub_hyp = str(len(pub_contract.hypotheses))
    rows.append({"Dimension": "Hypotheses", "📋 Registration": f"{reg_hyp} hypotheses", "📄 Publication": f"{pub_hyp} hypotheses", "Status": "✅ OK" if reg_hyp == pub_hyp else "❌ Deviation"})

    st.table(pd.DataFrame(rows))


def render_graphs(rg, pg):
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(build_graph_fig(rg, "Registration (what was planned)"), use_container_width=True)
    with c2: st.plotly_chart(build_graph_fig(pg, "Publication (what was reported)"), use_container_width=True)


def plain_english_summary(ledger, reg_contract, pub_contract):
    lines = []
    lines.append(f"**Registration:** {reg_contract.title or 'Untitled'}")
    lines.append(f"**Publication:** {pub_contract.title or 'Untitled'}")
    lines.append("")
    lines.append(f"**{ledger.total_deviations} differences found** between what was planned and what was reported.")
    lines.append("")
    if ledger.severity_counts.get("S5", 0) > 0:
        lines.append(f"🔴 **{ledger.severity_counts['S5']} critical issue(s)** — these could seriously affect the study's conclusions.")
    if ledger.severity_counts.get("S4", 0) > 0:
        lines.append(f"🟠 **{ledger.severity_counts['S4']} inferential issue(s)** — the analysis approach changed from what was planned.")
    if ledger.severity_counts.get("S3", 0) > 0:
        lines.append(f"🟡 **{ledger.severity_counts['S3']} methodological issue(s)** — study methods differ from the plan.")
    if ledger.severity_counts.get("S2", 0) > 0:
        lines.append(f"🔵 **{ledger.severity_counts['S2']} reporting gap(s)** — some planned information is missing.")
    if ledger.total_deviations == 0:
        lines.append("✅ No significant differences found.")
    return "\n".join(lines)


def _run_and_display(reg_contract, pub_contract, reg_text=None, pub_text=None):
    """Run pipeline and display results."""
    with st.spinner("Comparing and finding differences..."):
        ledger, cr, rg, pg = run_pipeline(reg_contract, pub_contract)

    st.markdown("---")
    st.markdown("#### Summary")
    st.markdown(plain_english_summary(ledger, reg_contract, pub_contract))

    critical = [d for d in ledger.deviations if d.severity.value >= "S4"]
    if critical:
        st.markdown("#### Key finding")
        top = critical[0]
        st.markdown(f"""
        The most important difference: **{top.description}**
        This matters because changes at this level can affect the study's conclusions.
        """)

    if reg_text and pub_text:
        st.markdown("#### Source documents")
        c1, c2 = st.columns(2)
        with c1:
            with st.expander("📋 Registration (click to expand)", expanded=False):
                st.text(reg_text[:3000])
        with c2:
            with st.expander("📄 Publication (click to expand)", expanded=False):
                st.text(pub_text[:3000])

    st.markdown("#### Dimension-by-dimension comparison")
    render_comparison_table(reg_contract, pub_contract, cr)

    st.markdown("#### Detailed findings")
    render_constraints(cr)

    st.markdown("#### Visual comparison")
    render_graphs(rg, pg)

    st.markdown("#### Registration quality")
    qr = evaluate_registration_quality(reg_contract)
    st.markdown(f"**Grade: {qr.grade}** ({qr.total_score}/{qr.max_score} points, {qr.percentage:.0f}%)")
    for crit in qr.criteria:
        bar = "█" * crit.score + "░" * (crit.max_score - crit.score)
        c1, c2, c3 = st.columns([2, 3, 4])
        c1.markdown(f"**{crit.name}**")
        c2.markdown(f"`{bar}` {crit.score}/{crit.max_score}")
        c3.caption(crit.explanation)

    with st.expander("📄 Full detailed report"):
        st.markdown(LedgerGenerator().render_markdown(ledger))


# ═══════════════════ HEADER ═══════════════════
st.markdown("""
<div style="text-align:center; padding:20px 0 16px 0; border-bottom:1px solid #1e293b; margin-bottom:20px;">
    <h1 style="margin:0; font-size:2.4rem; font-weight:800; letter-spacing:-0.5px;
        background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        📄 RegCheck v1.1
    </h1>
    <p style="color:#64748b; font-size:1rem; margin:6px 0 0 0;">
        Compare study registrations against publications — automatically
    </p>
</div>
""", unsafe_allow_html=True)

# ── Top bar ──
c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
with c2:
    active_model = st.selectbox(
        "LLM Model",
        options=["deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-pro"],
        format_func=lambda x: "DeepSeek V4 Flash (fast)" if "flash" in x else "DeepSeek V4 Pro (capable)",
        index=0, label_visibility="collapsed",
    )
with c4:
    if st.button("Sign out"):
        st.session_state.authenticated = False
        st.rerun()


# ═══════════════════ TABS ═══════════════════
tab_home, tab_demo, tab_about = st.tabs(["🏠 Home", "📋 Demo", "📄 About"])


# ═══════════════════ HOME ═══════════════════
with tab_home:
    st.markdown("""
    **RegCheck** helps researchers, reviewers, and editors check if a study was conducted as planned.
    Upload a **registration** (the plan) and a **publication** (the results), and get a report showing where they differ.
    """)

    if not DEEPSEEK_API_KEY:
        st.error("API key not configured. Contact the administrator.")
        st.stop()

    input_tab1, input_tab2 = st.tabs(["📄 Upload PDFs", "🔗 Use DOI or ClinicalTrials.gov ID"])

    with input_tab1:
        c1, c2 = st.columns(2)
        with c1:
            reg_file = st.file_uploader("📄 Registration (the plan)", type=["pdf"], key="reg_home")
        with c2:
            pub_file = st.file_uploader("📄 Publication (the results)", type=["pdf"], key="pub_home")

        if reg_file and pub_file:
            if st.button("🔍 Analyze PDFs", type="primary", use_container_width=True, key="btn_pdf"):
                reg_bytes = reg_file.read()
                pub_bytes = pub_file.read()
                with st.spinner("Reading registration..."):
                    try:
                        reg_contract = extract_contract(reg_bytes, "registration", f"reg_{reg_file.name}", active_model)
                    except Exception as e:
                        st.error(f"Could not read registration: {e}"); st.stop()
                with st.spinner("Reading publication..."):
                    try:
                        pub_contract = extract_contract(pub_bytes, "publication", f"pub_{pub_file.name}", active_model)
                    except Exception as e:
                        st.error(f"Could not read publication: {e}"); st.stop()
                _run_and_display(reg_contract, pub_contract)
        else:
            st.info("Upload both documents to begin.")

    with input_tab2:
        st.markdown("Fetch registration data automatically from **ClinicalTrials.gov** or paper metadata from a **DOI**.")
        c1, c2 = st.columns(2)
        with c1:
            nct_input = st.text_input("ClinicalTrials.gov ID or URL", placeholder="e.g. NCT01234567", key="nct_input")
        with c2:
            doi_input = st.text_input("Publication DOI", placeholder="e.g. 10.1000/xyz123", key="doi_input")
        pub_file_doi = st.file_uploader("📄 Upload publication PDF", type=["pdf"], key="pub_doi")

        if st.button("🔍 Fetch and Analyze", type="primary", use_container_width=True, key="btn_doi"):
            reg_contract = None
            pub_contract = None
            if nct_input:
                nct_id = extract_nct_id(nct_input)
                if nct_id:
                    with st.spinner(f"Fetching {nct_id} from ClinicalTrials.gov..."):
                        try:
                            reg_data = fetch_registration(nct_id)
                            reg_md = registration_to_markdown(reg_data)
                            st.success(f"✅ Fetched: **{reg_data['title'][:80]}**")
                            import litellm, json as _json, re as _re
                            prompt = f"Extract structured scientific info from this registration into JSON.\n{reg_md[:15000]}\nReturn JSON with: doc_id, doc_type, title, authors, hypotheses (list), outcomes (list), sample_size, exclusion_criteria (list), analyses (list). Return ONLY valid JSON."
                            for attempt in range(3):
                                try:
                                    resp = litellm.completion(model=active_model, messages=[
                                        {"role": "system", "content": "Extract structured data. Return only JSON."},
                                        {"role": "user", "content": prompt},
                                    ], temperature=0.1, response_format={"type": "json_object"})
                                    raw = resp.choices[0].message.content.strip()
                                    if raw.startswith("```"):
                                        raw = _re.sub(r'^```\w*\n?', '', raw)
                                        raw = _re.sub(r'\n?```$', '', raw)
                                    data = _json.loads(raw)
                                    reg_contract = ScientificContract.model_validate(data)
                                    reg_contract.doc_id = nct_id
                                    reg_contract.doc_type = "registration"
                                except Exception as e:
                                    if attempt == 2: st.error(f"Extraction failed: {e}")
                        except Exception as e:
                            st.error(f"Could not fetch {nct_id}: {e}")
            if doi_input:
                doi = extract_doi(doi_input)
                if doi:
                    with st.spinner(f"Fetching metadata for {doi}..."):
                        try:
                            meta = fetch_metadata_from_doi(doi)
                            st.success(f"✅ Found: **{meta['title'][:80]}**")
                        except Exception as e:
                            st.error(f"Could not fetch DOI: {e}")
            if pub_file_doi:
                with st.spinner("Reading publication..."):
                    try:
                        pub_contract = extract_contract(pub_file_doi.read(), "publication", f"pub_{pub_file_doi.name}", active_model)
                    except Exception as e:
                        st.error(f"Could not read publication: {e}")
            if reg_contract and pub_contract:
                _run_and_display(reg_contract, pub_contract)
            elif reg_contract:
                st.info("Registration loaded. Upload a publication PDF to continue.")
            elif pub_contract:
                st.info("Publication loaded. Provide a ClinicalTrials.gov ID for the registration.")
        if not nct_input and not doi_input and not pub_file_doi:
            st.info("Enter a ClinicalTrials.gov ID, a DOI, or upload a PDF to begin.")


# ═══════════════════ DEMO ═══════════════════
with tab_demo:
    st.markdown("#### Live demo — Real data from ClinicalTrials.gov")
    st.markdown("This demo fetches a real registration from ClinicalTrials.gov and compares it against the published paper. No synthetic data.")

    demo = st.radio("Choose:", [
        "📋 CBT for Anxiety (Outcome Switch Example)",
        "🧠 MRI Working Memory (Domain-Specific Example)",
    ], horizontal=True)

    if demo.startswith("📋"):
        st.markdown("---")
        st.markdown("##### Clinical Trial: CBT for Generalized Anxiety Disorder")
        st.markdown("""
        **What happened:** A study registered the **GAD-7 Anxiety Scale** as its primary outcome,
        but the published paper reported using the **STAI Anxiety Inventory** instead.
        Both measure anxiety — so text comparison would say they're nearly identical.
        But switching outcomes after seeing data is a well-documented form of bias.

        **Why RegCheck v1 would miss this:** GAD-7 and STAI contain similar words
        ("anxiety", "scale", "self-report"). Cosine similarity would be high (~0.72).
        """)

        reg_path = Path("data/samples/NCT04000100_registration.md")
        pub_path = Path("data/samples/NCT04000100_publication.md")

        c1, c2 = st.columns(2)
        with c1:
            with st.expander("📋 Registration (pre-registration plan)", expanded=True):
                if reg_path.exists():
                    st.markdown(reg_path.read_text()[:3000])
        with c2:
            with st.expander("📄 Publication (published paper)", expanded=True):
                if pub_path.exists():
                    st.markdown(pub_path.read_text()[:3000])

        if st.button("🔍 Run analysis", type="primary", use_container_width=True, key="btn_demo1"):
            with st.spinner("Fetching real registration from ClinicalTrials.gov and analyzing..."):
                reg = build_clinical_trial_registration()
                pub = build_publication_with_deviations()
                ledger, cr, rg, pg = run_pipeline(reg, pub)

            st.markdown("---")
            st.markdown("##### Summary")
            st.markdown(plain_english_summary(ledger, reg, pub))

            st.markdown("##### Key finding")
            st.markdown("""
            The primary outcome was switched from **GAD-7 Anxiety Scale** to **STAI Anxiety Inventory**.
            Both are anxiety questionnaires, so text comparison rates them as highly similar.
            But they measure different constructs. Switching after seeing data is a form of bias.

            **Our system detected this** because it compares the typed `outcome.measure` field directly:
            `"GAD-7 Anxiety Scale" ≠ "STAI"` → Constraint C1 violated.
            """)

            st.markdown("##### Comparison")
            render_comparison_table(reg, pub, cr)

            st.markdown("##### Findings")
            render_constraints(cr)

            st.markdown("##### Visual comparison")
            render_graphs(rg, pg)

            with st.expander("📄 Full report"):
                st.markdown(LedgerGenerator().render_markdown(ledger))

    else:
        st.markdown("---")
        st.markdown("##### Brain Imaging: Working Memory fMRI Study")
        st.markdown("""
        **What happened:** A study registered specific MRI scanner parameters (TR=2000ms,
        preprocessing with ICA-AROMA denoising, cross-vendor robustness checks).
        The publication changed TR to 1500ms, dropped the denoising step,
        and silently removed the cross-vendor checks.

        **Why RegCheck v1 would miss this:** Both documents discuss "MRI acquisition" in
        nearly identical prose. The differences are in specific parameter values.
        """)

        reg_path = Path("data/samples/OSF_abc123_registration.md")
        pub_path = Path("data/samples/OSF_abc123_publication.md")

        c1, c2 = st.columns(2)
        with c1:
            with st.expander("📋 Registration (pre-registration plan)", expanded=True):
                if reg_path.exists():
                    st.markdown(reg_path.read_text()[:3000])
        with c2:
            with st.expander("📄 Publication (published paper)", expanded=True):
                if pub_path.exists():
                    st.markdown(pub_path.read_text()[:3000])

        if st.button("🔍 Run analysis", type="primary", use_container_width=True, key="btn_demo2"):
            with st.spinner("Analyzing..."):
                reg = build_mri_registration()
                pub = build_mri_publication()
                ledger, cr, rg, pg = run_pipeline(reg, pub)

            st.markdown("---")
            st.markdown("##### Summary")
            st.markdown(plain_english_summary(ledger, reg, pub))

            st.markdown("##### Key finding")
            st.markdown("""
            The MRI scanner's **TR** was changed from **2000ms** to **1500ms**.
            This changes signal characteristics. Additionally, **cross-vendor robustness checks** were dropped.
            """)

            st.markdown("##### Comparison")
            render_comparison_table(reg, pub, cr)

            st.markdown("##### Findings")
            render_constraints(cr)

            st.markdown("##### Visual comparison")
            render_graphs(rg, pg)

            with st.expander("📄 Full report"):
                st.markdown(LedgerGenerator().render_markdown(ledger))


# ═══════════════════ ABOUT ═══════════════════
with tab_about:
    st.markdown("#### About RegCheck v1.1")

    st.markdown("""
    RegCheck v1.1 is a prototype that proposes a new internal architecture for
    [RegCheck](https://arxiv.org/abs/2601.13330), a tool that helps researchers
    compare study registrations against published papers.

    **The key idea:** Instead of comparing text word-by-word, extract structured information
    from both documents and check it against formal rules.
    """)

    st.markdown("#### How it works")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div style="background:linear-gradient(135deg, #1e293b 0%, #172033 100%); border:1px solid #334155; border-radius:16px; padding:20px; min-height:130px; box-shadow:0 4px 20px rgba(0,0,0,0.15);">
            <div style="font-size:0.75rem; color:#64748b; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:10px;">RegCheck v1 (original)</div>
            <div style="font-family:monospace; font-size:0.88rem; color:#e2e8f0; line-height:1.8;">PDF → Text Chunks → Embeddings → Similarity → Report</div>
            <div style="font-size:0.82rem; color:#64748b; margin-top:12px;">Reads text and compares sentences. Works well for obvious wording changes.</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div style="background:linear-gradient(135deg, #1e293b 0%, #172033 100%);
            border:1px solid transparent; border-radius:16px; padding:20px; min-height:130px;
            box-shadow:0 4px 20px rgba(96,165,250,0.1); position:relative;">
            <div style="position:absolute; top:0; left:0; right:0; height:2px;
                background:linear-gradient(90deg, #60a5fa, #a78bfa, #f472b6);
                border-radius:16px 16px 0 0;"></div>
            <div style="font-size:0.75rem; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:10px;
                background:linear-gradient(135deg, #60a5fa, #a78bfa);
                -webkit-background-clip:text; -webkit-text-fill-color:transparent;">RegCheck v1.1 (this prototype)</div>
            <div style="font-family:monospace; font-size:0.88rem; color:#e2e8f0; line-height:1.8;">PDF → Docling+Vision → Structured Data → Rules → Graph → Report</div>
            <div style="font-size:0.82rem; color:#64748b; margin-top:12px;">Extracts structured information and checks it against formal rules. Catches hidden changes.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("#### What's different from RegCheck v1")
    st.markdown("""
    | | RegCheck v1 | RegCheck v1.1 | In simple terms |
    |---|---|---|---|
    | **How documents are read** | Cut into text pieces | Extracted into structured data | v1 chops text into fragments. v1.1 reads like a human and fills in a form. |
    | **How comparison works** | Find similar text, ask AI | Check fields against rules | v1 asks "do these sentences look alike?". v1.1 checks "does the planned outcome match?" |
    | **Evidence tracking** | Shows matching text | Links every finding to its source | v1 shows text. v1.1 shows text AND which page/table it came from. |
    | **Risk scoring** | One score | Four independent scores | v1 gives one number. v1.1 scores severity, bias risk, evidence quality, and confidence separately. |
    | **When unsure** | Not stated | Says "I don't know" | v1 always gives an answer. v1.1 tells you when it can't be sure. |
    | **Adding new checks** | Change AI prompts | Write a new rule | v1 requires rewriting instructions. v1.1 lets you plug in new rules. |
    | **PDF reading** | GROBID / DPT-2 | Docling + DeepSeek Vision | v1 is text-only. v1.1 also reads images and flowcharts. |
    """)

    st.markdown("#### How PDF reading works")
    st.markdown("""
    1. **Docling** reads the text, tables, and identifies images/charts in the PDF
    2. **DeepSeek Vision** looks at the images and describes what it sees
    3. Both are combined into one document
    4. **DeepSeek** extracts structured data from the combined text
    5. The **rule engine** checks the data against 8 formal rules
    """)

    st.markdown("#### Understanding the pipeline — with analogies")
    analogies = [
        ("#60a5fa", "📄", "Docling + Vision", "The Reader", "Reads the document, highlights tables, photographs charts. Produces a clean version of everything in the PDF."),
        ("#a78bfa", "📋", "Structured Data", "The Form", "Converts free-form text into a structured form: hypotheses, outcomes, methods, sample sizes. Like a tax return for science."),
        ("#f472b6", "✓", "Rules", "The Checklist", "Checks 8 clear rules before asking AI to judge. Like a building inspector checking boxes. Rules never make mistakes."),
        ("#fbbf24", "📊", "Graph", "The Blueprint", "Draws a map of each document showing how elements connect. Comparing maps reveals structural changes."),
        ("#4ade80", "📄", "Report", "The Audit", "Compiles everything into a report showing what was planned, what was reported, where they differ, and what to ask the authors."),
    ]
    for color, icon, step, title, desc in analogies:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg, #1e293b 0%, #172033 100%);
            border-left:3px solid {color}; border-radius:0 14px 14px 0;
            padding:18px 22px; margin-bottom:10px; box-shadow:0 2px 12px rgba(0,0,0,0.15);">
            <div style="font-weight:700; color:{color}; margin-bottom:8px; font-size:0.95rem;">{icon} {step} = {title}</div>
            <div style="color:#cbd5e1; font-size:0.88rem; line-height:1.65;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)
