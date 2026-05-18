"""
main.py
SimplifIQ Lead Automation — FastAPI Backend
Orchestrates the full workflow: form → enrich → report → email → log → archive
"""

import os
import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, validator
from dotenv import load_dotenv

from enrichment import enrich_company, build_context_summary
from report_generator import generate_full_report
from email_sender import send_report_email
from google_services import log_lead_to_sheets, upload_pdf_to_drive, setup_sheet_headers

# ── Setup ──────────────────────────────────────────────────────────────────────
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SimplifIQ Lead Automation API",
    description="Automates lead intake → research → report → email workflow",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (if any)
os.makedirs("generated_pdfs", exist_ok=True)
os.makedirs("templates", exist_ok=True)


# ── Schema ─────────────────────────────────────────────────────────────────────
class LeadSubmission(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    company_name: str
    website: str
    industry: str
    company_size: str = ""
    challenge: str = ""
    source: str = ""

    @validator("first_name", "last_name", "company_name", "website", "industry")
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("This field is required")
        return v.strip()

    @validator("email")
    def valid_email(cls, v):
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email address")
        return v.strip().lower()

    @validator("website")
    def valid_website(cls, v):
        v = v.strip()
        if not v.startswith("http"):
            v = "https://" + v
        return v


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_form():
    """Serve the lead intake form."""
    try:
        with open("templates/form.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Form not found</h1>", status_code=404)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "SimplifIQ Lead Automation",
        "version": "1.0.0"
    }


@app.post("/submit")
async def submit_lead(lead: LeadSubmission, background_tasks: BackgroundTasks):
    """
    Main endpoint: receives lead form submission and kicks off the full automation.
    Returns immediately, runs the workflow in the background.
    """
    logger.info(f"New lead received: {lead.first_name} {lead.last_name} — {lead.company_name}")

    lead_data = lead.dict()

    # Run full workflow in background (non-blocking)
    background_tasks.add_task(run_full_workflow, lead_data)

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": f"Thank you {lead.first_name}! Your personalized audit report for {lead.company_name} is being generated and will be emailed to {lead.email} shortly.",
        }
    )


async def run_full_workflow(lead_data: dict):
    """
    Full automation pipeline:
    1. Enrich company data (scraping)
    2. Generate AI report content
    3. Create PDF
    4. Send email
    5. Log to Google Sheets
    6. Archive PDF to Google Drive
    """
    company = lead_data.get("company_name", "Unknown")
    email = lead_data.get("email", "")
    report_status = "Failed"
    pdf_path = None

    try:
        # ── Step 1: Enrich ───────────────────────────────────────────────────
        logger.info(f"[{company}] Step 1: Enriching company data...")
        enriched = await asyncio.get_event_loop().run_in_executor(
            None, enrich_company, lead_data
        )
        context_summary = build_context_summary(enriched)
        logger.info(f"[{company}] Enrichment complete.")

        # ── Step 2 & 3: Generate AI content + PDF ───────────────────────────
        logger.info(f"[{company}] Step 2-3: Generating AI report and PDF...")
        pdf_path = await asyncio.get_event_loop().run_in_executor(
            None, generate_full_report, lead_data, context_summary, "generated_pdfs"
        )
        logger.info(f"[{company}] PDF generated: {pdf_path}")

        # ── Step 4: Send Email ───────────────────────────────────────────────
        logger.info(f"[{company}] Step 4: Sending email to {email}...")
        email_sent = await asyncio.get_event_loop().run_in_executor(
            None, send_report_email, lead_data, pdf_path
        )

        if email_sent:
            logger.info(f"[{company}] Email sent successfully.")
            report_status = "Success"
        else:
            logger.warning(f"[{company}] Email failed.")
            report_status = "Email Failed"

        # ── Step 5: Google Sheets Logging ────────────────────────────────────
        logger.info(f"[{company}] Step 5: Logging to Google Sheets...")
        sheets_ok = await asyncio.get_event_loop().run_in_executor(
            None, log_lead_to_sheets, lead_data, report_status
        )
        if sheets_ok:
            logger.info(f"[{company}] Logged to Sheets.")
        else:
            logger.warning(f"[{company}] Sheets logging failed (non-critical).")

        # ── Step 6: Google Drive Archive ─────────────────────────────────────
        if pdf_path:
            logger.info(f"[{company}] Step 6: Uploading PDF to Drive...")
            drive_link = await asyncio.get_event_loop().run_in_executor(
                None, upload_pdf_to_drive, pdf_path, company
            )
            if drive_link:
                logger.info(f"[{company}] PDF archived to Drive: {drive_link}")
            else:
                logger.warning(f"[{company}] Drive upload failed (non-critical).")

        logger.info(f"[{company}] ✅ Full workflow complete!")

    except Exception as e:
        logger.error(f"[{company}] ❌ Workflow error: {e}", exc_info=True)
        # Still log to sheets even on failure
        try:
            log_lead_to_sheets(lead_data, "Error")
        except Exception:
            pass


# ── Startup ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """On startup: initialize Google Sheets headers."""
    logger.info("SimplifIQ Lead Automation starting up...")
    try:
        await asyncio.get_event_loop().run_in_executor(None, setup_sheet_headers)
        logger.info("Google Sheets initialized.")
    except Exception as e:
        logger.warning(f"Could not initialize Sheets (non-critical): {e}")
    logger.info("🚀 Server ready at http://localhost:8000")


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 8000)),
        reload=True,
        log_level="info"
    )