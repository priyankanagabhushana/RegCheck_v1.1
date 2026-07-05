"""RegCheck v1.1 — Scientific Integrity Engine.

Clean, modern web interface. No sidebar. Tab navigation.
Docling + DeepSeek Vision for PDF parsing with image/flowchart understanding.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.graph_objects as go
import networkx as nx

logger = logging.getLogger(__name__)

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
    from compilers.contract_extractor import ContractExtractor, _preclassify_document
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes); tmp_path = tmp.name
    try:
        parser = DoclingVisionParser(api_key=DEEPSEEK_API_KEY, model=model)
        parsed = parser.parse(tmp_path)

        # ── Defense-in-depth document classification ──
        # Layer 1: Deterministic pre-classifier (zero cost, catches obvious cases)
        doc_category = _preclassify_document(parsed.markdown)

        if doc_category is None:
            # Layer 2: LLM classifier (only if pre-classifier is uncertain)
            preview = parsed.markdown[:3000]
            classify_prompt = f"""Classify this document into exactly one category. Return ONLY the category name.
Categories:
- clinical_trial: A study with human participants, hypotheses, outcomes, sample sizes
- regulatory_guidance: An FDA/EMA guidance document defining thresholds or criteria (NOT a study)
- research_protocol: A detailed study protocol with methods and procedures
- other: Any other document type

IMPORTANT: A table of safety thresholds or operating conditions is NOT hypotheses.
A document titled "Guidance for Industry" is NOT a clinical trial.

Document:
{preview}

Category:"""
            try:
                resp = litellm.completion(model=model, messages=[
                    {"role": "system", "content": "Classify documents. Return exactly one word."},
                    {"role": "user", "content": classify_prompt},
                ], temperature=0.0, max_tokens=10)
                cat = resp.choices[0].message.content.strip().lower()
                cat = cat.replace("-", "_").replace(" ", "_")
                if cat in ("clinical_trial", "regulatory_guidance", "research_protocol", "other"):
                    doc_category = cat
                elif "guidance" in cat or "regulatory" in cat:
                    doc_category = "regulatory_guidance"
                else:
                    doc_category = "other"  # Fail closed
            except Exception:
                doc_category = "other"  # Fail closed

        logger.info(f"Document '{doc_id}' classified as: {doc_category}")
        st.info(f"📋 Document classified as **{doc_category.replace('_', ' ').title()}**")

        if doc_category != "clinical_trial":
            # Non-trial document: return minimal contract with structural comparison
            from datetime import datetime
            from schemas.ir import UncertaintyFlag, DomainSpecificParameters
            contract = ScientificContract(
                doc_id=doc_id, doc_type=doc_type,
                title=f"{doc_category.replace('_', ' ').title()}: {doc_id}",
                authors=[], hypotheses=[], outcomes=[], analyses=[],
                claims=[], exclusion_criteria=[], sample_size=None,
                domain_params=DomainSpecificParameters(),
                raw_markdown=parsed.markdown,
                extraction_confidence=0.0,
                overall_uncertainty=UncertaintyFlag(
                    is_uncertain=True,
                    reason=(
                        f"Document classified as '{doc_category}', not a clinical trial. "
                        "No hypotheses, outcomes, sample sizes, or analyses to extract. "
                        "Comparison will use structural text diff only."
                    ),
                    missing_data=[
                        "clinical trial hypotheses",
                        "primary/secondary outcomes",
                        "sample size justification",
                        "statistical analysis plan"
                    ],
                    resolution_suggestion=(
                        "This document is not suitable for clinical trial registration "
                        "comparison. The system will compare structural elements "
                        "(tables, thresholds, key values) instead."
                    ),
                ),
                compilation_timestamp=datetime.now(),
            )
            return contract

        # Clinical trial: use ContractExtractor for full extraction with evidence verification
        extractor = ContractExtractor(model=model, max_chars=25000)
        tables_text = "\n\n".join(parsed.tables[:5]) if parsed.tables else "None"

        # Evidence-guided retrieval: determine which fields have evidence BEFORE extraction
        from compilers.contract_extractor import _build_retrieval_hints
        retrieval_hints = _build_retrieval_hints(parsed.markdown[:25000])

        prompt = f"""Extract structured scientific information from this {doc_type} into JSON.
Document text:
{parsed.markdown[:25000]}
Tables:
{tables_text[:5000]}

{retrieval_hints}

