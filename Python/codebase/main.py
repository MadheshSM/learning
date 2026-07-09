"""ACC Dashboard Multi-Agent System - FastAPI Application"""
import os
import re
import logging
from pathlib import Path
from typing import Dict, Optional, List, Union, Any
from contextlib import asynccontextmanager

import httpx
import jwt
import pandas as pd

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from cache import create_cache_from_env, get_cache

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def normalize_user_query(query: str) -> str:
    """Strip whitespace and trailing punctuation so prompts like 'Show RFIs.' and 'Show RFIs' match."""
    if not query:
        return ""
    text = query.strip()
    return re.sub(r"[.!?,;:]+$", "", text)


def resolve_project_id_from_query(
    query_lower: str,
    project_id_name_map: Dict[str, str],
) -> Optional[str]:
    """
    When the UI sends no project_id (All Projects), map a known project name from
    the user's text to a single project_id. Returns None if no name matches or if
    multiple distinct projects match.
    """
    matched_ids: List[str] = []
    for pid, pname in project_id_name_map.items():
        if len(pname) <= 2:
            continue
        if pname.lower() in query_lower:
            matched_ids.append(pid)
    if not matched_ids:
        return None
    unique = set(matched_ids)
    if len(unique) > 1:
        return None
    return matched_ids[0]


# JWT configuration
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET", "")


def verify_bearer_token(http_request: Request) -> dict:
    """Extract and verify JWT bearer token from request headers.
    Returns the decoded payload or raises HTTPException on failure."""
    auth_header = http_request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token required")
    if not ACCESS_TOKEN_SECRET:
        raise HTTPException(status_code=500, detail="ACCESS_TOKEN_SECRET not configured on server")
    try:
        payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def _validate_export_auth(http_request: Request) -> None:
    """Require Bearer token for export; presence-only (no JWT verification)."""
    auth_header = http_request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token required")


# Import our modules
from data_layer.csv_loader import CSVDataLoader
from data_layer.query_engine import QueryEngine
from data_layer.krion6d_client import Krion6dClient
from data_layer.krion6d_loader import Krion6dDataLoader
from data_layer.acc_client import ACCAuthManager, ACCApiClient
from data_layer.acc_loader import ACCDataLoader
from llm_providers.factory import LLMProviderFactory, LLMProviderType
from agents.orchestrator import OrchestratorAgent
from agents.data_analyst_agent import DataAnalystAgent
from agents.safety_agent import SafetyAgent
from agents.schedule_agent import ScheduleAgent
from agents.cost_agent import CostAgent
from agents.forms_agent import FormsAgent
from agents.photos_agent import PhotosAgent
from agents.meetings_agent import MeetingsAgent
from agents.transmittals_agent import TransmittalsAgent
from agents.viewer_agent import ViewerAgent
from agents.erp_agent import ERPAgent
from agents.filter_planner_agent import FilterPlannerAgent
from data_layer.erp_loader import ERPDataLoader
from data_layer.time_period_parser import parse_time_period

from export.models import ExportRequest
from export.filename import (
    build_export_filename,
    build_xlsx_filename,
    build_timestamped_export_filename,
)
from export.csv_exporter import build_csv
from export.xlsx_exporter import build_xlsx, resolve_xlsx_timestamp
from export.pdf_exporter import build_pdf

# Global instances
data_loader: Optional[CSVDataLoader] = None
query_engine: Optional[QueryEngine] = None
orchestrator: Optional[OrchestratorAgent] = None
filter_planner: Optional[FilterPlannerAgent] = None
acc_auth_manager: ACCAuthManager = ACCAuthManager()
erp_loader: Optional[ERPDataLoader] = None
erp_query_engine: Optional[QueryEngine] = None


def initialize_system():
    """Initialize the data layer, LLM providers, and agents"""
    global data_loader, query_engine, orchestrator, erp_loader, erp_query_engine

    # Get configuration from environment
    data_directory = os.getenv("DATA_DIRECTORY", "data")
    extraction_folder = os.getenv("ACC_EXTRACTION_FOLDER", "Data extraction 29.08.25")
    llm_provider_name = os.getenv("LLM_PROVIDER", "anthropic")

    # Determine which API key to use
    api_key = None
    if llm_provider_name.lower() in ("anthropic", "claude"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
    elif llm_provider_name.lower() in ("openai", "gpt"):
        api_key = os.getenv("OPENAI_API_KEY")
    elif llm_provider_name.lower() in ("google", "gemini"):
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        logger.warning(f"No API key found for provider: {llm_provider_name}")
        logger.warning("The system will start but queries will fail without a valid API key")

    # Initialize data layer - use CSVDataLoader for ACC data extraction
    logger.info(f"Loading data from: {data_directory}/{extraction_folder}")
    data_loader = CSVDataLoader(data_directory, extraction_folder)
    dataframes = data_loader.load_all()

    if not dataframes:
        logger.warning("No data files found. Run the sample data generator first.")
    else:
        logger.info(f"Loaded {len(dataframes)} data tables: {list(dataframes.keys())}")

    query_engine = QueryEngine(dataframes, data_loader.source_files)

    # Initialize ERP data layer
    erp_directory = os.getenv("ERP_DIRECTORY", "erp")
    erp_loader = ERPDataLoader(erp_directory)
    erp_dfs = erp_loader.load_all()
    if erp_dfs:
        erp_query_engine = QueryEngine(erp_dfs, erp_loader.get_all_source_files())
        logger.info(f"ERP: Loaded {len(erp_dfs)} tables: {list(erp_dfs.keys())}")
    else:
        erp_query_engine = None
        logger.info("ERP: No ERP data files found (will load when uploaded)")

    # Initialize LLM provider (only if API key available)
    if api_key:
        try:
            llm_provider = LLMProviderFactory.create_from_env(
                provider_name=llm_provider_name,
                api_key=api_key,
                model=os.getenv("LLM_MODEL")
            )
            logger.info(f"LLM provider initialized: {llm_provider_name}")

            # Initialize agents
            agents = [
                DataAnalystAgent(llm_provider, query_engine),
                SafetyAgent(llm_provider, query_engine),
                ScheduleAgent(llm_provider, query_engine),
                CostAgent(llm_provider, query_engine),
                FormsAgent(llm_provider, query_engine),
                PhotosAgent(llm_provider, query_engine),
                MeetingsAgent(llm_provider, query_engine),
                TransmittalsAgent(llm_provider, query_engine),
                ViewerAgent(llm_provider, query_engine),
                ERPAgent(llm_provider, erp_query_engine or query_engine),
            ]

            orchestrator = OrchestratorAgent(llm_provider, agents)
            logger.info(f"Orchestrator initialized with {len(agents)} agents")

            # Initialize filter planner for external data queries
            global filter_planner
            filter_planner = FilterPlannerAgent(llm_provider, query_engine)
            logger.info("Filter planner agent initialized")

        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}")
            orchestrator = None
    else:
        orchestrator = None

    return dataframes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting ACC Dashboard Agent System...")
    initialize_system()

    # Initialize cache
    cache = await create_cache_from_env()
    logger.info(f"Cache initialized: {type(cache).__name__}")

    yield

    # Shutdown
    logger.info("Shutting down ACC Dashboard Agent System...")
    # Close cache connection if needed
    cache = get_cache()
    if cache and hasattr(cache, 'close'):
        await cache.close()


