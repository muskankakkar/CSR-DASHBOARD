"""
RMC Delhi CSR Intelligence Dashboard
HOD: Mr. Pankaj Kumar Dwivedi | Target FY2026-27: ₹100 Crore
Reads from CSV files in the data/ folder.
"""

import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template
import pandas as pd

app = Flask(__name__)
DATA = os.path.join(os.path.dirname(__file__), "data")
TARGET_L = 10000  # ₹100 Crore in Lakhs


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def csv(name):
    return pd.read_csv(os.path.join(DATA, name), dtype=str).fillna("")

def to_float(v, default=0.0):
    try: return float(str(v).replace(",", "").strip()) if str(v).strip() else default
    except: return default

def clean(v):
    s = str(v).strip()
    return s if s not in ("", "nan", "None") else None

def expiry(date_str):
    if not date_str: return {"status": "unknown", "expiry": None, "days_left": None}
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            d   = datetime.strptime(date_str.strip(), fmt)
            exp = d + timedelta(days=365)
            dl  = (exp - datetime.today()).days
            st  = "expired" if exp < datetime.today() else "expiring" if dl <= 365 else "ok"
            return {"status": st, "expiry": exp.strftime("%d-%m-%Y"), "days_left": dl}
        except: pass
    return {"status": "unknown", "expiry": None, "days_left": None}

def rows(df):
    return [
        {k: clean(v) for k, v in row.items()}
        for _, row in df.iterrows()
    ]


# ─── API ROUTES ───────────────────────────────────────────────────────────────

@app.route("/api/kpis")
def api_kpis():
    m25 = csv("05_mou_signed_fy2025_26.csv")
    m26 = csv("06_mou_signed_fy2026_27.csv")
    uc26 = csv("10_mou_under_consideration_fy2026_27.csv")

    t25  = sum(to_float(v) for v in m25["camp_value_lakhs"])
    t26  = sum(to_float(v) for v in m26["camp_value_lakhs"])
    tuc  = sum(to_float(v) for v in uc26["value_lakhs"])

    # Expiry check across both signed sheets
    exp_count = 0
    for df in [m25, m26]:
        for _, row in df.iterrows():
            e = expiry(clean(row.get("mou_date", "")))
            if e["status"] in ("expiring", "expired"):
                exp_count += 1

    return jsonify({
        "mou_count_2526": len(m25),
        "mou_value_2526": round(t25, 2),
        "mou_count_2627": len(m26),
        "mou_value_2627": round(t26, 2),
        "uc_count_2627":  len(uc26),
        "uc_value_2627":  round(tuc, 2),
        "expiring_count": exp_count,
        "target_lakhs":   TARGET_L,
        "target_pct":     round(t26 / TARGET_L * 100, 2),
        "last_updated":   datetime.now().strftime("%d %b %Y, %H:%M"),
    })


@app.route("/api/mou-signed/<fy>")
def api_mou_signed(fy):
    if fy == "2526":
        df = csv("05_mou_signed_fy2025_26.csv")
        fy_label = "2526"
    elif fy == "2627":
        df = csv("06_mou_signed_fy2026_27.csv")
        fy_label = "2627"
    else:
        df25 = csv("05_mou_signed_fy2025_26.csv")
        df25["fy"] = "2526"
        df26 = csv("06_mou_signed_fy2026_27.csv")
        df26["fy"] = "2627"
        df = pd.concat([df25, df26], ignore_index=True)
        fy_label = "both"

    out = []
    for _, row in df.iterrows():
        d = {
            "sno":            clean(row.get("sno","")),
            "cpse":           clean(row.get("cpse","")),
            "locations":      clean(row.get("locations","")),
            "value_lakhs":    to_float(row.get("camp_value_lakhs",0)),
            "mou_date":       clean(row.get("mou_date","")),
            "payment_status": clean(row.get("payment_status","")),
            "fy":             row.get("fy", fy_label),
        }
        d.update(expiry(d["mou_date"]))
        out.append(d)
    return jsonify(out)


@app.route("/api/under-consideration/<fy>")
def api_uc(fy):
    f = "10_mou_under_consideration_fy2026_27.csv" if fy == "2627" \
        else "09_mou_under_consideration_fy2025_26.csv"
    df = csv(f)
    out = []
    for _, row in df.iterrows():
        out.append({
            "sno":       clean(row.get("sno","")),
            "cpse":      clean(row.get("cpse","")),
            "locations": clean(row.get("locations","")),
            "value_lakhs": to_float(row.get("value_lakhs",0)),
            "remark":    clean(row.get("remark","")),
            "fy":        fy,
        })
    return jsonify(out)


