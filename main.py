from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import anthropic
import json
import os
import httpx
import re
from datetime import datetime
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors
from database import init_db, save_inquiry, get_all_inquiries, get_stats

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

init_db()

# ── Utility: clean JSON from Claude ─────────────────────────────────────────
def clean_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()

# ── Utility: Tavily web search ───────────────────────────────────────────────
async def web_search(query: str):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "max_results": 3,
                    "search_depth": "basic"
                },
                timeout=10.0
            )
            data = res.json()
            results = data.get("results", [])
            return " ".join([r.get("content", "")[:300] for r in results[:3]])
    except:
        return "No additional research data available."

# ── Utility: Send Slack notification ────────────────────────────────────────
async def send_slack(message: dict):
    if not SLACK_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(SLACK_WEBHOOK_URL, json=message, timeout=5.0)
    except:
        pass

# ── Utility: Generate PDF proposal ──────────────────────────────────────────
def generate_pdf(data: dict, filename: str):
    filepath = f"static/{filename}"
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                  fontSize=20, textColor=colors.HexColor('#1a1a2e'),
                                  spaceAfter=12)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'],
                                    fontSize=13, textColor=colors.HexColor('#667eea'),
                                    spaceAfter=8, spaceBefore=16)
    body_style = ParagraphStyle('Body', parent=styles['Normal'],
                                 fontSize=10, leading=16, spaceAfter=8)
    story = []
    story.append(Paragraph("AI-Generated Business Proposal", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}", body_style))
    story.append(Spacer(1, 0.3*inch))

    sections = [
        ("Inquiry Classification", f"Category: {data.get('category','')}\nPriority: {data.get('priority','')}\nLanguage: {data.get('language','')}"),
        ("Executive Summary", data.get('summary', '')),
        ("Market Research", data.get('research', '')),
        ("Proposed Response", data.get('suggested_reply', '')),
        ("Recommended Actions", "\n".join(f"• {a}" for a in data.get('actions', []))),
    ]
    for heading, content in sections:
        story.append(Paragraph(heading, heading_style))
        for line in content.split('\n'):
            if line.strip():
                story.append(Paragraph(line.strip(), body_style))
        story.append(Spacer(1, 0.1*inch))

    doc.build(story)
    return filepath

# ═══════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE — 4 Agents in sequence
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/pipeline")
async def run_pipeline(request: Request):
    data = await request.json()
    text = data.get("text", "")
    pipeline_log = []

    # ── AGENT 1: Classifier ──────────────────────────────────────────────────
    pipeline_log.append({"agent": "Classifier", "status": "running"})
    msg1 = claude.messages.create(
        model="claude-opus-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": f"""You are an AI classifier for a global travel representation company.
Analyze this inquiry and return ONLY valid JSON:
{{
  "category": "one of: Airline Inquiry, Hotel & Accommodation, Tourism Marketing, PR & Media, Finance & Operations, General",
  "priority": "one of: High, Medium, Low",
  "language": "detected language name",
  "sentiment": "one of: Positive, Neutral, Negative",
  "summary": "one sentence summary",
  "client_name": "extract company or person name if mentioned, else Unknown",
  "department": "one of: Sales, Marketing, Finance, PR, Operations"
}}
Return ONLY JSON. No markdown. No backticks.
Inquiry: {text}"""}]
    )
    classification = json.loads(clean_json(msg1.content[0].text))
    pipeline_log[-1]["status"] = "done"
    pipeline_log[-1]["output"] = classification

    # ── AGENT 2: Researcher ──────────────────────────────────────────────────
    pipeline_log.append({"agent": "Researcher", "status": "running"})
    client_name = classification.get("client_name", "")
    category = classification.get("category", "")
    search_query = f"{client_name} {category} travel industry 2024" if client_name != "Unknown" else f"{category} travel industry trends 2024"
    research_data = await web_search(search_query)
    pipeline_log[-1]["status"] = "done"
    pipeline_log[-1]["output"] = {"research_summary": research_data[:200] + "..."}

    # ── AGENT 3: Response Writer ─────────────────────────────────────────────
    pipeline_log.append({"agent": "Response Writer", "status": "running"})
    language = classification.get("language", "English")
    msg3 = claude.messages.create(
        model="claude-opus-4-6",
        max_tokens=1200,
        messages=[{"role": "user", "content": f"""You are a senior business development manager at a global travel representation company.
Write a personalized, professional response to this inquiry using the research context provided.
Return ONLY valid JSON:
{{
  "suggested_reply": "personalized professional reply in {language}, use \\n for line breaks between paragraphs",
  "key_points": ["point 1", "point 2", "point 3"],
  "actions": ["action 1", "action 2", "action 3"],
  "time_saved_minutes": 15
}}
Return ONLY JSON. No markdown. No backticks.

Original Inquiry: {text}
Classification: {json.dumps(classification)}
Research Context: {research_data[:500]}"""}]
    )
    response_data = json.loads(clean_json(msg3.content[0].text))
    pipeline_log[-1]["status"] = "done"
    pipeline_log[-1]["output"] = {"key_points": response_data.get("key_points", [])}

    # ── AGENT 4: Action Router ───────────────────────────────────────────────
    pipeline_log.append({"agent": "Action Router", "status": "running"})

    # Merge all data
    full_data = {**classification, **response_data, "research": research_data[:300]}

    # Send Slack notification
    priority = classification.get("priority", "Medium")
    priority_emoji = "🔴" if priority == "High" else "🟡" if priority == "Medium" else "🟢"
    await send_slack({
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": f"🔔 New {category} — {priority_emoji} {priority} Priority"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Category:*\n{category}"},
                {"type": "mrkdwn", "text": f"*Language:*\n{language}"},
                {"type": "mrkdwn", "text": f"*Client:*\n{client_name}"},
                {"type": "mrkdwn", "text": f"*Department:*\n{classification.get('department','')}"}
            ]},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Summary:*\n{classification.get('summary','')}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*AI Suggested Reply Preview:*\n_{response_data.get('suggested_reply','')[:200]}..._"}},
            {"type": "divider"},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"⏱ {response_data.get('time_saved_minutes', 15)} minutes saved by AI automation"}]}
        ]
    })

    # Generate PDF
    pdf_filename = f"proposal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    generate_pdf(full_data, pdf_filename)

    pipeline_log[-1]["status"] = "done"
    pipeline_log[-1]["output"] = {"slack": "sent", "pdf": pdf_filename}

    # Save to database
    save_inquiry(
        agent_type="Full Pipeline",
        input_text=text,
        category=category,
        language=language,
        priority=priority,
        summary=classification.get("summary", ""),
        output=response_data.get("suggested_reply", "")[:500]
    )

    return {
        "pipeline_log": pipeline_log,
        "classification": classification,
        "research_preview": research_data[:300],
        "response": response_data,
        "pdf_url": f"/static/{pdf_filename}",
        "slack_sent": True
    }


