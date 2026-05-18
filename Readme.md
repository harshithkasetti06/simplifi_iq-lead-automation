# SimplifIQ — AI Lead Automation System

> Automates the entire lead intake → research → report → email workflow using free tools only.

---

## 🏗️ Architecture

```
Form Submission (form.html)
        ↓
FastAPI Backend (main.py)
        ↓
Web Scraping & Enrichment (enrichment.py)
        ↓
Groq AI Report Generation (report_generator.py)
        ↓
PDF Creation (reportlab)
        ↓
Email Delivery (email_sender.py)
        ↓
Google Sheets Logging + Drive Archiving (google_services.py)
```

---

## 📁 Project Structure

```
simplifiq-lead-automation/
├── main.py                  # FastAPI app + orchestration
├── enrichment.py            # Web scraping + company research
├── report_generator.py      # Groq AI + PDF generation
├── email_sender.py          # Gmail SMTP email delivery
├── google_services.py       # Sheets logging + Drive archiving
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (secrets)
├── credentials.json         # Google service account (add manually)
├── templates/
│   └── form.html            # Lead intake form UI
└── generated_pdfs/          # Auto-created, stores generated PDFs
```

---

## ⚙️ Setup Instructions

### 1. Clone / Create Project

```bash
mkdir simplifiq-lead-automation
cd simplifiq-lead-automation
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```env
# Groq AI (FREE) — https://console.groq.com
GROQ_API_KEY=gsk_your_key_here

# Gmail SMTP (FREE) — Use App Password
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx_xxxx_xxxx_xxxx

# Google Sheets (FREE) — Sheet ID from URL
GOOGLE_SHEET_ID=your_sheet_id_here

# Google Drive (FREE) — Folder ID from URL
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here

# Server
APP_HOST=0.0.0.0
APP_PORT=8000
```

### 4. Add Google Credentials

- Download `credentials.json` from Google Cloud Console
- Place it in the project root directory

### 5. Run the Server

```bash
python main.py
```

Open your browser at: **http://localhost:8000**

---

## 🔑 API Keys Setup (All FREE)

### Groq API (AI — Replaces OpenAI)
1. Visit https://console.groq.com
2. Sign up → API Keys → Create Key
3. Copy `gsk_...` key to `.env`

### Gmail App Password
1. Enable 2-Step Verification at myaccount.google.com
2. Search "App Passwords" → Mail → Other → Generate
3. Copy 16-character password to `.env`

### Google Cloud (Sheets + Drive)
1. Visit https://console.cloud.google.com
2. Create project → Enable Google Sheets API + Drive API
3. Create Service Account → Download JSON as `credentials.json`
4. Share your Google Sheet and Drive folder with the service account email

---

## 🔄 Workflow Explained

| Step | What Happens |
|------|-------------|
| 1 | User submits the form with company details |
| 2 | FastAPI validates and accepts the submission |
| 3 | System scrapes the company website (homepage, about, services) |
| 4 | Groq LLaMA 3 generates a personalized audit report |
| 5 | ReportLab creates a professional dark-themed PDF |
| 6 | Gmail SMTP sends the PDF to the prospect |
| 7 | Lead data is logged to Google Sheets |
| 8 | PDF is archived to Google Drive |

---

## 🧰 Tech Stack

| Component | Tool | Cost |
|-----------|------|------|
| Backend | FastAPI + Python | Free |
| AI | Groq (LLaMA 3 70B) | Free |
| Scraping | BeautifulSoup + requests | Free |
| PDF | ReportLab | Free |
| Email | Gmail SMTP | Free |
| Sheets | Google Sheets API | Free |
| Drive | Google Drive API | Free |

---

## 📌 Assumptions & Tradeoffs

- **Groq over OpenAI**: LLaMA 3 70B via Groq is free and generates high-quality reports
- **BeautifulSoup over Playwright**: Simpler, no browser required; works for most static sites
- **Background tasks**: Email/PDF generation runs async so the form responds immediately
- **Graceful fallbacks**: If scraping fails, the AI still generates a report from form data alone
- **Gmail SMTP**: Simple and free; SendGrid would be more reliable at scale

---

## ⚠️ Known Limitations

- Some websites block scraping (Cloudflare, JS-only sites)
- Groq free tier has rate limits (14,400 req/day — sufficient for this use case)
- Gmail may flag emails as spam without a custom domain
- PDF styling uses ReportLab which has limited CSS support

---

## 🚀 Running in Production

For deployment, consider:
- **Railway / Render** for hosting (free tiers available)
- **Ngrok** for quick public URL during testing: `ngrok http 8000`

---

## 📧 Contact

Built for SimplifIQ Technical Assessment.  
Questions: career@simplifiiq.com