# InternShield 🛡️

**Protecting Students from Fake Internship Offers**

InternShield is a free, AI-powered tool that helps students verify the authenticity of internship and job offer letters. Upload or paste any offer letter and get an instant analysis with confidence score, red flags, and actionable next steps.

> **🚨 Every year, thousands of students in India fall victim to fake internship offers.** Scammers demand registration fees, collect sensitive documents, and waste students' time with non-existent positions. InternShield was built to fight back.

---

## ✨ Features

- **Multi-format input** — Analyze PDFs, images (JPG/PNG), DOCX, TXT, or paste text directly
- **8-point rule engine** — Checks for suspicious email domains, fake company names, urgency tactics, implausible stipends, missing fields, and more
- **NLP language analysis** — Detects fraud indicators and genuine offer patterns using keyword-weighted classification
- **Entity verification** — Extracts and verifies company names, people, dates, and contacts using spaCy NER
- **Enriched analysis** — Optionally provide company name, website, and email for deeper verification
- **Education section** — Learn how to spot fake offers with a detailed fake vs. genuine comparison
- **Privacy first** — No signup required, no data stored permanently, fully anonymous
- **Session history** — Track your past scans within the browser session

---

## 🏗️ Architecture

```
┌─────────────────────────┐     ┌─────────────────────────┐     ┌──────────────┐
│   Next.js 16 Frontend   │────▶│    FastAPI Backend       │────▶│   Supabase   │
│   (React 19, TypeScript)│◀────│    (Python 3.9+)        │◀────│  (Optional)  │
└─────────────────────────┘     └─────────────────────────┘     └──────────────┘
                                          │
                                ┌─────────┼─────────┐
                                ▼         ▼         ▼
                          Rule Engine    NLP     NER/spaCy
                          (8 rules)   (Keyword   (Entity
                           30%       Analysis)  Extraction)
                                      50%        20%
```

### ML Pipeline

| Component | Purpose | Weight |
|-----------|---------|--------|
| **Rule Engine** | 8 deterministic structural checks (email domain, stipend, fake companies, missing fields, dates, grammar, urgency, greeting) | 30% |
| **NLP Classifier** | Keyword-weighted language pattern analysis (genuine vs fraud indicators) | 50% |
| **NER Extractor** | Named entity extraction & verification using spaCy (companies, people, dates, contacts) | 20% |

### Scoring

| Score | Verdict |
|-------|---------|
| 75–100% | ✅ Likely Genuine |
| 45–74% | ⚠️ Suspicious |
| 0–44% | 🚨 Likely Fake |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** with pip
- **Node.js 18+** with npm

### 1. Clone the Repository

```bash
git clone https://github.com/Aadityavarier/internshield.git
cd internshield
```

### 2. Start the Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
# source venv/bin/activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Copy and fill env variables (optional — works without Supabase)
copy .env.example .env

# Run the server
uvicorn main:app --reload --port 8000
```

The backend will start at `http://localhost:8000`.

### 3. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will start at `http://localhost:3000`.

### 4. Open the App

Navigate to [http://localhost:3000](http://localhost:3000) and start verifying offer letters!

---

## 📁 Project Structure

```
internshield/
├── backend/
│   ├── main.py                    # FastAPI app, CORS, router mounting
│   ├── requirements.txt           # Python dependencies
│   ├── .env.example               # Environment variables template
│   ├── data/
│   │   ├── known_fake_companies.json
│   │   └── suspicious_domains.json
│   ├── models/
│   │   └── schemas.py             # Pydantic request/response models
│   ├── routers/
│   │   └── analyze.py             # API endpoints (/analyze, /result, /history)
│   └── services/
│       ├── text_extractor.py      # PDF, image, DOCX, TXT extraction
│       ├── rule_engine.py         # 8 rule-based fraud checks
│       ├── nlp_classifier.py      # Keyword-weighted NLP classification
│       ├── ner_extractor.py       # spaCy NER + regex fallback
│       └── scorer.py              # Weighted ensemble scoring
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   └── src/
│       ├── app/
│       │   ├── layout.tsx         # Root layout (Navbar + Footer)
│       │   ├── globals.css        # Design system (dark mode, glassmorphism)
│       │   ├── page.tsx           # Homepage (hero, upload, education, about)
│       │   ├── page.module.css    # Homepage styles
│       │   ├── history/           # Scan history page
│       │   └── result/[id]/       # Analysis result page
│       ├── components/
│       │   ├── Navbar.tsx         # Navigation bar
│       │   └── Footer.tsx         # Footer with links & disclaimer
│       └── lib/
│           └── api.ts             # API client + session caching
└── README.md
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/analyze` | Analyze an offer letter (file or text + optional company details) |
| `GET` | `/api/result/{scan_id}` | Get full analysis result for a scan |
| `GET` | `/api/history/{session_id}` | Get scan history for a browser session |
| `GET` | `/api/health` | Health check |

### POST /api/analyze

**Form Data:**
- `file` (optional) — PDF, DOCX, image, or TXT file
- `text` (optional) — Plain text of the offer letter
- `session_id` (required) — Browser session identifier
- `company_name_input` (optional) — Company name from the letter
- `company_website` (optional) — Company website URL
- `contact_email` (optional) — Contact email from the letter

---

## 💾 Database (Optional)

InternShield works fully without a database — results are cached in-memory on the server and in `sessionStorage` on the client. For persistent storage:

1. Create a project at [supabase.com](https://supabase.com)
2. Run this SQL in the SQL editor:

```sql
CREATE TABLE scans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT now(),
  input_type TEXT,
  extracted_text TEXT,
  confidence_score NUMERIC,
  verdict TEXT,
  dimension_scores JSONB,
  triggered_flags JSONB,
  next_steps JSONB,
  company_name TEXT,
  session_id TEXT,
  file_hash TEXT,
  extraction_method TEXT,
  processing_time_ms INT,
  model_version TEXT DEFAULT 'v1.0'
);

CREATE INDEX idx_scans_session_id ON scans(session_id);
CREATE INDEX idx_scans_file_hash ON scans(file_hash);
```

3. Add your credentials to `backend/.env`:
```
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 16, React 19, TypeScript, CSS Modules |
| **Backend** | FastAPI, Python 3.9+, Pydantic v2 |
| **ML/NLP** | spaCy, regex-based NLP, textstat, rapidfuzz |
| **OCR** | Tesseract (optional), pdfplumber, python-docx, Pillow |
| **Database** | Supabase/PostgreSQL (optional — works without it) |
| **Design** | Dark mode, glassmorphism, Inter font, micro-animations |

---

## 📄 License

This project is open source and available for educational and non-commercial use.

---

## ⚠️ Disclaimer

InternShield provides automated analysis and should **not** be treated as legal advice. Always independently verify offers through official channels. If you suspect fraud, report it at [cybercrime.gov.in](https://cybercrime.gov.in).