# ── Keep existing agents for backwards compatibility ─────────────────────────

@app.post("/api/inquiry")
async def process_inquiry(request: Request):
    data = await request.json()
    text = data.get("text", "")
    msg = claude.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"""Analyze this inquiry for a global travel company. Return ONLY valid JSON:
{{
  "category": "one of: Airline Inquiry, Hotel & Accommodation, Tourism Marketing, PR & Media, Finance & Operations, General",
  "language": "language name",
  "priority": "one of: High, Medium, Low",
  "summary": "one sentence summary",
  "suggested_reply": "professional reply in same language, use \\n for line breaks",
  "time_saved_minutes": 8
}}
Return ONLY JSON. No markdown. No backticks.
Inquiry: {text}"""}]
    )
    result = json.loads(clean_json(msg.content[0].text))
    save_inquiry("Inquiry Router", text, result.get("category","General"),
                 result.get("language","English"), result.get("priority","Low"),
                 result.get("summary",""), result.get("suggested_reply",""))
    return result

@app.post("/api/marketing")
async def generate_marketing(request: Request):
    data = await request.json()
    destination = data.get("destination","")
    target_market = data.get("target_market","")
    language = data.get("language","English")
    msg = claude.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"""Generate travel marketing content. Return ONLY valid JSON:
{{
  "linkedin_post": "professional LinkedIn post max 150 words",
  "instagram_caption": "Instagram caption with hashtags max 80 words",
  "email_subject": "compelling subject line",
  "email_body": "marketing email body max 100 words",
  "press_release_intro": "press release opening paragraph max 80 words"
}}
All content in {language}. Return ONLY JSON. No markdown. No backticks.
Destination: {destination}, Target Market: {target_market}"""}]
    )
    result = json.loads(clean_json(msg.content[0].text))
    save_inquiry("Marketing Generator", f"{destination}→{target_market}",
                 "Tourism Marketing", language, "Medium",
                 f"Marketing content for {destination}", result.get("linkedin_post",""))
    return result

@app.post("/api/report")
async def summarize_report(request: Request):
    data = await request.json()
    report_text = data.get("text","")
    msg = claude.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"""Analyze this business report. Return ONLY valid JSON:
{{
  "key_insights": ["insight 1", "insight 2", "insight 3"],
  "risks": ["risk 1", "risk 2"],
  "recommended_actions": ["action 1", "action 2", "action 3"],
  "executive_summary": "2-3 sentence summary for senior management",
  "sentiment": "one of: Positive, Neutral, Negative"
}}
Return ONLY JSON. No markdown. No backticks.
Report: {report_text}"""}]
    )
    result = json.loads(clean_json(msg.content[0].text))
    save_inquiry("Report Summarizer", report_text[:200], "Finance & Operations",
                 "English", "High", result.get("executive_summary",""),
                 str(result.get("key_insights",[])))
    return result

# ── Dashboard & Stats ─────────────────────────────────────────────────────────
@app.get("/api/stats")
async def get_dashboard_stats():
    return get_stats()

@app.get("/api/history")
async def get_history():
    rows = get_all_inquiries()
    return [{"id":r[0],"timestamp":r[1],"agent_type":r[2],"input_text":r[3][:100],
             "category":r[4],"language":r[5],"priority":r[6],"summary":r[7],"output":r[8][:150]}
            for r in rows]

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "index.html")