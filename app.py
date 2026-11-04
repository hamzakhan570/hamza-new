"""
Imtihan Tayyari - exam practice from your own textbook chapter.

Students upload a chapter (PDF / Word / TXT / photos of pages). The app:
  1. generates board-style practice questions from that chapter only,
  2. checks the student's answers against the chapter,
  3. explains in English, Urdu or Roman Urdu.
"""
import base64
import html
import io
import json
import os
import re

import streamlit as st
from anthropic import Anthropic

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_CHARS = 60_000  # chapter text sent to the model (about 15k tokens)

st.set_page_config(page_title="Imtihan Tayyari", page_icon="📘", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;600&display=swap');
.urdu { direction: rtl; text-align: right; font-family: 'Noto Nastaliq Urdu', serif;
        line-height: 2.4; font-size: 1.15rem; }
.ltr  { line-height: 1.6; }
</style>
""",
    unsafe_allow_html=True,
)

LANGS = {
    "English": "Write in clear, simple English suitable for a Pakistani board-exam student.",
    "اردو (Urdu)": "Write in simple, clear Urdu using Urdu script. Keep technical terms in English in brackets where helpful.",
    "Roman Urdu": "Write in Roman Urdu (Urdu using English letters, the way Pakistani students type). Keep technical terms in English.",
}
LEVELS = {
    "Matric (Class 9-10)": "Pakistani Matric (SSC) board exam style: MCQs, short questions, long questions.",
    "Inter (Class 11-12)": "Pakistani Intermediate (HSSC) board exam style: MCQs, short questions, long/descriptive questions with higher depth.",
}


# ---------------------------------------------------------------- helpers
def get_secret(name):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name)


@st.cache_resource
def get_client():
    key = get_secret("ANTHROPIC_API_KEY")
    if not key:
        st.error("ANTHROPIC_API_KEY is not set. Add it in Streamlit secrets or as an environment variable.")
        st.stop()
    return Anthropic(api_key=key)


def ask_claude(system, content, max_tokens=4000):
    resp = get_client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": content}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Model did not return JSON")
    return json.loads(text[start : end + 1])


def show(text, big=False):
    """Render text; right-to-left Nastaliq if it contains Urdu script."""
    safe = html.escape(str(text)).replace("\n", "<br>")
    cls = "urdu" if re.search(r"[\u0600-\u06FF]", safe) else "ltr"
    st.markdown(f'<div class="{cls}">{safe}</div>', unsafe_allow_html=True)


def extract_pdf(file):
    from pypdf import PdfReader

    reader = PdfReader(file)
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def extract_docx(file):
    from docx import Document

    return "\n".join(p.text for p in Document(file).paragraphs)


def transcribe_images(files):
    blocks = []
    for f in files:
        data = base64.standard_b64encode(f.getvalue()).decode()
        media = "image/png" if f.name.lower().endswith("png") else "image/jpeg"
        blocks.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": data}})
    blocks.append(
        {
            "type": "text",
            "text": "These are photos of textbook pages, in order. Transcribe all the text exactly as written "
            "(English and/or Urdu). Describe diagrams or tables briefly in [brackets]. Output only the text.",
        }
    )
    return ask_claude("You are an accurate OCR transcriber.", blocks, max_tokens=8000)


# ---------------------------------------------------------------- password gate (optional)
pw = get_secret("APP_PASSWORD")
if pw and not st.session_state.get("authed"):
    entered = st.text_input("Password", type="password")
    if entered == pw:
        st.session_state.authed = True
        st.rerun()
    st.stop()

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Settings")
    level = st.selectbox("Level", list(LEVELS))
    subject = st.text_input("Subject (optional)", placeholder="Physics, Biology, Pak Studies, English...")
    explain_lang = st.radio("Explain in", list(LANGS), index=0)
    q_lang = st.selectbox("Questions in", ["Same language as chapter", "English", "Urdu"])
    types = st.multiselect(
        "Question types",
        ["MCQ", "Short question", "Long question"],
        default=["MCQ", "Short question", "Long question"],
    )
    n_q = st.slider("Number of questions", 3, 15, 8)
    difficulty = st.select_slider("Difficulty", ["Easy", "Medium", "Exam level"], value="Medium")
    st.caption("Answers are checked against your uploaded chapter only. AI can make mistakes - verify with your teacher or textbook.")

st.title("📘 Imtihan Tayyari")
st.write("Upload a chapter from your own textbook, practise, and get explanations in English, اردو or Roman Urdu.")

# ---------------------------------------------------------------- step 1: chapter
st.subheader("1. Upload your chapter")
up = st.file_uploader(
    "PDF, Word, TXT, or photos of pages (in page order)",
    type=["pdf", "docx", "txt", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
)
pasted = st.text_area("...or paste chapter text here", height=120)

if st.button("Read chapter", type="primary"):
    text = pasted.strip()
    images = [f for f in up if f.name.lower().endswith(("png", "jpg", "jpeg"))]
    try:
        with st.spinner("Reading chapter..."):
            for f in up:
                n = f.name.lower()
                if n.endswith(".pdf"):
                    text += "\n" + extract_pdf(f)
                elif n.endswith(".docx"):
                    text += "\n" + extract_docx(f)
                elif n.endswith(".txt"):
                    text += "\n" + f.getvalue().decode("utf-8", errors="ignore")
            if images:
                text += "\n" + transcribe_images(images[:10])
    except Exception as e:
        st.error(f"Could not read the file: {e}")
        text = ""
    text = text.strip()
    if len(text) < 200:
        st.warning("Very little text found. If your PDF is a scan, upload photos of the pages instead, or paste the text.")
    else:
        if len(text) > MAX_CHARS:
            st.info(f"Chapter is long - using the first {MAX_CHARS:,} characters. Upload long chapters in parts.")
            text = text[:MAX_CHARS]
        st.session_state.chapter = text
        st.session_state.pop("questions", None)
        st.session_state.pop("results", None)

chapter = st.session_state.get("chapter")
if chapter:
    with st.expander(f"Chapter loaded ({len(chapter):,} characters) - preview"):
        show(chapter[:1500] + ("..." if len(chapter) > 1500 else ""))

# ---------------------------------------------------------------- step 2: questions
if chapter:
    st.subheader("2. Create practice questions")
    if st.button("Generate questions"):
        if not types:
            st.warning("Pick at least one question type.")
        else:
            system = (
                "You are an experienced Pakistani board-exam paper setter. "
                f"{LEVELS[level]} Create questions ONLY from the chapter text provided - never from outside knowledge. "
                "Return ONLY valid JSON, no commentary."
            )
            qlang_rule = {
                "Same language as chapter": "Write questions in the same language as the chapter.",
                "English": "Write questions in English.",
                "Urdu": "Write questions in Urdu script.",
            }[q_lang]
            prompt = f"""Subject: {subject or 'not specified'}
Create {n_q} questions. Types allowed: {', '.join(types)}. Difficulty: {difficulty}.
{qlang_rule}
Marks: MCQ=1, Short question=2, Long question=5.
Mix the types sensibly and cover different parts of the chapter.

JSON schema:
{{"questions":[{{"id":1,"type":"mcq|short|long","marks":1,
"question":"...",
"options":["A) ...","B) ...","C) ...","D) ..."],   (MCQ only, otherwise omit)
"answer":"B"  (MCQ: correct letter) or "model answer written from the chapter" (short/long),
"source":"a short phrase (under 20 words) from the chapter that supports the answer"}}]}}

CHAPTER:
{chapter}"""
            try:
                with st.spinner("Writing questions..."):
                    data = parse_json(ask_claude(system, prompt, 6000))
                st.session_state.questions = data["questions"]
                st.session_state.pop("results", None)
            except Exception as e:
                st.error(f"Could not generate questions, please try again. ({e})")

# ---------------------------------------------------------------- step 3: answer
questions = st.session_state.get("questions")
if questions:
    st.subheader("3. Answer")
    with st.form("answers"):
        for i, q in enumerate(questions, 1):
            st.markdown(f"**Q{i}.** ({q.get('marks', 1)} mark{'s' if q.get('marks', 1) != 1 else ''})")
            show(q["question"])
            if q["type"] == "mcq":
                st.radio("Choose", q.get("options", []), index=None, key=f"ans_{q['id']}", label_visibility="collapsed")
            else:
                st.text_area("Your answer", key=f"ans_{q['id']}", height=100 if q["type"] == "short" else 180, label_visibility="collapsed")
            st.divider()
        submitted = st.form_submit_button("Check my answers", type="primary")

    if submitted:
        payload = []
        for q in questions:
            payload.append(
                {
                    "id": q["id"],
                    "type": q["type"],
                    "marks": q.get("marks", 1),
                    "question": q["question"],
                    "options": q.get("options"),
                    "reference_answer": q.get("answer"),
                    "student_answer": st.session_state.get(f"ans_{q['id']}") or "",
                }
            )
        system = (
            "You are a kind, accurate teacher marking a Pakistani board-exam practice test. "
            "Mark ONLY against the chapter text provided; never use outside knowledge to decide marks. "
            "If the chapter does not cover something, say so. Return ONLY valid JSON."
        )
        prompt = f"""{LANGS[explain_lang]}
Write feedback, model_answer, explanation and study_tips in that language.

For every question give:
- score: marks awarded (can be partial for short/long; MCQ is all or nothing)
- verdict: "correct" | "partial" | "incorrect" | "unanswered"
- feedback: 1-2 sentences on what the student got right/wrong
- model_answer: the ideal answer based on the chapter
- explanation: simple explanation of the concept so the student understands why
- chapter_reference: a short phrase (under 20 words) from the chapter that supports the answer

JSON schema:
{{"results":[{{"id":1,"score":0,"verdict":"","feedback":"","model_answer":"","explanation":"","chapter_reference":""}}],
"study_tips":"2-3 short tips on what to revise"}}

QUESTIONS AND STUDENT ANSWERS:
{json.dumps(payload, ensure_ascii=False)}

CHAPTER:
{chapter}"""
        try:
            with st.spinner("Checking against your chapter..."):
                res = parse_json(ask_claude(system, prompt, 8000))
            # MCQs are marked exactly in code, not by the model
            by_id = {r["id"]: r for r in res["results"]}
            for q in questions:
                if q["type"] == "mcq" and q["id"] in by_id:
                    choice = (st.session_state.get(f"ans_{q['id']}") or "").strip()[:1].upper()
                    ok = bool(choice) and choice == str(q.get("answer", "")).strip()[:1].upper()
                    by_id[q["id"]]["score"] = q.get("marks", 1) if ok else 0
                    by_id[q["id"]]["verdict"] = "correct" if ok else ("unanswered" if not choice else "incorrect")
            st.session_state.results = res
        except Exception as e:
            st.error(f"Could not check answers, please try again. ({e})")

# ---------------------------------------------------------------- results
res = st.session_state.get("results")
if res and questions:
    by_id = {r["id"]: r for r in res["results"]}
    total = sum(q.get("marks", 1) for q in questions)
    got = sum(float(by_id.get(q["id"], {}).get("score", 0)) for q in questions)
    st.subheader(f"Result: {got:g} / {total}")
    st.progress(min(got / total, 1.0) if total else 0)
    icons = {"correct": "✅", "partial": "🟡", "incorrect": "❌", "unanswered": "⚪"}
    for i, q in enumerate(questions, 1):
        r = by_id.get(q["id"])
        if not r:
            continue
        with st.expander(f"{icons.get(r.get('verdict'), '')} Q{i}  -  {r.get('score', 0)}/{q.get('marks', 1)}"):
            show(q["question"])
            st.markdown("**Feedback**")
            show(r.get("feedback", ""))
            st.markdown("**Model answer**")
            show(r.get("model_answer", ""))
            st.markdown("**Explanation**")
            show(r.get("explanation", ""))
            st.markdown("**From your chapter**")
            show(r.get("chapter_reference", ""))
    if res.get("study_tips"):
        st.subheader("What to revise")
        show(res["study_tips"])
    st.caption("Change the 'Explain in' language in the sidebar and press 'Check my answers' again to get explanations in another language.")
