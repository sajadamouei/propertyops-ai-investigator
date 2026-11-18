# PropertyOps AI Investigator

**An agentic AI demo for investigating HVAC faults in building operations.**

When a building system behaves unexpectedly, finding the cause often means checking sensor readings, maintenance history, tenant complaints, and technical documents separately. PropertyOps brings that evidence into one investigation and suggests a practical next step—while leaving the final decision to a human operator.

**[Try the live demo](https://ca-propertyops-ai.bravemeadow-1c7ef3e7.northeurope.azurecontainerapps.io/operations)**

## Try it out

1. Open the **Lab** tab and choose **Heating Valve Fault** (the default scenario).
2. Click **Run full pipeline**. The app generates synthetic sensor data, detects the anomaly, investigates the incident, and prepares an AI assessment.
3. Click any pipeline stage to inspect its **inputs, outputs, and visualizations**.
4. Open **Operations** to review the timeline, supporting evidence, and recommended action. **Approve** or **reject** the proposed work order; nothing is created without your approval.
5. Back in **Lab**, try **Normal Operation** (no work order needed) or inject a **Custom Fault**.

## How it works

`Synthetic telemetry → Feature engineering → Isolation Forest → Incident → MCP investigation → RAG → AI assessment → Human approval → Demo work order`

- **Anomaly detection:** Scikit-learn's Isolation Forest identifies unusual HVAC behavior and groups anomalous readings into incidents.
- **Evidence gathering:** An LLM agent uses **Model Context Protocol (MCP)** tools to read sensor data, past work orders, and tenant complaints.
- **Grounded assessment:** **FAISS** and Sentence Transformers retrieve relevant technical guidance. A **Google Gemini** model combines that guidance with operational evidence to suggest a likely issue and next action—not a confirmed diagnosis.
- **Controlled execution:** **LangGraph** manages workflow state, checkpoints, and the human approval step before a work order can be written.

## Engineering challenges

- **Keeping AI conclusions grounded:** Separate observed facts from diagnostic guidance, capture tool-call traces, and return structured assessments.
- **Making agents safe to use:** Keep investigation tools read-only, require explicit approval for write actions, and make work-order creation idempotent.
- **Making the demo repeatable:** Use seeded fault scenarios, recovery checkpoints, automated AI-quality checks, backend tests, and frontend end-to-end tests.

## Tech stack

**AI/ML:** Python, scikit-learn, LangChain, LangGraph, MCP, Google Gemini, FAISS, Sentence Transformers  
**App:** FastAPI, React, TypeScript, Recharts  
**Deployment & testing:** Docker, GitHub Actions (CI/CD), Azure Container Apps, pytest, Playwright

## Run locally

With Docker installed, clone the repository and add a `.env` file at its root containing `GOOGLE_API_KEY=your_key` (needed for the AI investigation and assessment stages). Then run:

```bash
docker compose up --build
```

Open **http://localhost:3000**. The first run may download the embedding model.

> **Note:** This is an independent portfolio project using synthetic building data. Work orders are created in the demo environment only; it does not control real building equipment.
