# ACC Dashboard Multi-Agent System

A Proof of Concept (POC) multi-agent dashboard system that allows users to query construction project data using natural language. The system uses Excel files exported from Autodesk Construction Cloud as the data source.

## Features

- **Natural Language Queries**: Ask questions about your construction data in plain English
- **Multi-Agent Architecture**: Specialized agents for different data domains
  - Data Analyst Agent: Issues, RFIs, Submittals analysis
  - Safety Agent: Incident analysis and risk assessment
  - Schedule Agent: Timeline and delay analysis
  - Cost Agent: Budget and financial analysis
- **Multi-LLM Support**: Works with Anthropic Claude, OpenAI GPT-4, and Google Gemini
- **Dynamic Visualizations**: Auto-generates charts based on query results
- **Drag-and-Drop Dashboard**: Customize your view with Gridstack.js

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                            │
│  "Show me overdue RFIs by contractor"                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR AGENT                           │
│  Intent Classification → Agent Routing → Response Synthesis      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │  DATA    │     │  SAFETY  │     │ SCHEDULE │
    │ ANALYST  │     │  AGENT   │     │  AGENT   │
    └──────────┘     └──────────┘     └──────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EXCEL DATA LAYER                            │
│  projects.xlsx │ issues.xlsx │ rfis.xlsx │ safety_incidents.xlsx │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd acc-dashboard-poc
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API key
# For Anthropic: ANTHROPIC_API_KEY=sk-ant-...
# For OpenAI: OPENAI_API_KEY=sk-proj-...
# For Google: GEMINI_API_KEY=AIza...
```

### 3. Generate Sample Data

```bash
python scripts/generate_sample_data.py
```

This creates sample Excel files in the `data/` directory:
- `projects.xlsx` - Project master list
- `issues.xlsx` - Issues/defects data
- `rfis.xlsx` - RFI data
- `submittals.xlsx` - Submittal data
- `safety_incidents.xlsx` - Safety incidents
- `schedule.xlsx` - Schedule/tasks data
- `cost.xlsx` - Budget/cost data
- `users.xlsx` - Team members

### 4. Start the Server

```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --reload --port 8000
```

### 5. Open the Dashboard

Navigate to http://localhost:8000 in your browser.

## Sample Queries

Try these natural language queries:

1. **Issues Analysis**
   - "Show me open issues by priority"
   - "Which project has the most critical issues?"
   - "List overdue issues for Tower A"

2. **RFI Analysis**
   - "How many RFIs are overdue?"
   - "Show RFI breakdown by discipline"
   - "Overdue RFIs by contractor"

3. **Safety Analysis**
   - "Safety incidents this month by type"
   - "Show near miss ratio"
   - "Which locations have the most incidents?"

4. **Schedule Analysis**
   - "Show delayed tasks"
   - "What's the schedule status for Tower B?"
   - "List upcoming milestones"

5. **Cost Analysis**
   - "Budget variance by category"
   - "Which projects are over budget?"
   - "Compare budgets across projects"

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/api/query` | POST | Process natural language query |
| `/api/health` | GET | Health check |
| `/api/data/summary` | GET | Get summary of all data tables |
| `/api/data/{table}` | GET | Get data from specific table |
| `/api/data/reload` | POST | Reload all Excel files |
| `/api/data/upload` | POST | Upload new Excel file |
| `/api/projects` | GET | List available projects |
| `/api/agents` | GET | List available agents |

## Project Structure

```
acc-dashboard-poc/
├── main.py                      # FastAPI application
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
│
├── data/                        # Excel data files
│   ├── projects.xlsx
│   ├── issues.xlsx
│   └── ...
│
├── data_layer/                  # Data management
│   ├── excel_loader.py          # Excel file loading
│   ├── query_engine.py          # Query execution
│   ├── data_store.py            # Data storage
│   └── schema.py                # Data validation
│
├── agents/                      # Agent system
│   ├── base_agent.py            # Base agent class
│   ├── orchestrator.py          # Query routing
│   ├── data_analyst_agent.py    # Issues/RFIs analysis
│   ├── safety_agent.py          # Safety analysis
│   ├── schedule_agent.py        # Schedule analysis
│   ├── cost_agent.py            # Cost analysis
│   └── tools/                   # Agent tools
│       ├── data_tools.py
│       ├── aggregation_tools.py
│       └── chart_tools.py
│
├── llm_providers/               # LLM integrations
│   ├── base.py                  # Abstract provider
│   ├── factory.py               # Provider factory
│   ├── claude_provider.py       # Anthropic Claude
│   ├── openai_provider.py       # OpenAI GPT
│   └── gemini_provider.py       # Google Gemini
│
├── frontend/                    # Web UI
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
└── scripts/
    └── generate_sample_data.py  # Sample data generator
```

## Configuration

### LLM Provider Selection

Set `LLM_PROVIDER` in `.env`:
- `anthropic` - Use Claude (recommended)
- `openai` - Use GPT-4
- `google` or `gemini` - Use Gemini

### Custom Models

Override the default model with `LLM_MODEL`:
```env
LLM_MODEL=claude-3-haiku-20240307
```

## Using Your Own Data

1. Export data from ACC (Autodesk Construction Cloud) as Excel files
2. Place the `.xlsx` files in the `data/` directory
3. Ensure column names match the expected schema (see `data_layer/schema.py`)
4. Reload data via the API: `POST /api/data/reload`

## Development

### Running Tests

```bash
pytest tests/
```

### Debug Mode

Enable auto-reload for development:
```env
DEBUG=true
```

## License

MIT License
