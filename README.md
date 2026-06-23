# Faculty Resume Parser & Evaluation System

Run locally with Streamlit:

```bash
pip install -r requirements.txt
streamlit run main.py
```

Usage:
- Set `Select Resume Folder` to the folder containing resumes (PDF/DOCX/DOC).
- Set `Select Output Folder` for the generated excel files.
- Click `Process Resumes`.

Notes:
- PaddleOCR and sentence-transformers models may need to download model data on first run.
- Ollama/qwen integration is optional and not implemented automatically; enable the checkbox only if you have a local Ollama server and model available.