Return a JSON object with: doc_id, doc_type, title, authors,
hypotheses (list of {{id, description, hypothesis_type, variables, status, evidence: [{{text, source_doc, section}}]}}),
outcomes (list of {{id, measure, timepoint, outcome_type, description, status, evidence: [{{text, source_doc, section}}]}}),
sample_size ({{planned_n, actual_n, power_analysis, status, evidence: [{{text, source_doc, section}}]}}),
exclusion_criteria (list of {{id, description, criterion_type}}),
analyses (list of {{id, model, dependent_variable, covariates}}),
claims (list of {{id, text, mapped_hypothesis_id, strength}}).

status field: "present" (extracted from doc), "missing" (absent), "low_evidence" (weak evidence), "not_applicable" (doesn't apply)

CRITICAL RULES:
- Every hypothesis, outcome, and sample_size MUST have at least one evidence span with exact text from the document.
- If the retrieval analysis says a field is NOT FOUND, set status to "missing" and return empty list [].
- Tables of thresholds or limits are NOT hypotheses. Do not convert table rows into hypotheses.

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
                # Apply evidence verification, retrieval enforcement, and sanity checks
                contract = extractor._verify_extraction_evidence(contract)
                contract = extractor._enforce_retrieval_results(contract, parsed.markdown[:25000])
                contract = extractor._validate_extraction_sanity(contract, doc_category)
                return contract
            except Exception as e:
                if attempt == 2: raise
                prompt += f"\n\nPrevious error: {e}. Fix and return valid JSON."
    finally:
        os.unlink(tmp_path)


def extract_contract_from_json(json_bytes, doc_type, doc_id, model):
    """Extract a ScientificContract from a JSON file.

    Handles two JSON formats:
    1. ClinicalTrials.gov API v2 JSON (has 'protocolSection' key)
       → Uses CTGovJSONParser for structured markdown conversion
    2. Generic JSON (metadata, abstracts, etc.)
       → Converts to markdown and extracts via LLM

    For CT.gov JSON, the structured fields (outcomes, eligibility, arms)
    are already typed, so the LLM extraction is more reliable than from PDF.
    """
    import json
    from parsers.ctgov_json_parser import CTGovJSONParser

    data = json.loads(json_bytes)

    # Check if this is CT.gov format
    if "protocolSection" in data:
        logger.info(f"Detected CT.gov JSON format for {doc_id}")
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(data, tmp)
            tmp_path = tmp.name
        try:
            parser = CTGovJSONParser()
            parsed = parser.parse(tmp_path)
        finally:
            os.unlink(tmp_path)

        # CT.gov JSON is already structured — extract directly
        extractor = ContractExtractor(model=model, max_chars=50000)
        contract = extractor.extract(parsed, doc_type=doc_type)
        # Override doc_id to use the NCT ID from the JSON
        nct_id = data.get("protocolSection", {}).get("identificationModule", {}).get("nctId", "")
        if nct_id:
            contract.doc_id = nct_id
            contract.registration_id = nct_id
        return contract

    # Generic JSON — convert to markdown for LLM extraction
    logger.info(f"Generic JSON format for {doc_id}, converting to markdown")

    # Build markdown from JSON content
    md_parts = [f"# Document: {doc_id}", ""]

    # Try common JSON structures
    if "title" in data:
        md_parts.append(f"## Title\n{data['title']}")
    if "abstract" in data:
        md_parts.append(f"## Abstract\n{data['abstract']}")
    if "authors" in data:
        if isinstance(data["authors"], list):
            authors = ", ".join(
                a if isinstance(a, str) else a.get("family", str(a))
                for a in data["authors"]
            )
            md_parts.append(f"## Authors\n{authors}")
    if "message" in data and "abstract" in data.get("message", {}):
        md_parts.append(f"## Abstract\n{data['message']['abstract']}")
    if "description" in data:
        md_parts.append(f"## Description\n{data['description']}")

    # Include any string values as context
    for key, value in data.items():
        if isinstance(value, str) and len(value) > 50 and key not in ("title", "abstract", "description"):
            md_parts.append(f"## {key.replace('_', ' ').title()}\n{value}")

    markdown = "\n\n".join(md_parts)

    if len(markdown) < 100:
        st.warning("JSON file has very little text content. Extraction may be limited.")

    # Use the same classification + extraction pipeline as PDFs
    from datetime import datetime
    from schemas.ir import UncertaintyFlag, DomainSpecificParameters

    doc_category = _preclassify_document(markdown)

    if doc_category is None:
        # Try LLM classification
        try:
            import litellm
            resp = litellm.completion(model=model, messages=[
                {"role": "system", "content": "Classify documents. Return exactly one word."},
                {"role": "user", "content": f"Classify: clinical_trial, regulatory_guidance, research_protocol, or other.\n\n{markdown[:3000]}\n\nCategory:"},
            ], temperature=0.0, max_tokens=10)
            cat = resp.choices[0].message.content.strip().lower()
            cat = cat.replace("-", "_").replace(" ", "_")
            if cat in ("clinical_trial", "regulatory_guidance", "research_protocol", "other"):
                doc_category = cat
            else:
                doc_category = "other"
        except Exception:
            doc_category = "other"

    logger.info(f"JSON document '{doc_id}' classified as: {doc_category}")

    if doc_category != "clinical_trial":
        return ScientificContract(
            doc_id=doc_id, doc_type=doc_type,
            title=f"{doc_category.replace('_', ' ').title()}: {doc_id}",
            authors=[], hypotheses=[], outcomes=[], analyses=[],
            claims=[], exclusion_criteria=[], sample_size=None,
            domain_params=DomainSpecificParameters(),
            raw_markdown=markdown,
            extraction_confidence=0.0,
            overall_uncertainty=UncertaintyFlag(
                is_uncertain=True,
                reason=f"Document classified as '{doc_category}', not a clinical trial.",
            ),
            compilation_timestamp=datetime.now(),
        )

    # Extract from markdown
    extractor = ContractExtractor(model=model, max_chars=50000)

    from compilers.contract_extractor import _build_retrieval_hints
    retrieval_hints = _build_retrieval_hints(markdown[:50000])

    prompt = f"""Extract structured scientific information from this {doc_type} into JSON.
Document text:
{markdown[:50000]}

{retrieval_hints}

Return a JSON object with: doc_id, doc_type, title, authors,
hypotheses (list of {{id, description, hypothesis_type, variables, status, evidence: [{{text, source_doc, section}}]}}),
outcomes (list of {{id, measure, timepoint, outcome_type, description, status, evidence: [{{text, source_doc, section}}]}}),
sample_size ({{planned_n, actual_n, power_analysis, status, evidence: [{{text, source_doc, section}}]}}),
exclusion_criteria (list of {{id, description, criterion_type}}),
analyses (list of {{id, model, dependent_variable, covariates}}),
claims (list of {{id, text, mapped_hypothesis_id, strength}}).

status field: "present" (extracted from doc), "missing" (absent), "low_evidence" (weak evidence), "not_applicable" (doesn't apply)

CRITICAL RULES:
- Every hypothesis, outcome, and sample_size MUST have at least one evidence span with exact text from the document.
- If the retrieval analysis says a field is NOT FOUND, set status to "missing" and return empty list [].
- Tables of thresholds or limits are NOT hypotheses.

IMPORTANT: variables must be a list of plain strings, not dicts.
Return ONLY valid JSON."""
    import litellm, re
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
            contract.doc_id = doc_id
            contract.doc_type = doc_type
            contract.raw_markdown = markdown
            contract = extractor._verify_extraction_evidence(contract)
            contract = extractor._enforce_retrieval_results(contract, markdown[:50000])
            contract = extractor._validate_extraction_sanity(contract, doc_category)
            return contract
        except Exception as e:
            if attempt == 2: raise
            prompt += f"\n\nPrevious error: {e}. Fix and return valid JSON."


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
    nd_x, nd_y, nd_t, nd_c, nd_s, nd_lw, nd_lc = [], [], [], [], [], [], []
    for n in G.nodes():
        d = G.nodes[n]
        nd_x.append(pos[n][0]); nd_y.append(pos[n][1])
        status = d.get('status', 'present')
        status_note = f" ({status})" if status != 'present' else ""
        nd_t.append(f"<b>{n}</b><br>{d.get('node_type','')}{status_note}<br>{d.get('label','')[:60]}")
        nd_c.append(colors.get(d.get('node_type',''), '#94a3b8'))
        nd_s.append(22 if d.get('node_type') == 'hypothesis' else 16)
        # Dashed border for missing/low-evidence/not_applicable nodes
        if status in ('missing', 'low_evidence', 'not_applicable'):
            nd_lw.append(3)
            nd_lc.append('#f97316' if status == 'missing' else '#eab308' if status == 'low_evidence' else '#64748b')
        else:
            nd_lw.append(2)
            nd_lc.append('#1e293b')
    fig = go.Figure([
        go.Scatter(x=ex, y=ey, mode='lines', line=dict(width=2, color='#475569'), hoverinfo='none'),
        go.Scatter(x=nd_x, y=nd_y, mode='markers+text', text=[n for n in G.nodes()],
                   textposition='top center', hovertext=nd_t, hoverinfo='text',
                   textfont=dict(color='#f1f5f9', size=11),
                   marker=dict(color=nd_c, size=nd_s,
                              line=dict(width=nd_lw, color=nd_lc))),
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
        elif r.status.value == "missing":
            rows.append({"": "➖", "Rule": r.constraint_name, "Status": "No data", "Details": r.violation_detail or "Neither document contains this information"})
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
    # Check for non-trial documents
    reg_uncertain = reg_contract.overall_uncertainty.is_uncertain
    pub_uncertain = pub_contract.overall_uncertainty.is_uncertain

    if reg_uncertain or pub_uncertain:
        st.warning("⚠️ One or both documents were classified as non-clinical-trial documents.")
        if reg_uncertain:
            st.caption(f"Registration: {reg_contract.overall_uncertainty.reason}")
        if pub_uncertain:
            st.caption(f"Publication: {pub_contract.overall_uncertainty.reason}")

        # For non-trial document pairs, do structural text comparison
        _run_structural_comparison(reg_contract, pub_contract, reg_text, pub_text)
        return

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


def _run_structural_comparison(reg_contract, pub_contract, reg_text=None, pub_text=None):
    """Compare non-trial documents using structural text comparison.

    Instead of forcing clinical trial extraction, this compares the raw
    document text to find structural differences: added/removed sections,
    changed numerical values, modified tables, and updated language.

    This is the correct approach for regulatory guidance, policy documents,
    and other non-trial document types.
    """
    st.markdown("---")
    st.markdown("#### Structural Comparison")
    st.markdown(
        "These documents are not clinical trials. The system compares their "
        "structure and content directly, without forcing clinical trial extraction."
    )

    reg_raw = reg_contract.raw_markdown or ""
    pub_raw = pub_contract.raw_markdown or ""

    if not reg_raw or not pub_raw:
        st.warning("No document text available for comparison.")
        return

    # Basic structural metrics
    reg_lines = reg_raw.split('\n')
    pub_lines = pub_raw.split('\n')

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Registration length", f"{len(reg_raw):,} chars")
    with col2:
        st.metric("Publication length", f"{len(pub_raw):,} chars")
    with col3:
        st.metric("Length difference", f"{len(pub_raw) - len(reg_raw):+,} chars")

    # Find key numerical differences
    import re
    reg_numbers = set(re.findall(r'\b\d+\.?\d*\b', reg_raw))
    pub_numbers = set(re.findall(r'\b\d+\.?\d*\b', pub_raw))
    only_in_reg = reg_numbers - pub_numbers
    only_in_pub = pub_numbers - reg_numbers

    if only_in_reg or only_in_pub:
        st.markdown("#### Numerical differences")
        c1, c2 = st.columns(2)
        with c1:
            if only_in_reg:
                st.markdown("**Only in registration:**")
                for n in sorted(only_in_reg, key=float)[:20]:
                    st.code(n)
        with c2:
            if only_in_pub:
                st.markdown("**Only in publication:**")
                for n in sorted(only_in_pub, key=float)[:20]:
                    st.code(n)

    # Show key sections side by side
    st.markdown("#### Document content")
    c1, c2 = st.columns(2)
    with c1:
        with st.expander("📋 Registration content", expanded=True):
            st.text(reg_raw[:5000])
    with c2:
        with st.expander("📄 Publication content", expanded=True):
            st.text(pub_raw[:5000])


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

    input_tab1, input_tab2 = st.tabs(["📄 Upload Files", "🔗 Use DOI or ClinicalTrials.gov ID"])

    with input_tab1:
        st.markdown("Upload **PDF** or **JSON** (ClinicalTrials.gov format) files for registration and publication.")
        c1, c2 = st.columns(2)
        with c1:
            reg_file = st.file_uploader("📋 Registration (the plan)", type=["pdf", "json"], key="reg_home")
        with c2:
            pub_file = st.file_uploader("📄 Publication (the results)", type=["pdf", "json"], key="pub_home")

        if reg_file and pub_file:
            button_label = "🔍 Analyze Files"
            if st.button(button_label, type="primary", use_container_width=True, key="btn_pdf"):
                reg_bytes = reg_file.read()
                pub_bytes = pub_file.read()
                reg_is_json = reg_file.name.lower().endswith(".json")
                pub_is_json = pub_file.name.lower().endswith(".json")

                with st.spinner("Reading registration..."):
                    try:
                        if reg_is_json:
                            reg_contract = extract_contract_from_json(reg_bytes, "registration", f"reg_{reg_file.name}", active_model)
                        else:
                            reg_contract = extract_contract(reg_bytes, "registration", f"reg_{reg_file.name}", active_model)
                    except Exception as e:
                        st.error(f"Could not read registration: {e}"); st.stop()
                with st.spinner("Reading publication..."):
                    try:
                        if pub_is_json:
                            pub_contract = extract_contract_from_json(pub_bytes, "publication", f"pub_{pub_file.name}", active_model)
                        else:
                            pub_contract = extract_contract(pub_bytes, "publication", f"pub_{pub_file.name}", active_model)
                    except Exception as e:
                        st.error(f"Could not read publication: {e}"); st.stop()
                _run_and_display(reg_contract, pub_contract)
        else:
            st.info("Upload both documents to begin. Supports PDF and ClinicalTrials.gov JSON.")

    with input_tab2:
        st.markdown("Fetch registration data automatically from **ClinicalTrials.gov** or paper metadata from a **DOI**.")
        c1, c2 = st.columns(2)
        with c1:
            nct_input = st.text_input("ClinicalTrials.gov ID or URL", placeholder="e.g. NCT01234567", key="nct_input")
        with c2:
            doi_input = st.text_input("Publication DOI", placeholder="e.g. 10.1000/xyz123", key="doi_input")
        pub_file_doi = st.file_uploader("📄 Upload publication (PDF or JSON)", type=["pdf", "json"], key="pub_doi")

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
                        pub_bytes = pub_file_doi.read()
                        if pub_file_doi.name.lower().endswith(".json"):
                            pub_contract = extract_contract_from_json(pub_bytes, "publication", f"pub_{pub_file_doi.name}", active_model)
                        else:
                            pub_contract = extract_contract(pub_bytes, "publication", f"pub_{pub_file_doi.name}", active_model)
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

    st.divider()
    st.markdown("#### Scientific Contributions")

    contribs = [
        ("1. Scientific Contract IR", "Converts unstructured documents into typed Pydantic models with full provenance. Every hypothesis, outcome, and analysis becomes a structured field — enabling deterministic comparison instead of fuzzy text similarity."),
        ("2. Deterministic Constraint Engine", "8 formal rules (C1–C6 + MRI-C1, MRI-C2) evaluate assertions with four-state logic: SATISFIED / VIOLATED / UNCERTAIN / MISSING. The system explicitly reports when data is absent rather than inventing deviations."),
        ("3. Graph-Based Structural Comparison", "Detects inferential changes beyond semantic similarity. Structural diff finds added/removed nodes and edges. Semantic diff finds inferential drift (ANCOVA→t-test) and evidence gaps."),
        ("4. Evidence Provenance Chains", "Every deviation links to its source through Claim → Hypothesis → Outcome → Analysis → Evidence. Every finding is fully auditable."),
        ("5. Multi-Axis Severity Scoring", "Four independent axes: scientific severity (S0–S5), bias risk, evidence quality, and confidence — replacing single-score assessments."),
    ]
    for title, desc in contribs:
        st.markdown(f"**{title}** — {desc}")

    st.divider()
    st.markdown("#### Evaluation")
    st.markdown("""
    Benchmarked against the **COMPARE Trials dataset** (72 human-annotated trials, Goldacre et al. 2019).

    | Constraint | Precision | Recall | F1 |
    |-----------|-----------|--------|-----|
    | C1 — Outcome Switching | 0.27 | 1.00 | 0.42 |
    | C4 — Hypothesis Presence | 1.00 | 1.00 | 1.00 |
    | C5 — Claim-Hypothesis Mapping | 1.00 | 1.00 | 1.00 |
    | **Overall** | **0.75** | **1.00** | **0.86** |

    C1 acts as a broad catch-all (recall=1.00 but precision=0.27). Addressing this
    entanglement is the focus of the next research phase. Run `python main.py eval-cmd`
    for full per-constraint metrics and ablation study.
    """)