# Create FastAPI app
app = FastAPI(
    title="ACC Dashboard Multi-Agent System",
    description="Natural language interface for querying construction project data",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class QueryRequest(BaseModel):
    query: str
    project_id: Optional[str] = None
    data_source: Optional[str] = "acc"         # "acc", "krion6d", "erp", or "viewer"
    module: Optional[str] = "design"           # Krion6d API module
    user_id: Optional[int] = None              # Krion6d user ID (from login response)
    model_context: Optional[dict] = None       # 3D model metadata (categories, properties, selected elements)


class InteractionSummary(BaseModel):
    total_steps: int = 0
    agents_involved: List[str] = []
    tool_calls: int = 0
    errors: int = 0
    total_duration_ms: float = 0


class QueryResponse(BaseModel):
    success: bool
    interpretation: Optional[str] = None
    data: Optional[Union[dict, list]] = None  # Can be dict or list of records
    message: Optional[str] = None
    charts: Optional[List[dict]] = None
    agents_used: Optional[List[str]] = None
    routing: Optional[dict] = None  # Intent, reasoning, selected agents
    interaction_logs: Optional[List[dict]] = None  # Detailed interaction logs
    interaction_summary: Optional[InteractionSummary] = None  # Summary stats
    error: Optional[str] = None
    viewer_actions: Optional[List[dict]] = None  # Viewer commands for 3D viewer control
    follow_up_questions: Optional[List[str]] = None  # Suggested follow-up questions
    # Authoritative data scope for UI labels (avoids mismatch with user phrasing / chart titles).
    scoped_project_id: Optional[str] = None
    scoped_project_name: Optional[str] = None
    project_resolved_from_query: bool = False


class ExternalDataContext(BaseModel):
    """Context about external data connected to the model"""
    columns: List[str] = []
    distinct_values: dict = {}  # column_name -> list of distinct values
    identity_column: Optional[str] = None
    status_column: Optional[str] = None
    progress_column: Optional[str] = None


class ModelContext(BaseModel):
    """Context about the 3D model"""
    categories: List[str] = []
    searchable_properties: List[str] = []
    element_count: int = 0
    selected_ids: List[int] = []


class FilterQueryRequest(BaseModel):
    """Request for filter-based queries with external data"""
    query: str
    model_context: Optional[ModelContext] = None
    external_data_context: Optional[ExternalDataContext] = None


class FilterOperation(BaseModel):
    """A single filter operation"""
    source: str  # "model" or "external"
    property: str
    operator: str  # equals, contains, gt, lt, etc.
    value: Any
    caseSensitive: bool = False


class FilterQueryResponse(BaseModel):
    """Response containing filter operations for frontend execution"""
    success: bool
    filter_operations: List[dict] = []
    combine_mode: str = "AND"  # "AND" or "OR"
    viewer_actions: List[dict] = []
    interpretation: Optional[str] = None
    requires_external_data: bool = False
    error: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# Auth Endpoints
@app.get("/login")
async def login_page():
    """Serve the login page"""
    login_path = Path("frontend/login.html")
    if login_path.exists():
        return FileResponse(login_path)
    raise HTTPException(status_code=404, detail="Login page not found")


@app.post("/api/auth/login")
async def auth_login(request: LoginRequest):
    """Proxy login request to Krion6d API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://jkr-api.krion6d.com/api/v1/auth/login",
                json={"username": request.username, "password": request.password},
                headers={"Origin": "https://jkr.krion6d.com"}
            )

        if response.status_code == 200:
            return response.json()
        else:
            # Normalize auth failures to a safe, user-friendly message.
            if response.status_code in (400, 401, 403):
                raise HTTPException(status_code=401, detail="Incorrect username or password")

            detail = "Authentication failed"
            try:
                body = response.json()
                detail = body.get("message", body.get("detail", detail))
            except Exception:
                pass
            raise HTTPException(status_code=response.status_code, detail=detail)

    except httpx.RequestError as e:
        logger.error(f"Auth proxy error: {e}")
        raise HTTPException(status_code=502, detail="Authentication service unavailable")


@app.post("/api/auth/logout")
async def auth_logout():
    """Logout endpoint - token clearing is client-side"""
    return {"success": True}


# ---------------------------------------------------------------------------
# ACC OAuth 2.0 Endpoints
# ---------------------------------------------------------------------------
from fastapi.responses import HTMLResponse


@app.get("/api/acc/login")
async def acc_login(request: Request):
    """Return the Autodesk OAuth authorization URL for the frontend to open in a popup."""
    if not acc_auth_manager.client_id:
        raise HTTPException(status_code=503, detail="APS_CLIENT_ID not configured")

    # Extract JWT userID to tie the ACC session to the authenticated user
    app_user_id = ""
    try:
        payload = verify_bearer_token(request)
        app_user_id = str(payload.get("userID", ""))
    except Exception:
        pass  # ACC login may work without JWT in dev mode

    url, state = acc_auth_manager.get_authorization_url(app_user_id=app_user_id)
    return {"url": url, "state": state}


@app.get("/api/acc/callback")
async def acc_callback(code: str = Query(...), state: str = Query(default="")):
    """Handle the OAuth callback from Autodesk. Exchanges code for tokens and returns
    an HTML page that posts the result back to the opener window and closes itself."""
    try:
        result = await acc_auth_manager.exchange_code(code, state)

        html = f"""<!DOCTYPE html>
<html><head><title>ACC Login Success</title></head>
<body>
<h2>Login successful! This window will close automatically.</h2>
<script>
    // Try postMessage to opener (may fail if cross-origin redirect cleared opener)
    try {{
        if (window.opener && !window.opener.closed) {{
            window.opener.postMessage({{
                type: 'acc-auth-callback',
                success: true,
                accUserId: '{result["acc_user_id"]}',
                userName: '{result.get("user_name", "")}',
                email: '{result.get("email", "")}'
            }}, '*');
        }}
    }} catch(e) {{
        console.log('postMessage failed:', e);
    }}
    // Close after delay to give polling fallback time to detect
    setTimeout(function() {{ window.close(); }}, 2000);
</script>
</body></html>"""
        return HTMLResponse(content=html)

    except Exception as e:
        logger.error(f"ACC OAuth callback error: {e}")
        html = f"""<!DOCTYPE html>
<html><head><title>ACC Login Failed</title></head>
<body>
<h2>Login failed: {str(e)}</h2>
<script>
    if (window.opener) {{
        window.opener.postMessage({{
            type: 'acc-auth-callback',
            success: false,
            error: '{str(e)}'.replace("'", "\\'")
        }}, '*');
    }}
    setTimeout(function() {{ window.close(); }}, 3000);
</script>
</body></html>"""
        return HTMLResponse(content=html, status_code=200)


@app.get("/api/acc/status")
async def acc_status(request: Request):
    """Check ACC connection status for the authenticated user."""
    user_key = ""
    try:
        payload = verify_bearer_token(request)
        user_key = str(payload.get("userID", ""))
    except Exception:
        pass
    if not user_key:
        return {"connected": False}
    return acc_auth_manager.get_status(user_key)


@app.post("/api/acc/disconnect")
async def acc_disconnect(request: Request):
    """Disconnect ACC OAuth for the authenticated user."""
    user_key = ""
    try:
        payload = verify_bearer_token(request)
        user_key = str(payload.get("userID", ""))
    except Exception:
        pass
    if user_key:
        acc_auth_manager.disconnect(user_key)
    return {"success": True}




    """Test schedule API — returns raw schedule activities from ACC.
    
    Usage: GET /api/acc/test/schedule?project_id=<optional>
    If project_id is omitted, uses the first available project.
    """
    user_key = ""
    try:
        payload = verify_bearer_token(request)
        user_key = str(payload.get("userID", ""))
    except Exception:
        user_key = acc_auth_manager.get_any_connected_user() or ""

    if not user_key:
        raise HTTPException(status_code=401, detail="Not connected to ACC. Please login first.")

    try:
        token = await acc_auth_manager.get_valid_token(user_key)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))

    client = ACCApiClient(token)

    # If no project_id provided, get the first project
    if not project_id:
        projects = await client.list_projects()
        if not projects:
            return {"error": "No projects found", "projects": []}
        project_id = projects[0]["id"]
        project_name = projects[0].get("name", "")
    else:
        project_name = project_id

    # Fetch schedule
    try:
        activities = await client.list_project_schedule_activities(project_id)
        return {
            "status": "success",
            "project_id": project_id,
            "project_name": project_name,
            "total_activities": len(activities),
            "sample_fields": list(activities[0].keys()) if activities else [],
            "activities": activities[:20],  # First 20 for preview
        }
    except Exception as e:
        return {
            "status": "error",
            "project_id": project_id,
            "error": f"{type(e).__name__}: {e}",
            "debug": await client.debug_schedule_fetch(project_id),
        }


@app.get("/api/acc/test/transmittals")
async def acc_test_transmittals(request: Request, project_id: str = Query(default="")):
    """Test transmittals API — returns raw transmittal data from ACC.
    
    Usage: GET /api/acc/test/transmittals?project_id=<optional>
    If project_id is omitted, uses the first available project.
    """
    user_key = ""
    try:
        payload = verify_bearer_token(request)
        user_key = str(payload.get("userID", ""))
    except Exception:
        user_key = acc_auth_manager.get_any_connected_user() or ""

    if not user_key:
        raise HTTPException(status_code=401, detail="Not connected to ACC. Please login first.")

    try:
        token = await acc_auth_manager.get_valid_token(user_key)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))

    client = ACCApiClient(token)

    # If no project_id provided, get the first project
    if not project_id:
        projects = await client.list_projects()
        if not projects:
            return {"error": "No projects found", "projects": []}
        project_id = projects[0]["id"]
        project_name = projects[0].get("name", "")
    else:
        project_name = project_id

    # Fetch transmittals
    try:
        transmittals = await client.list_transmittals(project_id)
        return {
            "status": "success",
            "project_id": project_id,
            "project_name": project_name,
            "total_transmittals": len(transmittals),
            "sample_fields": list(transmittals[0].keys()) if transmittals else [],
            "transmittals": transmittals[:20],  # First 20 for preview
        }
    except Exception as e:
        return {
            "status": "error",
            "project_id": project_id,
            "error": f"{type(e).__name__}: {e}",
        }


@app.get("/api/acc/test/members")
async def acc_test_members(request: Request, project_id: str = Query(default="")):
    """Test project members API — returns raw member data for user ID resolution.
    
    Usage: GET /api/acc/test/members?project_id=<optional>
    """
    user_key = ""
    try:
        payload = verify_bearer_token(request)
        user_key = str(payload.get("userID", ""))
    except Exception:
        user_key = acc_auth_manager.get_any_connected_user() or ""

    if not user_key:
        raise HTTPException(status_code=401, detail="Not connected to ACC. Please login first.")

    try:
        token = await acc_auth_manager.get_valid_token(user_key)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))

    client = ACCApiClient(token)

    if not project_id:
        projects = await client.list_projects()
        if not projects:
            return {"error": "No projects found"}
        project_id = projects[0]["id"]
        if projects[0].get("hub_id"):
            client.account_id = projects[0]["hub_id"]

    try:
        members = await client.list_project_members(project_id)
        return {
            "status": "success",
            "project_id": project_id,
            "total_members": len(members),
            "sample_fields": list(members[0].keys()) if members else [],
            "members": members[:20],
        }
    except Exception as e:
        debug = await client.debug_user_resolution(project_id)
        return {
            "status": "error",
            "project_id": project_id,
            "error": f"{type(e).__name__}: {e}",
            "debug": debug,
        }


@app.get("/api/acc/test/schedule-connector")
async def acc_test_schedule_connector(request: Request, project_id: str = Query(default="")):
    """Test Data Connector API for schedule extraction.

    This is the fallback used when the direct Schedule API returns 403.
    Usage: GET /api/acc/test/schedule-connector?project_id=<optional>
    NOTE: This triggers a batch extraction job that takes 1-5 minutes.
    """
    user_key = ""
    try:
        payload = verify_bearer_token(request)
        user_key = str(payload.get("userID", ""))
    except Exception:
        user_key = acc_auth_manager.get_any_connected_user() or ""

    if not user_key:
        raise HTTPException(status_code=401, detail="Not connected to ACC. Please login first.")

    try:
        token = await acc_auth_manager.get_valid_token(user_key)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))

    client = ACCApiClient(token)

    # Get account_id from projects
    projects = await client.list_projects()
    if not projects:
        return {"error": "No projects found"}

    account_id = ""
    for p in projects:
        if p.get("hub_id"):
            account_id = p["hub_id"]
            break
    if not account_id:
        return {"error": "No hub_id found in projects — cannot use Data Connector"}

    if not project_id:
        project_id = projects[0]["id"]

    try:
        # Step 1: Create extraction request
        debug_steps = {}
        request = await client.create_data_extraction(
            account_id=account_id,
            service_groups=["schedule"],
            project_id=project_id,
        )
        request_id = request.get("id", "")
        debug_steps["1_create_request"] = {
            "status": "success",
            "request_id": request_id,
            "raw": {k: v for k, v in request.items() if k != "accessToken"},
        }

        if not request_id:
            return {"status": "error", "error": "No request ID", "debug": debug_steps}

        # Step 2: Check request status
        import asyncio
        req_status = await client.get_request_status(account_id, request_id)
        debug_steps["2_request_status"] = req_status

        # Step 3: List jobs (try a few times)
        for attempt in range(6):  # Max ~60 seconds
            await asyncio.sleep(10)
            try:
                jobs = await client.list_extraction_jobs(account_id, request_id)
                debug_steps[f"3_jobs_attempt_{attempt}"] = {
                    "count": len(jobs),
                    "jobs": [
                        {"id": j.get("id"), "status": j.get("status"), "requestId": j.get("requestId")}
                        for j in jobs[:5]
                    ] if jobs else "empty",
                }
                if jobs:
                    job = jobs[-1]
                    job_status = job.get("status", "").lower()
                    if job_status in ("success", "completed", "complete"):
                        # Step 4: Download
                        job_id = job.get("id") or job.get("jobId", "")
                        zip_bytes = await client.download_extraction_zip(account_id, job_id)
                        debug_steps["4_download"] = {"zip_size": len(zip_bytes)}

                        # Parse
                        import csv, io, zipfile
                        tables = {}
                        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                            for name in zf.namelist():
                                if name.endswith(".csv"):
                                    tname = name.rsplit("/", 1)[-1].replace(".csv", "")
                                    with zf.open(name) as f:
                                        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
                                        records = list(reader)
                                        tables[tname] = {
                                            "rows": len(records),
                                            "columns": list(records[0].keys()) if records else [],
                                            "sample": records[0] if records else None,
                                        }

                        return {
                            "status": "success",
                            "method": "Data Connector API",
                            "project_id": project_id,
                            "tables": tables,
                            "debug": debug_steps,
                        }
                    elif job_status in ("failed", "error"):
                        return {"status": "error", "error": f"Job failed: {job}", "debug": debug_steps}
            except Exception as step_err:
                debug_steps[f"3_jobs_attempt_{attempt}"] = {"error": str(step_err)}

        # If we get here, jobs never completed in time
        return {
            "status": "timeout",
            "error": "Jobs did not complete in 60s — check debug for details",
            "debug": debug_steps,
        }

    except Exception as e:
        return {
            "status": "error",
            "project_id": project_id,
            "account_id": account_id,
            "error": f"{type(e).__name__}: {e}",
        }


# API Endpoints
@app.get("/")
async def root():
    """Serve the main dashboard page"""
    frontend_path = Path("frontend/index.html")
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {"message": "ACC Dashboard API", "docs": "/docs"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "data_loaded": data_loader is not None and len(data_loader.dataframes) > 0,
        "orchestrator_ready": orchestrator is not None,
        "tables_available": list(data_loader.dataframes.keys()) if data_loader else []
    }


@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest, http_request: Request):
    """Process natural language query through the multi-agent system"""
    if orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not initialized. Check API key configuration."
        )

    original_qe_refs: Dict[str, Any] = {}
    workflow_statuses: Dict[str, Any] = {}
    loaded_project_names: List[str] = []
    project_id_name_map: Dict[str, str] = {}  # project_id -> project_name

    try:
        query_text = normalize_user_query(request.query)
        logger.info(f"Processing query: {query_text} [source={request.data_source}]")

        # Effective scope used by both loading and orchestrator context.
        # Default is dropdown project_id; infer from query only when dropdown is All Projects.
        effective_project_id: Optional[str] = request.project_id
        project_resolved_from_query = False

        # --- ACC API mode: swap QueryEngine ---
        if request.data_source == "acc":
            # Use JWT userID as the key for ACC token lookup (secure)
            try:
                jwt_payload = verify_bearer_token(http_request)
                user_key = str(jwt_payload.get("userID", ""))
            except Exception:
                user_key = ""
            if not user_key:
                raise HTTPException(status_code=401, detail="Not connected to ACC. Please login first.")

            try:
                access_token = await acc_auth_manager.get_valid_token(user_key)
            except PermissionError as e:
                raise HTTPException(status_code=401, detail=str(e))

            client = ACCApiClient(access_token)
            loader = ACCDataLoader(client)

            # Fetch projects first
            projects_df = await loader.load_projects()
            logger.info(f"ACC: loaded {len(projects_df)} projects, columns: {list(projects_df.columns)}")

            # Pass hub_id (account_id) to client for user resolution fallback
            if "hub_id" in projects_df.columns and not projects_df.empty:
                hub_id = str(projects_df["hub_id"].iloc[0])
                if hub_id:
                    client.account_id = hub_id
                    logger.info(f"ACC: set account_id={hub_id} for user resolution")

            # Build id -> name map for scoped_project_name on QueryResponse (same pattern as Krion6d).
            if "project_id" in projects_df.columns and "project_name" in projects_df.columns:
                for _, row in projects_df.iterrows():
                    pid = str(row.get("project_id", ""))
                    pname = row.get("project_name", "")
                    if pid and pname:
                        project_id_name_map[pid] = pname

            # Fetch entity data
            if request.project_id:
                await loader.load_project_data(request.project_id)
            else:
                if "project_id" in projects_df.columns:
                    pids = projects_df["project_id"].dropna().tolist()[:10]
                    logger.info(f"ACC: fetching data for {len(pids)} projects: {pids}")
                    await loader.load_all_projects_data(pids)
                else:
                    logger.warning(f"ACC: no 'project_id' column in projects. Columns: {list(projects_df.columns)}")

            loaded_tables = {k: len(v) for k, v in loader.dataframes.items()}
            logger.info(f"ACC: available tables → {loaded_tables}")
            if loader.load_errors:
                logger.warning(f"ACC: {len(loader.load_errors)} fetch errors")


            acc_qe = QueryEngine(loader.dataframes, loader.source_files)

            for agent_name, agent in orchestrator.agents.items():
                original_qe_refs[agent_name] = agent.query_engine
                agent.query_engine = acc_qe
                for attr in ("data_tools", "agg_tools", "chart_tools"):
                    tool_obj = getattr(agent, attr, None)
                    if tool_obj is not None and hasattr(tool_obj, "qe"):
                        tool_obj.qe = acc_qe

        # --- Viewer mode: authenticate but use default QueryEngine (no data loading) ---
        elif request.data_source == "viewer":
            token_payload = verify_bearer_token(http_request)
            logger.info(f"Viewer mode: authenticated user {token_payload.get('userID')}, using default QueryEngine")

        # --- Krion6d mode: swap QueryEngine ---
        elif request.data_source == "krion6d":
            auth_header = http_request.headers.get("Authorization", "")
            token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
            if not token:
                raise HTTPException(status_code=401, detail="Authorization token required for Krion6d API")

            # Get user_id from request body, or fallback to JWT payload.
            # Krion6d list APIs expect numeric user IDs; if parsing fails, omit user filter.
            user_id = request.user_id
            if not user_id:
                try:
                    import json as _json, base64
                    payload_part = token.split(".")[1]
                    padding = 4 - len(payload_part) % 4
                    if padding != 4:
                        payload_part += "=" * padding
                    jwt_payload = _json.loads(base64.urlsafe_b64decode(payload_part))
                    jwt_user_id = jwt_payload.get("userID")
                    user_id = int(jwt_user_id) if jwt_user_id is not None else None
                except Exception:
                    user_id = None
            logger.info(f"Krion6d: user_id = {user_id}")
            client = Krion6dClient(token, request.module or "design", user_id=user_id)
            loader = Krion6dDataLoader(client)

            # Fetch projects first
            projects_df = await loader.load_projects()
            logger.info(f"Krion6d: loaded {len(projects_df)} projects, columns: {list(projects_df.columns)}")

            if "project_name" in projects_df.columns:
                loaded_project_names = projects_df["project_name"].dropna().tolist()
                if "project_id" in projects_df.columns:
                    for _, row in projects_df.iterrows():
                        pid = str(row.get("project_id", ""))
                        pname = row.get("project_name", "")
                        if pid and pname:
                            project_id_name_map[pid] = pname

            # Detect query type and entities needed
            query_lower = query_text.lower()

            # If dropdown is "All Projects", infer scope from a project name in the query.
            if not request.project_id and project_id_name_map:
                resolved_pid = resolve_project_id_from_query(
                    query_lower, project_id_name_map
                )
                if resolved_pid:
                    effective_project_id = resolved_pid
                    project_resolved_from_query = True
                    logger.info(
                        "Krion6d: resolved project_id=%s from query (dropdown was All Projects)",
                        resolved_pid,
                    )

            # Entity keywords (check FIRST to avoid dashboard stealing entity-specific queries)
            entity_keywords = {
                "issues": ["issue", "issues", "bug", "bugs", "defect"],
                "rfis": ["rfi", "rfis", "request for information"],
                "rfas": ["rfa", "rfas", "request for action"],
                "schedule": ["task", "tasks", "schedule", "milestone", "milestones", "review", "reviews"],
                "submittals": ["submittal", "submittals", "submission", "submital", "submitals", "summital", "summitals"],
                "transmittals": ["transmittal", "transmittals", "transmital", "transmitals", "transmiital", "transmiitals"],
                "tickets": ["ticket", "tickets"],
                "meetings": ["meeting", "meetings", "mom", "minutes of meeting", "meeting minutes"],
                "punch_lists": ["punch", "punchlist", "punch list", "punch_list", "snag"],
                "check_lists": ["checklist", "check list", "check_list", "inspection"],
                "boms": [
                    "bom",
                    "boms",
                    "bill of materials",
                    "bill-of-materials",
                    "boq",
                    "boqs",
                    "bill of quantity",
                    "bill of quantities",
                    "bill-of-quantity",
                ],
            }
            needed = [entity for entity, kws in entity_keywords.items()
                      if any(kw in query_lower for kw in kws)]

            # Attachment/document intent on workflow entities should also load documents.
            attachment_keywords = [
                "attachment", "attachments", "attached", "document", "documents",
                "file", "files", "pdf", "rvt", "dwg",
            ]
            has_attachment_intent = any(kw in query_lower for kw in attachment_keywords)
            has_workflow_entity = any(
                e in needed for e in ("submittals", "transmittals", "rfis", "rfas", "issues", "tickets")
            )
            if has_attachment_intent and has_workflow_entity and "documents" not in needed:
                needed.append("documents")

            dashboard_keywords = ["summary", "overview", "count", "how many",
                "total", "pending", "project wise", "project-wise", "across project",
                "all project", "dashboard", "breakdown"]
            # Only use dashboard API if no specific entity detected AND no project scope
            is_summary_query = not effective_project_id and not needed and any(kw in query_lower for kw in dashboard_keywords)

            if is_summary_query:
                # All projects summary — use dashboard API (single call)
                logger.info("Krion6d: using dashboard API for summary query")
                await loader.load_dashboard_summary()
            else:
                if not needed:
                    needed = None
                    logger.info("Krion6d: no specific entity detected in query, fetching all")
                else:
                    logger.info(f"Krion6d: detected entities from query: {needed}")

                # Use effective_project_id so a project named in the prompt loads like a dropdown pick.
                if effective_project_id:
                    await loader.load_project_data(effective_project_id, entities=needed)
                else:
                    if "project_id" in projects_df.columns:
                        pids = projects_df["project_id"].dropna().tolist()
                        logger.info(f"Krion6d: fetching data for {len(pids)} projects: {pids}")
                        await loader.load_all_projects_data(pids, entities=needed)
                    else:
                        logger.warning(f"Krion6d: no 'project_id' column. Columns: {list(projects_df.columns)}")

            # Log what was loaded
            loaded_tables = {k: len(v) for k, v in loader.dataframes.items()}
            logger.info(f"Krion6d: available tables → {loaded_tables}")
            if loader.load_errors:
                logger.warning(f"Krion6d: {len(loader.load_errors)} fetch errors")

            # Fallback: Krion6d transmittal/submittal list endpoints can return empty/500
            # even when dashboard counters show data. Load dashboard summary so agents can
            # use it as a secondary source instead of returning zero.
            needs_transmittal_like = bool(needed and any(e in needed for e in ("transmittals", "submittals")))
            transmittals_empty = ("transmittals" not in loader.dataframes) or loader.dataframes["transmittals"].empty
            submittals_empty = ("submittals" not in loader.dataframes) or loader.dataframes["submittals"].empty
            if needs_transmittal_like and (transmittals_empty or submittals_empty):
                try:
                    project_ids = (
                        [int(effective_project_id)]
                        if effective_project_id and str(effective_project_id).isdigit()
                        else None
                    )
                    await loader.load_dashboard_summary(project_ids=project_ids, time_filter="all")
                    logger.info("Krion6d: loaded dashboard_summary fallback for transmittals/submittals")
                except Exception as e:
                    logger.warning(f"Krion6d: failed to load dashboard fallback: {e}")

            # Fetch workflow statuses only for specific project queries (skip for dashboard summary)
            first_pid = effective_project_id if not is_summary_query else None
            if first_pid:
                try:
                    await loader.load_workflow_statuses(str(first_pid))
                    workflow_statuses = loader.workflow_statuses
                    logger.info(f"Krion6d: workflow statuses → {workflow_statuses}")
                except Exception as e:
                    logger.warning(f"Krion6d: failed to load workflow statuses: {e}")

            # Create a temporary QueryEngine
            krion_qe = QueryEngine(loader.dataframes, loader.source_files)

            # Swap into every agent's tool instances
            for agent_name, agent in orchestrator.agents.items():
                original_qe_refs[agent_name] = agent.query_engine
                agent.query_engine = krion_qe
                # Swap tool-level references
                for attr in ("data_tools", "agg_tools", "chart_tools"):
                    tool_obj = getattr(agent, attr, None)
                    if tool_obj is not None and hasattr(tool_obj, "qe"):
                        tool_obj.qe = krion_qe

        # --- ERP mode: swap QueryEngine to ERP data ---
        elif request.data_source == "erp":
            verify_bearer_token(http_request)
            if erp_query_engine is None or not erp_loader or not erp_loader.dataframes:
                raise HTTPException(
                    status_code=400,
                    detail="ERP data not loaded. Please upload ERP Excel files first."
                )
            # Swap ERP query engine into the ERP agent (and data_analyst as fallback)
            for agent_name, agent in orchestrator.agents.items():
                original_qe_refs[agent_name] = agent.query_engine
                if agent_name == "erp":
                    agent.query_engine = erp_query_engine
                    for attr in ("data_tools", "agg_tools", "chart_tools"):
                        tool_obj = getattr(agent, attr, None)
                        if tool_obj is not None and hasattr(tool_obj, "qe"):
                            tool_obj.qe = erp_query_engine

        # Skip cache for user-specific data sources
        skip_cache = request.data_source in ("krion6d", "viewer", "erp")

        time_ctx = parse_time_period(query_text)
        time_filter = vars(time_ctx) if time_ctx else None

        # Scoped labels: same id the loader used (effective_project_id). Map may be filled in ACC or Krion6d.
        scoped_project_name: Optional[str] = None
        if effective_project_id:
            scoped_project_name = project_id_name_map.get(str(effective_project_id))

        # LLM context: force chart titles / prose to match loaded data, not a different project name in the prompt.
        data_scope_instruction: Optional[str] = None
        if effective_project_id and scoped_project_name:
            data_scope_instruction = (
                f"The loaded dataset is scoped to project {scoped_project_name} "
                f"(project_id={effective_project_id}). "
                "Chart titles and summaries must use this project name only; "
                "do not use a different project name from the user message if it conflicts."
            )
        elif effective_project_id:
            data_scope_instruction = (
                f"The loaded dataset is scoped to project_id={effective_project_id}. "
                "Chart titles and summaries must reflect this scope; "
                "do not use a different project name from the user message if it conflicts."
            )

        # Pass effective_project_id so agent context matches loaded data scope.
        result = await orchestrator.process_query(
            query=query_text,
            context={
                **({"project_id": effective_project_id} if effective_project_id else {}),
                "skip_cache": skip_cache,
                "data_source": request.data_source,
                **({"model_context": request.model_context} if request.model_context else {}),
                **({"workflow_statuses": workflow_statuses} if workflow_statuses else {}),
                **({"time_filter": time_filter} if time_filter else {}),
                **({"data_scope_instruction": data_scope_instruction} if data_scope_instruction else {}),
            },
        )

        # Append project scope hints.
        message = result.get('message', '')
        if request.data_source == "krion6d" and loaded_project_names:
            query_lower = query_text.lower()
            if project_resolved_from_query and effective_project_id:
                scoped_name = project_id_name_map.get(str(effective_project_id), "")
                if scoped_name:
                    message = (message or '') + (
                        f"\n\nShowing data for '{scoped_name}' only "
                        f"(matched from your message)."
                    )
            else:
                for pname in loaded_project_names:
                    if len(pname) > 2 and pname.lower() in query_lower:
                        if not request.project_id:
                            message = (message or '') + (
                                f"\n\nThis shows data across all projects. To filter for '{pname}' only, "
                                f"select it from the project dropdown at the top."
                            )
                        elif request.project_id:
                            # Option A: data always follows dropdown; warn if user names another project
                            selected_name = project_id_name_map.get(str(request.project_id), "")
                            if selected_name and pname.lower() != selected_name.lower():
                                message = (message or '') + (
                                    f"\n\nThe data shown is for '{selected_name}' (selected in the dropdown). "
                                    f"To ask about '{pname}', switch the project dropdown to that project first."
                                )
                        break

        return QueryResponse(
            success=result.get('success', False),
            interpretation=result.get('interpretation'),
            data=result.get('data'),
            message=message,
            charts=result.get('charts', []),
            agents_used=result.get('agents_used', []),
            routing=result.get('routing'),
            interaction_logs=result.get('interaction_logs', []),
            interaction_summary=result.get('interaction_summary'),
            error=result.get('error'),
            viewer_actions=result.get('viewer_actions', []),
            follow_up_questions=result.get('follow_up_questions', []),
            scoped_project_id=effective_project_id,
            scoped_project_name=scoped_project_name,
            project_resolved_from_query=project_resolved_from_query,
        )

    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        import traceback
        logger.error(f"Query processing error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Restore original QueryEngine references
        for agent_name, orig_qe in original_qe_refs.items():
            agent = orchestrator.agents.get(agent_name)
            if agent:
                agent.query_engine = orig_qe
                for attr in ("data_tools", "agg_tools", "chart_tools"):
                    tool_obj = getattr(agent, attr, None)
                    if tool_obj is not None and hasattr(tool_obj, "qe"):
                        tool_obj.qe = orig_qe


@app.post("/api/filter-query", response_model=FilterQueryResponse)
async def process_filter_query(request: FilterQueryRequest):
    """Process natural language query and return filter operations for frontend execution.

    This endpoint is designed for queries involving external data. Instead of processing
    data on the backend, it analyzes the query and returns filter operations that the
    frontend can execute locally on its external data.

    The frontend should send:
    - query: The natural language query
    - model_context: Metadata about the 3D model (categories, properties, selected elements)
    - external_data_context: Metadata about connected external data (column names, distinct values)

    The response contains filter operations that the frontend should execute.
    """
    if filter_planner is None:
        raise HTTPException(
            status_code=503,
            detail="Filter planner not initialized. Check API key configuration."
        )

    try:
        logger.info(f"Processing filter query: {request.query}")

        # Build context dict from request
        context = {}
        if request.model_context:
            context['model_context'] = {
                'metadata': {
                    'categories': request.model_context.categories,
                    'searchable_properties': request.model_context.searchable_properties,
                    'element_count': request.model_context.element_count
                },
                'selected_ids': request.model_context.selected_ids
            }
        if request.external_data_context:
            context['external_data_context'] = {
                'columns': request.external_data_context.columns,
                'distinct_values': request.external_data_context.distinct_values,
                'identity_column': request.external_data_context.identity_column,
                'status_column': request.external_data_context.status_column,
                'progress_column': request.external_data_context.progress_column
            }

        result = await filter_planner.process(request.query, context)

        return FilterQueryResponse(
            success=result.success,
            filter_operations=result.metadata.get('filter_operations', []) if result.metadata else [],
            combine_mode=result.metadata.get('combine_mode', 'AND') if result.metadata else 'AND',
            viewer_actions=result.metadata.get('viewer_actions', []) if result.metadata else [],
            interpretation=result.message,
            requires_external_data=result.metadata.get('requires_external_data', False) if result.metadata else False,
            error=result.error
        )

    except Exception as e:
        logger.error(f"Filter query processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/summary")
async def get_data_summary():
    """Get summary of all loaded data tables"""
    if not data_loader or not data_loader.dataframes:
        return {"tables": {}, "message": "No data loaded"}

    summary = {}
    for name, df in data_loader.dataframes.items():
        summary[name] = {
            "rows": len(df),
            "columns": list(df.columns),
            "sample": df.head(3).to_dict('records')
        }

    return {"tables": summary, "total_tables": len(summary)}


@app.get("/api/data/{table_name}")
async def get_table_data(
    table_name: str,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """Get data from a specific table"""
    if not data_loader or table_name not in data_loader.dataframes:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    df = data_loader.dataframes[table_name]
    data = df.iloc[offset:offset + limit].to_dict('records')

    return {
        "table": table_name,
        "total_rows": len(df),
        "returned_rows": len(data),
        "offset": offset,
        "data": data
    }


@app.get("/api/data/{table_name}/schema")
async def get_table_schema(table_name: str):
    """Get schema for a specific table"""
    if not data_loader:
        raise HTTPException(status_code=503, detail="Data not loaded")

    schema = data_loader.get_schema(table_name)
    if schema is None:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    return schema


@app.post("/api/data/reload")
async def reload_data():
    """Reload all Excel files from the data directory"""
    global query_engine

    if not data_loader:
        raise HTTPException(status_code=503, detail="Data loader not initialized")

    try:
        dataframes = data_loader.load_all()
        query_engine = QueryEngine(dataframes, data_loader.source_files)

        # Update agents with new query engine
        if orchestrator:
            for agent in orchestrator.agents.values():
                agent.query_engine = query_engine

        return {
            "success": True,
            "tables": list(dataframes.keys()),
            "message": f"Reloaded {len(dataframes)} tables"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data/upload")
async def upload_excel(file: UploadFile = File(...)):
    """Upload a new Excel file to the data directory"""
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

    try:
        data_dir = Path(os.getenv("DATA_DIRECTORY", "data"))
        data_dir.mkdir(exist_ok=True)

        file_path = data_dir / file.filename
        content = await file.read()

        with open(file_path, "wb") as f:
            f.write(content)

        # Reload the specific file
        table_name = file.filename.replace('.xlsx', '')
        data_loader.reload(table_name)

        if query_engine:
            query_engine.update_dataframes(data_loader.dataframes)

        return {
            "success": True,
            "filename": file.filename,
            "table_name": table_name,
            "message": f"Uploaded and loaded {file.filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents")
async def get_agents():
    """Get information about available agents"""
    if orchestrator is None:
        return {"agents": [], "message": "Orchestrator not initialized"}

    return {"agents": orchestrator.get_available_agents()}


@app.get("/api/cache/health")
async def cache_health():
    """Check cache health status"""
    cache = get_cache()
    if cache is None:
        return {"status": "disabled", "message": "Cache not initialized"}

    try:
        healthy = await cache.health_check()
        return {
            "status": "healthy" if healthy else "unhealthy",
            "type": type(cache).__name__,
            "message": "Cache is operational" if healthy else "Cache health check failed"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/cache/clear")
async def clear_cache():
    """Clear all cached query results"""
    cache = get_cache()
    if cache is None:
        raise HTTPException(status_code=503, detail="Cache not initialized")

    try:
        success = await cache.clear()
        return {
            "success": success,
            "message": "Cache cleared successfully" if success else "Failed to clear cache"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cache/stats")
async def cache_stats():
    """Get detailed cache statistics including all entries and their TTL"""
    cache = get_cache()
    if cache is None:
        return {"status": "disabled", "message": "Cache not initialized"}

    try:
        stats = await cache.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CacheRefreshRequest(BaseModel):
    query: str
    project_id: Optional[str] = None
    ttl: Optional[int] = None  # New TTL in seconds


@app.post("/api/cache/refresh")
async def refresh_cache_entry(request: CacheRefreshRequest):
    """Refresh/extend the TTL of a specific cached query"""
    cache = get_cache()
    if cache is None:
        raise HTTPException(status_code=503, detail="Cache not initialized")

    try:
        q = normalize_user_query(request.query)
        success = await cache.refresh_query(q, request.project_id, request.ttl)
        if success:
            ttl = await cache.get_query_ttl(q, request.project_id)
            return {
                "success": True,
                "message": "Cache entry refreshed",
                "new_ttl": ttl
            }
        else:
            return {
                "success": False,
                "message": "Cache entry not found or expired"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CacheInvalidateRequest(BaseModel):
    query: Optional[str] = None
    project_id: Optional[str] = None


@app.post("/api/cache/invalidate")
async def invalidate_cache_entry(request: CacheInvalidateRequest):
    """Invalidate a specific cached query or all queries for a project"""
    cache = get_cache()
    if cache is None:
        raise HTTPException(status_code=503, detail="Cache not initialized")

    try:
        if request.query:
            # Invalidate specific query
            success = await cache.invalidate_query(
                normalize_user_query(request.query), request.project_id
            )
            return {
                "success": success,
                "message": "Cache entry invalidated" if success else "Cache entry not found"
            }
        elif request.project_id:
            # Invalidate all queries for a project
            count = await cache.invalidate_project(request.project_id)
            return {
                "success": True,
                "message": f"Invalidated {count} cache entries for project",
                "count": count
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide either 'query' or 'project_id'"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cache/entries")
async def list_cache_entries():
    """List all cache entries with their TTL information"""
    cache = get_cache()
    if cache is None:
        return {"entries": [], "message": "Cache not initialized"}

    try:
        entries = await cache.get_all_entries()
        return {
            "count": len(entries),
            "entries": entries
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects")
async def get_projects(
    request: Request,
    data_source: str = Query(default="acc"),
    module: str = Query(default="design"),
):
    """Get list of available projects from ACC API, Krion6d API, or local CSV"""
    import numpy as np

    # --- ACC API mode ---
    if data_source == "acc":
        # Use JWT userID for secure token lookup
        try:
            jwt_payload = verify_bearer_token(request)
            user_key = str(jwt_payload.get("userID", ""))
        except Exception:
            user_key = ""
        if not user_key:
            raise HTTPException(status_code=401, detail="Not connected to ACC. Please login first.")

        try:
            access_token = await acc_auth_manager.get_valid_token(user_key)
            client = ACCApiClient(access_token)
            loader = ACCDataLoader(client)
            df = await loader.load_projects()

            columns = [c for c in ["project_id", "project_name", "status", "project_type", "location"] if c in df.columns]
            if columns:
                df = df[columns]
            df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
            projects = df.to_dict("records")
            return {"projects": projects, "total": len(projects)}
        except PermissionError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            import traceback
            logger.error(f"ACC projects error: {e}\n{traceback.format_exc()}")
            raise HTTPException(status_code=502, detail=f"ACC API error: {e}")

    # --- Krion6d API mode ---
    elif data_source == "krion6d":
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required for Krion6d API")

        try:
            client = Krion6dClient(token, module)
            loader = Krion6dDataLoader(client)
            df = await loader.load_projects()

            columns = [c for c in ["project_id", "project_name", "status", "project_type", "location"] if c in df.columns]
            if columns:
                df = df[columns]
            df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
            projects = df.to_dict("records")
            return {"projects": projects, "total": len(projects)}
        except PermissionError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            import traceback
            logger.error(f"Krion6d projects error: {e}\n{traceback.format_exc()}")
            raise HTTPException(status_code=502, detail=f"Krion6d API error: {e}")

    # --- ERP mode: no projects ---
    elif data_source == "erp":
        return {"projects": [], "total": 0, "message": "ERP data source does not have projects"}

    # --- Local CSV mode (fallback) ---
    if not query_engine:
        raise HTTPException(status_code=503, detail="Query engine not initialized")

    try:
        if "projects" in data_loader.dataframes:
            df = data_loader.dataframes["projects"].copy()
            columns = []
            for col in ["project_id", "project_name", "status", "project_type", "location"]:
                if col in df.columns:
                    columns.append(col)
            if columns:
                df = df[columns]
            df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
            projects = df.to_dict('records')
            return {"projects": projects, "total": len(projects)}
        return {"projects": [], "message": "Projects table not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export")
async def export_dashboard(request: ExportRequest, http_request: Request):
    """Generate dashboard exports in csv/xlsx/pdf formats."""
    _validate_export_auth(http_request)

    fmt = (request.format or "").lower()
    snapshot = request.snapshot
    metadata = snapshot.metadata
    project_code = metadata.project_code or "AllProjects"
    timestamp = resolve_xlsx_timestamp(metadata.timestamp or "")
    filename = build_timestamped_export_filename(
        project_code=project_code,
        timestamp=timestamp,
        fmt=fmt,
    )

    try:
        if fmt == "csv":
            content = build_csv(snapshot)
            media_type = "text/csv; charset=utf-8"
        elif fmt == "xlsx":
            content = build_xlsx(snapshot)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif fmt == "pdf":
            content = build_pdf(snapshot)
            media_type = "application/pdf"
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")

        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed for format {fmt}: {e}")
        raise HTTPException(status_code=500, detail="Export generation failed")


# ---------------------------------------------------------------------------
# ERP Data Upload Endpoints (superadmin@kkm.com only)
# ---------------------------------------------------------------------------

ERP_ADMIN_USER_ID = int(os.getenv("ERP_ADMIN_USER_ID", "1"))


def _verify_erp_admin(http_request: Request) -> dict:
    """Verify the user is the ERP admin (by userID from JWT)."""
    payload = verify_bearer_token(http_request)
    user_id = payload.get("userID")
    if user_id != ERP_ADMIN_USER_ID:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You do not have permission to manage ERP data."
        )
    return payload


@app.get("/erp-upload")
async def erp_upload_page():
    """Serve the ERP upload admin page"""
    page_path = Path("frontend/erp-upload.html")
    if page_path.exists():
        return FileResponse(page_path)
    raise HTTPException(status_code=404, detail="ERP upload page not found")


@app.post("/api/erp/upload")
async def upload_erp_file(
    http_request: Request,
    file: UploadFile = File(...),
):
    """Upload an ERP Excel file (superadmin@kkm.com only).
    Accepts: project_plan.xlsx, bom.xlsx, erp_costing.xlsx
    """
    global erp_loader, erp_query_engine

    _verify_erp_admin(http_request)

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx) are supported")

    try:
        if erp_loader is None:
            erp_directory = os.getenv("ERP_DIRECTORY", "erp")
            erp_loader = ERPDataLoader(erp_directory)

        content = await file.read()
        if not erp_loader.save_uploaded_file(file.filename, content):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid filename: {file.filename}. Expected: project_plan.xlsx, bom.xlsx, or erp_costing.xlsx"
            )

        # Reload all ERP data
        erp_dfs = erp_loader.reload()
        if erp_dfs:
            erp_query_engine = QueryEngine(erp_dfs, erp_loader.get_all_source_files())

            # Update ERP agent's query engine
            if orchestrator and "erp" in orchestrator.agents:
                erp_agent = orchestrator.agents["erp"]
                erp_agent.query_engine = erp_query_engine
                for attr in ("data_tools", "agg_tools", "chart_tools"):
                    tool_obj = getattr(erp_agent, attr, None)
                    if tool_obj is not None and hasattr(tool_obj, "qe"):
                        tool_obj.qe = erp_query_engine

        return {
            "success": True,
            "filename": file.filename,
            "tables_loaded": list(erp_dfs.keys()) if erp_dfs else [],
            "message": f"Uploaded {file.filename} and reloaded ERP data.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ERP upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/erp/admin-check")
async def erp_admin_check(http_request: Request):
    """Check if the current user has ERP admin access. Returns {allowed: true/false}."""
    try:
        _verify_erp_admin(http_request)
        return {"allowed": True}
    except HTTPException:
        return {"allowed": False}


@app.get("/api/erp/status")
async def erp_status():
    """Get ERP data loading status."""
    if not erp_loader or not erp_loader.dataframes:
        return {
            "loaded": False,
            "tables": [],
            "message": "No ERP data loaded. Upload Excel files to get started.",
        }

    tables_info = {}
    for name, df in erp_loader.dataframes.items():
        tables_info[name] = {"rows": len(df), "columns": list(df.columns)}

    return {
        "loaded": True,
        "tables": list(erp_loader.dataframes.keys()),
        "tables_info": tables_info,
    }


@app.delete("/api/erp/data")
async def clear_erp_data(http_request: Request):
    """Clear all ERP data (superadmin@kkm.com only)."""
    global erp_query_engine
    _verify_erp_admin(http_request)

    if erp_loader:
        erp_loader.dataframes.clear()
        erp_loader.source_files.clear()
    erp_query_engine = None

    return {"success": True, "message": "ERP data cleared."}


# Mount static files for frontend
frontend_path = Path("frontend")
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory="frontend"), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=debug
    )