@app.route("/api/mou-to-sign")
def api_mou_to_sign():
    df25 = csv("07_mou_to_be_signed_fy2025_26.csv")
    df26 = csv("08_mou_to_be_signed_fy2026_27.csv")
    def parse(df, fy):
        return [{"company": clean(r["company"]), "value_lakhs": to_float(r["value_lakhs"]), "fy": fy}
                for _, r in df.iterrows() if clean(r.get("company",""))]
    return jsonify({"fy2526": parse(df25, "2526"), "fy2627": parse(df26, "2627")})


@app.route("/api/distribution-done")
def api_dd():
    df = csv("02_distribution_done.csv")
    out = []
    for _, row in df.iterrows():
        cv = to_float(row.get("camp_value_inr", 0))
        out.append({
            "sno":         clean(row.get("sno","")),
            "cpse":        clean(row.get("cpse","")),
            "location":    clean(row.get("location","")),
            "state":       clean(row.get("state","")),
            "camp_value_inr": cv,
            "camp_value_lakhs": round(cv / 100000, 2),
            "noa":         clean(row.get("noa","")),
            "nob":         clean(row.get("nob","")),
            "dist_date":   clean(row.get("distribution_date","")),
            "camp_ids":    clean(row.get("camp_ids","")),
            "uc_status":   clean(row.get("uc_status","")),
        })
    return jsonify(out)


@app.route("/api/assessment-no-mou")
def api_anm():
    df = csv("04_assessment_done_dist_pending_no_mou.csv")
    out = []
    for _, row in df.iterrows():
        vi = to_float(row.get("value_inr", 0))
        out.append({
            "sub_category": clean(row.get("sub_category","")),
            "scheme":       clean(row.get("scheme","")),
            "state":        clean(row.get("state","")),
            "district":     clean(row.get("district","")),
            "camp_id":      clean(row.get("camp_id","")),
            "nob":          clean(row.get("nob","")),
            "noa":          clean(row.get("noa","")),
            "value_inr":    vi,
            "value_lakhs":  round(vi / 100000, 2),
        })
    return jsonify(out)


@app.route("/api/summary")
def api_summary():
    df = csv("01_summary.csv")
    return jsonify([
        {"status": clean(r["status"]), "fy": clean(r.get("fy","")), "value_lakhs": to_float(r.get("value_lakhs",0))}
        for _, r in df.iterrows() if clean(r.get("status",""))
    ])


@app.route("/api/pipeline")
def api_pipeline():
    df = csv("11_mou_pipeline.csv")
    return jsonify([
        {"cpse": clean(r["cpse"]), "locations": clean(r.get("locations","")),
         "value_lakhs": to_float(r.get("value_lakhs",0)), "remark": clean(r.get("remark",""))}
        for _, r in df.iterrows() if clean(r.get("cpse",""))
    ])


# Words that are too common to use for matching (suffixes, generic words)
_STOP = {
    "ltd", "limited", "the", "of", "and", "india", "indian", "corporation",
    "company", "corp", "pvt", "private", "national", "industries",
}

def _engaged_tokens():
    """
    Returns a flat set of meaningful short tokens (abbreviations + key words)
    extracted from every engaged company across all datasets.
    """
    import re
    def n(s): return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]', ' ', str(s).lower())).strip()
    def sig_toks(s):
        """Tokens that are genuinely identifying — not common stopwords."""
        return {w for w in n(s).split() if w not in _STOP}

    sources = [
        ("05_mou_signed_fy2025_26.csv",               "cpse"),
        ("06_mou_signed_fy2026_27.csv",               "cpse"),
        ("09_mou_under_consideration_fy2025_26.csv",   "cpse"),
        ("10_mou_under_consideration_fy2026_27.csv",   "cpse"),
        ("07_mou_to_be_signed_fy2025_26.csv",          "company"),
        ("08_mou_to_be_signed_fy2026_27.csv",          "company"),
        ("02_distribution_done.csv",                   "cpse"),
        ("11_mou_pipeline.csv",                        "cpse"),
    ]
    all_names = []
    for fname, col in sources:
        df = csv(fname)
        if col in df.columns:
            all_names += [str(v).strip() for v in df[col]
                          if str(v).strip() not in ("", "nan")]

    # Build: set of (normalised_full_name, significant_token_set)
    pairs = []
    for name in all_names:
        nn = n(name)
        st = sig_toks(name)
        if nn:
            pairs.append((nn, st))
    return pairs


