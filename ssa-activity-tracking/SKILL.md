---
name: ssa-activity-tracking
description: Track SA activities in Salesforce (AWSentral) and create SIFT entries using kiro-cli with ai-ml-ssa agent. Covers logging customer meetings, demos, POCs, architecture reviews, and generating weekly SIFT insights.
version: 1.0.0
tags: [salesforce, sift, activity, tracking, kiro, awsentral]
---

# SSA Activity Tracking

## Overview
Automated workflow for logging Specialist SA customer activities in Salesforce (AWSentral) and creating SIFT (Sales Inputs & Field Trends) entries using `kiro-cli` with the `ai-ml-ssa` agent.

## Goals (FY2026)
- **240** 1:Customer activities (50% should be POC, Demo, Immersion Day)
- **40** SIFT entries (Bedrock CLF, SageMaker CLF, AgentCore CLF; PFR, customer reference also count)
- **5** Scale Activities
- **120** TFC points

## Tool: kiro-cli with ai-ml-ssa agent

### Non-interactive mode (preferred for automation)
```bash
kiro-cli chat --agent ai-ml-ssa --no-interactive -a "YOUR_PROMPT_HERE"
```

### Interactive mode
```bash
kiro-cli chat --agent ai-ml-ssa
```

### Key flags
- `--no-interactive`: Run without expecting user input (for automation)
- `-a` / `--trust-all-tools`: Allow all tool calls without confirmation
- `--model MODEL`: Override model (default: claude-opus-4.5)

### MCP Servers used
- `aws-sentral-mcp`: Salesforce CRUD (create_tech_activity, search_opportunities, search_accounts, etc.)
- `builder-mcp`: Skills engine (salesforce-activity-logging, salesforce-sift skills)
- `awslabs.aws-documentation-mcp-server`: AWS docs search
- `bedrock-agentcore-mcp-server`: AgentCore docs

## Salesforce Activity Logging

### Activity Types (SA Activity field)
| Activity Type | When to Use |
|---|---|
| `Architecture Review [Architecture]` | Architecture discussions, technical deep dives |
| `Demo [Architecture]` | Product demos, live demonstrations |
| `Prototype/PoC/Pilot [Architecture]` | POC scoping, execution, reviews |
| `Immersion Day [Workshops]` | Immersion days delivered |
| `Other Workshops [Workshops]` | Workshops, EBAs, hands-on sessions |
| `EBC Support - own accounts [Management]` | Executive Briefing Center support |
| `Meeting/ Office Hours [Management]` | General meetings, office hours |
| `Cost Optimization [Cost]` | Cost optimization discussions |
| `Well Architected [Architecture]` | WAR reviews |

### Priority: 50% should be POC/Demo/Immersion Day
Map activities to maximize POC/Demo tracking:
- Discovery calls with technical content -> `Architecture Review [Architecture]`
- Calls where you showed something -> `Demo [Architecture]`
- POC proposals, POC reviews, POC execution -> `Prototype/PoC/Pilot [Architecture]`
- EBC with demo -> `EBC Support - own accounts [Management]` + note demo in description
- Workshops/EBAs -> `Immersion Day [Workshops]` or `Other Workshops [Workshops]`

### Required Fields
- `parentRecord`: Opportunity ID (006...) - MUST be linked to opportunity
- `subject`: "[Date] Customer - Topic" format
- `description`: Attendees, discussion, insights, next steps
- `activityDate`: YYYY-MM-DD
- `status`: "Completed"
- `isVirtual`: true for remote
- `saActivity`: Activity type from table above
- `awsServices`: Array of AWS services discussed
- `domains`: e.g., ["Generative AI"], ["Machine Learning"]
- `goals`: e.g., ["Technical Guidance"], ["Proof of Concept"]

### Workflow
1. Read engagement notes from `~/Library/CloudStorage/OneDrive-SharedLibraries-amazon.com/sanghwa - Documents/2026 Engagements - Sanghwa/`
2. Also available in Quip: `https://quip-amazon.com/ceAIOzQL8qaf/2026-Engagements-Sanghwa`
3. Categorize activity type (prioritize POC/Demo)
4. Search for opportunity: `search_opportunities` with customer name
5. If no opportunity found, search account: `search_accounts`
6. Create activity: `create_tech_activity`

### Batch Prompt Template for kiro-cli
```
Log the following customer activity in Salesforce:
- Customer: [NAME]
- Date: [YYYY-MM-DD]
- Subject: [SUBJECT]
- Activity Type: [TYPE]
- AWS Services: [SERVICES]
- Description:
  Attendees: [LIST]
  Discussion: [SUMMARY]
  Next Steps: [ACTIONS]
  
First search for the opportunity for [CUSTOMER], then create the tech activity.
```

## SIFT Entry Creation

### Frequency
- **Minimum 1 per week** (40 total target)
- Focus on AgentCore, Bedrock, SageMaker product feedback
- PFR and customer references also count

### SIFT Types
| Type | When |
|---|---|
| Observation | Trends, patterns across customers |
| Highlight | Customer wins, successful outcomes |
| Risk | Potential problems without data yet |
| Challenge | Problems you can solve without leadership |
| Blocker | Need leadership help |
| Lowlight | Where AWS missed the mark |

### SIFT Prompt Template for kiro-cli
```
Create a SIFT entry in AWSentral:
- Type: Observation
- Template: NAMER CSC TECH
- Related Account: [CUSTOMER]
- Title: [DESCRIPTIVE TITLE with customer name and ARR if known]
- Content:
  Observation: [PATTERN]
  Evidence:
  - Customer 1: [EXAMPLE]
  - Customer 2: [EXAMPLE]
  Impact: [WHY IT MATTERS]
  Recommendation: [WHAT SHOULD BE DONE]
- Tags: csc-tech-[manager-alias]
- AWS Services: [SERVICES]
```

### Good SIFT Topics from Engagements
- **AgentCore**: Observability trace clutter feedback, MCP deployment patterns, custom auth challenges
- **Bedrock**: Model evaluation needs (no ground truth), multi-model routing demand, throughput concerns
- **SageMaker**: HyperPod EKS integration patterns, deployment workflows
- **General**: Customer migration patterns (OpenAI -> Bedrock), MCP server adoption trends

## Engagement Source Files
OneDrive path: `~/Library/CloudStorage/OneDrive-SharedLibraries-amazon.com/sanghwa - Documents/2026 Engagements - Sanghwa/`
Quip folder: `https://quip-amazon.com/ceAIOzQL8qaf/2026-Engagements-Sanghwa`

Files follow `[MM-DD] Customer - Topic.md` naming convention.
Internal-only meetings (tagged [Internal]) still need logging if tied to a customer opportunity.

## Common Mistakes
- Logging to Account instead of Opportunity -> always search for opportunity first
- Generic subjects -> use "[Date] Customer - Specific Topic" format
- Missing AWS services tags -> always include services discussed
- Forgetting to set Virtual=true for remote calls
- Not categorizing as POC/Demo when applicable -> maximize these categories
