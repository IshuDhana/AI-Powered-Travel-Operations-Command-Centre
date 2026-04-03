# AI Command Centre 🤖
### AI-Powered Travel Operations Intelligence Platform

A production-ready, end-to-end AI automation platform built to demonstrate 
how AI can transform global travel operations — from intelligent inquiry 
routing to personalised response generation, team notifications, and 
management reporting.

---

## Live Demo
🔗 [View Live App](YOUR_RAILWAY_URL_HERE ON REQUEST ONLY) 
📹 [Watch Demo Video](https://drive.google.com/file/d/1cHSR4dGBJCdDx1CHPobOUBLW4S7FMg7S/view?usp=sharing)

---

## What It Does

A 4-agent AI pipeline that processes client inquiries automatically:

| Agent | Role |
|---|---|
| Agent 1 — Classifier | Detects category, language, priority, sentiment |
| Agent 2 — Researcher | Web searches the client and market context |
| Agent 3 — Response Writer | Generates personalised reply using research |
| Agent 4 — Action Router | Sends Slack alert, generates PDF, logs to database |

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Brain | Claude Opus (Anthropic) |
| Web Research | Tavily API |
| Backend | Python + FastAPI |
| Database | PostgreSQL (Railway) |
| Low-code Automation | Zapier |
| Team Notifications | Slack Webhooks |
| PDF Generation | ReportLab |
| Deployment | Railway |
| Frontend | Tailwind CSS + Vanilla JS |

---

## Features

- ⚡ Full 4-agent AI pipeline
- 🔍 Real-time web research per inquiry
- 🌍 7 language support
- 📄 Auto-generated PDF proposals
- 💬 Slack team routing
- 📊 Live analytics dashboard
- 💰 ROI tracker (time + cost saved)
- 🗺️ System architecture documentation

---

## System Architecture

**System 1 — Zapier Automation (Low-code layer)**
```
Gmail → AI by Zapier → Slack → Google Sheets
```
Runs 24/7 automatically on every incoming email.

**System 2 — AI Command Centre (This app)**
```
Input → Agent 1 → Agent 2 → Agent 3 → Agent 4 → Output
```
Live web platform for manual pipeline execution with full analytics.

---

## Local Setup
```bash
git clone https://github.com/IshuDhana/ai-command-centre.git
cd ai-command-centre
pip install -r requirements.txt
```

Create `.env` file:
```
ANTHROPIC_API_KEY=your_key
TAVILY_API_KEY=your_key
SLACK_WEBHOOK_URL=your_webhook
```

Run:
```bash
uvicorn main:app --reload
```

Open: `http://127.0.0.1:8000`

---

## Built By

**Iswarya Malayamaan** — AI Engineer  
📍 Germany 🇩🇪  
🔗 [LinkedIn](https://linkedin.com/in/iswarya-malayamaan-13362a125)  
🐙 [GitHub](https://github.com/IshuDhana)  
🌐 [Portfolio](https://ishudhana.github.io/)  
📧 iswarya.abinayam@gmail.com
