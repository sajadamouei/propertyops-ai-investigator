import type { ExperimentScenario } from '../types'

export const demoScenarios = {
  fault: {
    name: 'Heating Valve Fault',
    description: 'A known heating fault is injected. Expect detection → investigation → assessment → human approval.',
  },
  normal: {
    name: 'Normal Operation',
    description: 'The baseline has no injected fault. An incident or work order is generally unexpected.',
  },
  custom: {
    name: 'Custom Fault',
    description: 'Choose a sensor and fault configuration, then see how detection and investigation respond.',
  },
} satisfies Record<ExperimentScenario, { name: string; description: string }>

export const recommendedRun = {
  scenario: 'fault',
  name: demoScenarios.fault.name,
  days: 14,
  seed: 42,
  action: 'Run full pipeline',
} as const

export const telemetryStage = {
  title: 'Synthetic telemetry',
  detail: 'Python generates HVAC sensor readings.',
}

export const investigationWorkflow = [
  {
    action: 'Detect anomalies',
    label: 'Detect',
    title: 'Anomaly detection',
    detail: 'Feature engineering and Isolation Forest analyze synthetic HVAC telemetry for unusual patterns.',
  },
  {
    action: 'Gather evidence',
    label: 'Investigate',
    title: 'AI investigation',
    detail: 'Gemini gathers sensor data, maintenance history, and tenant complaints through MCP tools.',
  },
  {
    action: 'Retrieve technical guidance',
    label: 'Ground',
    title: 'Technical grounding',
    detail: 'FAISS-based RAG retrieves relevant troubleshooting guidance.',
  },
  {
    action: 'Assess the issue',
    label: 'Assess',
    title: 'Assessment',
    detail: 'The evidence and guidance support a likely cause, confidence level, and recommended action.',
  },
  {
    action: 'Human decision',
    label: 'Decide',
    title: 'Human approval',
    detail: 'The workflow pauses for you to approve or reject the proposed demo work order.',
  },
]

export const engineeringChallenges = [
  {
    title: 'Fragmented operational context',
    detail: 'Connect evidence from separate building and maintenance systems.',
  },
  {
    title: 'Grounded AI reasoning',
    detail: 'Support the assessment with operational evidence and technical guidance.',
  },
  {
    title: 'Human-in-the-loop actions',
    detail: 'Require approval before an AI recommendation can change operational records.',
  },
  {
    title: 'Recoverable workflows',
    detail: 'Persist workflow state with LangGraph so an investigation can pause and resume safely.',
  },
  {
    title: 'End-to-end AI application engineering',
    detail: 'Connect ML, agents, and RAG to APIs, the frontend, tests, containers, CI/CD, and cloud deployment.',
  },
]

export const technologyGroups = [
  { title: 'AI / ML', items: ['Isolation Forest', 'Gemini', 'LangGraph', 'MCP', 'FAISS'] },
  { title: 'Application', items: ['FastAPI', 'React', 'TypeScript'] },
  { title: 'Engineering / Deployment', items: ['Docker', 'GitHub Actions', 'Azure Container Apps'] },
]

export const simulationSources = [
  {
    title: 'Synthetic telemetry',
    detail: 'Occupancy schedules and seeded randomness drive sensor readings. Scenarios can inject stuck values, offsets, spikes, multipliers, or missing readings.',
  },
  {
    title: 'Operational systems',
    detail: 'Demo equipment, sensor, maintenance, and tenant-complaint records stand in for separate property systems. Model Context Protocol (MCP) tools let the agent access those records.',
  },
  {
    title: 'Technical guidance',
    detail: 'Retrieval-augmented generation (RAG) finds relevant troubleshooting documents written for the demo and uses them to support likely causes and recommended actions.',
  },
]

export const projectLinks = [
  { label: 'View GitHub', href: 'https://github.com/sajadamouei/propertyops-ai-investigator' },
  { label: 'Project presentation', href: 'https://propertyops-ai-presentation.sajad-amouei.workers.dev/' },
]