# Explicit abbreviation → keyword mappings for CPSEs whose short name
# doesn't share tokens with their full name
_ABBREV_EXPANSIONS = {
    "aai":      ["airports authority"],
    "igl":      ["indraprastha gas"],
    "dtl":      ["delhi transco"],
    "pfc":      ["power finance corporation"],
    "pgcil":    ["power grid corporation", "powergrid"],
    "powergrid":["power grid corporation"],
    "gail":     ["gas authority", "gail india"],
    "iocl":     ["indian oil corporation"],
    "bel":      ["bharat electronics"],
    "hal":      ["hindustan aeronautics"],
    "nhpc":     ["national hydroelectric power"],
    "sail":     ["steel authority"],
    "bhel":     ["bharat heavy electricals"],
    "seci":     ["solar energy corporation"],
    "hurl":     ["hindustan urvarak"],
    "cwc":      ["central warehousing"],
    "ntpc":     ["national thermal power"],
    "rec":      ["rural electrification"],
    "nmdc":     ["national mineral development"],
    "npcil":    ["nuclear power corporation"],
    "npcl":     ["noida power"],
    "nbcc":     ["national buildings construction"],
    "hscc":     ["hospital services consultancy"],
    "edcil":    ["educational consultants"],
    "tcil":     ["telecommunications consultants"],
    "itpo":     ["india trade promotion"],
    "pnb":      ["punjab national bank"],
    "eil":      ["engineers india"],
    "apcpl":    ["aravali power"],
    "mdl":      ["mazagon dock"],
    "irctc":    ["indian railway catering"],
    "irfc":     ["indian railway finance"],
    "ireda":    ["renewable energy development"],
    "hridc":    ["haryana rail infrastructure"],
    "ppcl":     ["pragati power"],
    "ipgcl":    ["indraprastha power generation"],
    "aic":      ["agriculture insurance"],
    "hudco":    ["housing urban development"],
    "hscc":     ["hospital services"],
    "hurl":     ["hindustan urvarak"],
}


def _is_engaged(company_name, engaged_pairs):
    """
    Returns True if company_name matches any already-engaged company.
    Three strategies:
      1. Exact normalised name match
      2. Abbreviation expansion — checks if any engaged abbreviation expands to cover this company
      3. Significant token overlap (2+ non-generic tokens in common)
    """
    import re
    def n(s): return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]', ' ', str(s).lower())).strip()
    def sig_toks(s): return {w for w in n(s).split() if w not in _STOP}

    cn = n(company_name)
    ct = sig_toks(company_name)

    # Build flat set of all engaged normalised names for fast exact lookup
    engaged_names = {en for en, _ in engaged_pairs}

    # 1. Exact full-name match
    if cn in engaged_names:
        return True

    # 2. Abbreviation expansion: for each engaged company that IS a short abbreviation,
    #    check if its expansion keywords appear in the candidate company name
    for en, et in engaged_pairs:
        if en in _ABBREV_EXPANSIONS:
            for phrase in _ABBREV_EXPANSIONS[en]:
                if phrase in cn:
                    return True
        # Also check reverse: if candidate is an abbreviation, expand and check against engaged name
        if cn in _ABBREV_EXPANSIONS:
            for phrase in _ABBREV_EXPANSIONS[cn]:
                phrase_toks = set(phrase.split())
                if len(phrase_toks & et) >= 1:
                    return True

    # 3. Significant token overlap (2+ non-stopword tokens shared)
    for en, et in engaged_pairs:
        overlap = ct & et
        if len(overlap) >= 2:
            return True
        # Single token match only valid if it's a clear abbreviation (≤5 chars, not a common word)
        _not_unique = {"power", "energy", "finance", "bank", "trust", "fund",
                       "heavy", "steel", "coal", "solar", "wind", "hydro",
                       "north", "south", "east", "west", "new", "old"}
        for tok in overlap:
            if len(tok) <= 5 and tok not in _not_unique:
                return True

    return False


@app.route("/api/potential-companies")
def api_potential():
    engaged_pairs = _engaged_tokens()
    df = csv("12_potential_companies.csv")
    out = []
    for _, r in df.iterrows():
        co = clean(r.get("company_name", ""))
        if not co:
            continue
        if _is_engaged(co, engaged_pairs):
            continue          # already in contract / pipeline — skip
        out.append({
            "sno":          clean(r.get("sno","")),
            "type":         clean(r.get("type","")),
            "company":      co,
            "city":         clean(r.get("city_district","")),
            "profit_lakhs": to_float(r.get("profit_lakhs",0)),
            "csr_lakhs":    to_float(r.get("available_csr_lakhs",0)),
            "contact":      clean(r.get("contact_person","")),
            "designation":  clean(r.get("designation","")),
            "mobile":       clean(r.get("mobile","")),
        })
    return jsonify(out)


@app.route("/api/assessment-ready")
def api_ar():
    df = csv("03_assessment_done_ready_for_dist.csv")
    return jsonify(rows(df))


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    print("\n🚀 RMC Delhi CSR Dashboard → http://localhost:5000\n")
    app.run(debug=True, port=5000)
