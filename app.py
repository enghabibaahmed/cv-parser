import json

import requests
import streamlit as st
from pypdf import PdfReader

st.set_page_config(page_title="AI CV Parser", page_icon="📄", layout="wide")

HEADERS = {"ngrok-skip-browser-warning": "true"}

st.markdown(
    """
<style>
.chip{display:inline-block;padding:5px 14px;margin:4px 4px 4px 0;border-radius:999px;
      background:#EEF2FF;color:#3730A3;font-size:.85rem;font-weight:600}
.card{border:1px solid rgba(128,128,128,.28);border-radius:14px;padding:14px 18px;margin-bottom:10px}
.card h4{margin:0 0 2px 0;font-size:1.05rem}
.muted{opacity:.7;font-size:.9rem}
.hero{padding:18px 22px;border-radius:16px;
      background:linear-gradient(135deg,#4F46E5 0%,#7C3AED 100%);color:white;margin-bottom:18px}
.hero h1{margin:0;font-size:1.8rem}
.hero p{margin:4px 0 0 0;opacity:.9}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------- helpers ----------------
def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def read_pdf(file) -> str:
    reader = PdfReader(file)
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


def call_api(base_url: str, text: str) -> dict:
    r = requests.post(
        f"{base_url}/parse", json={"text": text}, headers=HEADERS, timeout=600
    )
    r.raise_for_status()
    return r.json()


# ---------------- sidebar ----------------
with st.sidebar:
    st.header("⚙️ Connection")
    api_url = st.text_input(
        "Kaggle ngrok URL", placeholder="https://xxxx.ngrok-free.app"
    ).strip().rstrip("/")

    if st.button("Test connection", use_container_width=True):
        if not api_url:
            st.warning("Paste the ngrok URL first.")
        else:
            try:
                r = requests.get(f"{api_url}/health", headers=HEADERS, timeout=15)
                if r.ok:
                    st.success("Connected ✅")
                else:
                    st.error(f"Server answered with status {r.status_code}")
            except Exception as e:
                st.error(f"Can't reach the server: {e}")

    st.divider()
    st.caption(
        "The model runs on Kaggle (GPU). This app only sends the CV text there "
        "and shows the result."
    )

# ---------------- header ----------------
st.markdown(
    """
<div class="hero">
  <h1>📄 AI CV Parser</h1>
  <p>Upload a resume and get clean, structured data in seconds.</p>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------- input ----------------
tab_pdf, tab_text = st.tabs(["📎 Upload PDF", "✍️ Paste text"])
cv_text = ""

with tab_pdf:
    uploaded = st.file_uploader("Drop a CV (PDF)", type=["pdf"])
    if uploaded:
        try:
            cv_text = read_pdf(uploaded)
        except Exception as e:
            st.error(f"Could not read this PDF: {e}")

with tab_text:
    pasted = st.text_area("Paste CV text", height=220)
    if pasted.strip():
        cv_text = pasted.strip()

if cv_text:
    with st.expander("Extracted text preview"):
        st.text(cv_text[:3000] + ("..." if len(cv_text) > 3000 else ""))
    if len(cv_text) > 6000:
        st.info("Long CV: only the first 6000 characters are sent to the model.")

go = st.button("✨ Parse CV", type="primary", disabled=not cv_text)

if go:
    if not api_url:
        st.error("Paste the Kaggle ngrok URL in the sidebar first.")
    else:
        with st.spinner("The model is reading the CV... (can take 30-90 seconds)"):
            try:
                st.session_state["result"] = call_api(api_url, cv_text)
            except Exception as e:
                st.session_state.pop("result", None)
                st.error(f"Request failed: {e}")

# ---------------- output ----------------
result = st.session_state.get("result")
if result:
    parsed = result.get("parsed")

    if not parsed:
        st.warning("The model's answer could not be read as JSON. Raw output:")
        st.code(result.get("raw", ""), language="text")
    else:
        skills = as_list(parsed.get("skills"))
        education = as_list(parsed.get("education"))
        experience = as_list(parsed.get("experience"))

        st.subheader("Candidate")
        c1, c2 = st.columns(2)
        c1.markdown(
            f'<div class="card"><div class="muted">Full name</div>'
            f'<h4>{parsed.get("full_name") or "—"}</h4></div>',
            unsafe_allow_html=True,
        )
        c2.markdown(
            f'<div class="card"><div class="muted">Email</div>'
            f'<h4>{parsed.get("email") or "—"}</h4></div>',
            unsafe_allow_html=True,
        )

        m1, m2, m3 = st.columns(3)
        m1.metric("Skills", len(skills))
        m2.metric("Education entries", len(education))
        m3.metric("Experience entries", len(experience))

        left, right = st.columns(2)

        with left:
            st.subheader("🎓 Education")
            if not education:
                st.caption("Nothing found.")
            for e in education:
                if isinstance(e, dict):
                    st.markdown(
                        f'<div class="card"><h4>{e.get("degree", "—")}</h4>'
                        f'<div class="muted">{e.get("institution", "")} · {e.get("year", "")}</div></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f'<div class="card">{e}</div>', unsafe_allow_html=True)

        with right:
            st.subheader("💼 Experience")
            if not experience:
                st.caption("Nothing found.")
            for x in experience:
                if isinstance(x, dict):
                    st.markdown(
                        f'<div class="card"><h4>{x.get("role", "—")}</h4>'
                        f'<div class="muted">{x.get("company", "")} · {x.get("years", "")}</div></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f'<div class="card">{x}</div>', unsafe_allow_html=True)

        st.subheader("🛠️ Skills")
        if skills:
            st.markdown(
                "".join(f'<span class="chip">{s}</span>' for s in skills),
                unsafe_allow_html=True,
            )
        else:
            st.caption("Nothing found.")

        st.divider()
        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(parsed, indent=2, ensure_ascii=False),
            file_name="parsed_cv.json",
            mime="application/json",
        )
        with st.expander("Raw JSON"):
            st.json(parsed)
