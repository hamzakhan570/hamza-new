[README.md](https://github.com/user-attachments/files/34354761/README.md)
# Imtihan Tayyari 📘

Exam practice for Pakistani Matric and Inter students, built from **their own textbook chapter**.

1. Upload a chapter (PDF, Word, TXT, or photos of pages) or paste text
2. The app creates board-style MCQs, short and long questions from that chapter only
3. Students answer; answers are checked against the chapter
4. Feedback, model answers and explanations in **English, اردو or Roman Urdu**

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
mkdir -p .streamlit && cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit secrets.toml and add your Anthropic API key
streamlit run app.py
```

## Put it on GitHub

```bash
git init
git add .
git commit -m "Imtihan Tayyari: first version"
git branch -M main
git remote add origin https://github.com/<your-username>/imtihan-tayyari.git
git push -u origin main
```

`.gitignore` already keeps your `secrets.toml` out of GitHub.

## Deploy free on Streamlit Community Cloud

1. Go to share.streamlit.io, sign in with GitHub, click **New app**
2. Pick this repo, branch `main`, main file `app.py`
3. Open **Advanced settings → Secrets** and paste:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   APP_PASSWORD = "choose-a-password"   # optional
   ```
4. Deploy. Share the link with students.

## Notes

- **Cost:** every student action calls the Claude API, which you pay for. Set a monthly spend limit in the Anthropic Console, and use `APP_PASSWORD` while testing.
- **Model:** defaults to `claude-sonnet-5-5`. Override with the `CLAUDE_MODEL` environment variable (a Haiku model is cheaper).
- **Scanned PDFs:** if a PDF has no selectable text, upload photos of the pages instead (up to 10); the app reads them with Claude vision.
- **Long chapters:** the first 60,000 characters are used. Split very long chapters.
- **Accuracy:** MCQs are marked in code; written answers are marked by the AI against the chapter. Always tell students to verify with their teacher.

## Ideas for next steps

- Save scores per student (Supabase or Google Sheets) to show progress over time
- Past-paper mode: upload a past paper and match questions to chapters
- Voice answers and read-aloud explanations for Urdu
- Download practice sets as PDF
