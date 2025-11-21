"""
FastAPI Application - Main Entry Point

This module defines the FastAPI application with all REST API endpoints
for the Teams-integrated RCA chatbot.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any
from datetime import datetime
import logging

from models import UserContext, RCAResponse, ParsedContext
from config import settings
from orchestrator import OrchestratorAgent

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="SRE RCA Agent API",
    description="Multi-agent system for root cause analysis using LangChain and Azure services",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = OrchestratorAgent()


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "service": "SRE RCA Agent",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "azure_openai": "configured",
            "github_mcp": "configured",
            "azure_mcp": "configured"
        }
    }


# ============================================================================
# Main RCA Endpoint
# ============================================================================

@app.post("/api/v1/investigate", response_model=RCAResponse)
async def investigate_incident(user_context: UserContext) -> RCAResponse:
    """
    Main endpoint for RCA investigation.
    
    This endpoint:
    1. Accepts user context (free text description of incident)
    2. Orchestrates all agents to perform investigation
    3. Returns comprehensive RCA results
    
    Args:
        user_context: User-provided incident context
        
    Returns:
        Complete RCA response with suspected causes and recommendations
        
    Example Request:
        ```json
        {
            "raw_text": "Users experiencing 500 errors in payment service at 2PM. Error: ERR_PAYMENT_TIMEOUT",
            "user_id": "user@company.com",
            "timestamp": "2025-11-21T14:00:00Z"
        }
        ```
    """
    try:
        logger.info(f"Starting investigation for user: {user_context.user_id}")
        logger.debug(f"Context: {user_context.raw_text[:100]}...")
        
        # Run investigation through orchestrator
        result = await orchestrator.investigate(user_context)
        
        logger.info(f"Investigation completed. Found {len(result.top_suspects)} suspects")
        
        return result
        
    except Exception as e:
        logger.error(f"Investigation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Investigation failed: {str(e)}"
        )


# ============================================================================
# Individual Agent Endpoints (for testing/debugging)
# ============================================================================

@app.post("/api/v1/parse-context", response_model=ParsedContext)
async def parse_context(user_context: UserContext) -> ParsedContext:
    """
    Parse user context into structured data.
    
    This endpoint uses only the Context Parser Agent to extract
    structured entities from free text.
    
    Useful for testing context parsing independently.
    """
    try:
        logger.info("Parsing context...")
        
        from agents.context_parser import ContextParserAgent
        parser = ContextParserAgent()
        result = await parser.parse_context(user_context)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        return result.data
        
    except Exception as e:
        logger.error(f"Context parsing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/fetch-commits")
async def fetch_commits(parsed_context: ParsedContext) -> Dict[str, Any]:
    """
    Fetch GitHub commits related to the incident.
    
    This endpoint uses only the GitHub Fetcher Agent.
    Useful for testing GitHub integration independently.
    """
    try:
        logger.info("Fetching GitHub commits...")
        
        from agents.github_fetcher import GitHubFetcherAgent
        fetcher = GitHubFetcherAgent()
        result = await fetcher.fetch_commits(parsed_context)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        return result.data.model_dump()
        
    except Exception as e:
        logger.error(f"GitHub fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/status/{request_id}")
async def get_investigation_status(request_id: str) -> Dict[str, Any]:
    """
    Get the status of an ongoing investigation.
    
    This endpoint allows clients to check the progress of
    long-running investigations.
    
    Args:
        request_id: Unique request ID from investigation
        
    Returns:
        Investigation status
        
    Note: This is a stub - implement with a cache/database for production
    """
    return {
        "request_id": request_id,
        "status": "completed",
        "message": "Status tracking not fully implemented yet"
    }


# ============================================================================
# Teams Bot Webhook Endpoint
# ============================================================================

@app.post("/api/v1/teams-webhook")
async def teams_webhook(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Webhook endpoint for Microsoft Teams bot integration.
    
    This endpoint receives messages from Teams, processes them
    through the RCA system, and returns adaptive card responses.
    
    Args:
        payload: Teams webhook payload
        background_tasks: FastAPI background tasks
        
    Returns:
        Response for Teams
        
    Note: This is a basic stub - implement full Teams Bot Framework for production
    """
    try:
        # Extract message from Teams payload
        message_text = payload.get("text", "")
        user_id = payload.get("from", {}).get("id", "unknown")
        
        logger.info(f"Received Teams message from {user_id}")
        
        # Create user context
        user_context = UserContext(
            raw_text=message_text,
            user_id=user_id,
            timestamp=datetime.utcnow()
        )
        
        # Run investigation
        result = await orchestrator.investigate(user_context)
        
        # Return adaptive card response
        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": result.adaptive_card
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Teams webhook error: {str(e)}")
        return {
            "type": "message",
            "text": f"Sorry, I encountered an error: {str(e)}"
        }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ============================================================================
# Application Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Execute on application startup"""
    logger.info("=" * 60)
    logger.info("SRE RCA Agent starting up...")
    logger.info(f"Azure OpenAI Endpoint: {settings.azure_openai_endpoint}")
    logger.info(f"GitHub Org: {settings.github_org}")
    logger.info(f"Correlation Time Window: {settings.correlation_time_window_hours}h")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Execute on application shutdown"""
    logger.info("SRE RCA Agent shutting down...")


# ============================================================================
# Run Application
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )
