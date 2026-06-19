# BioQuestion

Biomedical literature learning workflow: **extract knowledge points → generate quiz → grade answers**.

Uses Google Gemini API with a Streamlit web UI and CLI.

## Features

- Upload **TXT** or **PDF** (with OCR for scanned pages)
- Extract entities, mechanisms, and findings with source quotes
- Generate 3 multi-select + 2 short-answer questions
- AI grading with detailed feedback

## Setup

```bash
cd BIOQUESTION
python -m pip install -r requirements.txt
python -m pip install -e .
copy .env.example .env   # Windows
# Edit .env and set GOOGLE_API_KEY
```

## Web UI (recommended)

```bash
python -m streamlit run app.py
```

Open http://localhost:8502

Or double-click `start.bat` on Windows.

## CLI

```bash
python main.py extract -i examples/literature_sample.txt -o output/knowledge.json
python main.py quiz -k output/knowledge.json -o output/quiz.json
python main.py grade -q output/quiz.json -I -o output/grading.json
python main.py pipeline -i examples/literature_sample.txt -d output
```

## Project structure

```
BIOQUESTION/
├── app.py              # Streamlit entry
├── main.py             # CLI entry
├── bioquestion/        # Python package
├── examples/
└── .streamlit/         # Port 8502
```

## Security

Never commit `.env`. Use `.env.example` as a template only.

## License

MIT
