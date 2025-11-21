"""
Backend API Client

This module handles all communication with the FastAPI backend service.
"""

import os
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class BackendApiClient:
    """Client for communicating with the FastAPI backend."""
    
    def __init__(self):
        self.base_url = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
        self.timeout = int(os.getenv('BACKEND_API_TIMEOUT', '30'))
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={'Content-Type': 'application/json'}
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def check_health(self) -> Dict[str, Any]:
        """Check backend health."""
        try:
            response = await self.client.get('/health')
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f'Backend service is unavailable: {str(e)}')
    
    async def analyze_incident(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform root cause analysis.
        
        Args:
            user_context: The user context containing error details
            
        Returns:
            RCA response dictionary
        """
        try:
            response = await self.client.post('/api/v1/investigate', json=user_context)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json().get('detail', e.response.text) if e.response else str(e)
            raise Exception(f'Analysis failed: {error_detail}')
        except Exception as e:
            raise Exception(f'Failed to connect to backend service: {str(e)}')
    
    async def get_analysis_status(self, analysis_id: str) -> Dict[str, Any]:
        """
        Get analysis status by ID.
        
        Args:
            analysis_id: The analysis ID
            
        Returns:
            Analysis status dictionary
        """
        try:
            response = await self.client.get(f'/api/v1/status/{analysis_id}')
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception('Analysis not found')
            raise Exception(f'Failed to retrieve analysis status: {str(e)}')
        except Exception as e:
            raise Exception(f'Failed to retrieve analysis status: {str(e)}')
    
    async def search_github(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Search GitHub issues.
        Note: This endpoint is not yet implemented in the backend.
        
        Args:
            query: Search query
            filters: Optional filters (repo, labels, state)
            
        Returns:
            GitHub issues
        """
        try:
            # TODO: Backend endpoint not yet implemented
            raise Exception('GitHub search endpoint not yet implemented in backend')
        except Exception as e:
            raise Exception(f'Failed to search GitHub issues: {str(e)}')
    
    async def query_deployments(self, project: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Query Azure DevOps deployments.
        Note: This endpoint is not yet implemented in the backend.
        
        Args:
            project: Project name
            filters: Optional filters (pipeline, status, timeRange)
            
        Returns:
            Deployment information
        """
        try:
            # TODO: Backend endpoint not yet implemented
            raise Exception('Azure deployments endpoint not yet implemented in backend')
        except Exception as e:
            raise Exception(f'Failed to query Azure DevOps deployments: {str(e)}')
    
    async def query_logs(self, query: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Query Application Insights logs.
        Note: This endpoint is not yet implemented in the backend.
        
        Args:
            query: KQL query
            options: Optional query options (timeRange, workspace)
            
        Returns:
            Log query results
        """
        try:
            # TODO: Backend endpoint not yet implemented
            raise Exception('Azure logs endpoint not yet implemented in backend')
        except Exception as e:
            raise Exception(f'Failed to query Application Insights logs: {str(e)}')
