"""
Context Parser Agent

This agent parses and understands free-text user input using rule-based extraction,
extracting structured entities like service names, error codes, timestamps, and severity levels.
"""

from typing import Dict, Any
from datetime import datetime
import json
import re

from models import UserContext, ParsedContext, SeverityLevel, AgentResult
from config import settings


class ContextParserAgent:
    """
    Agent responsible for parsing user context into structured data.
    
    This agent uses GPT-4.1 Nano to understand natural language descriptions
    of incidents and extract key entities for downstream processing.
    """
    
    def __init__(self):
        """Initialize the Context Parser Agent"""
        # Simple rule-based parser - no LLM needed for basic entity extraction
        pass
    
    def _get_system_prompt(self) -> str:
        """
        Get the system prompt for context parsing.
        
        Returns:
            System prompt string
        """
        return """You are an expert SRE assistant that analyzes incident reports.

Your task is to parse free-text incident descriptions and extract structured information.

Extract the following entities:
1. **service_name**: The name of the affected service or module (e.g., "payment-service", "auth-api")
2. **error_codes**: List of error codes mentioned (e.g., ["ERR_TIMEOUT", "500"])
3. **timestamp**: The incident timestamp (convert to ISO 8601 format)
4. **severity**: Severity level (critical, high, medium, low, info)
5. **keywords**: Key terms that might be useful for searching logs (e.g., ["timeout", "database", "connection"])
6. **summary**: A concise 1-2 sentence summary of the issue

Guidelines:
- If no explicit timestamp is given, infer it from phrases like "around 2PM", "this morning", "10 minutes ago"
- If no service name is explicitly mentioned, try to infer it from context
- Extract ALL error codes, HTTP status codes, and error identifiers
- Be conservative with severity - only mark as "critical" if clearly stated or implied
- Include technical terms and domain-specific keywords

Return ONLY a valid JSON object with these fields:
{
    "service_name": "string or null",
    "error_codes": ["string"],
    "timestamp": "ISO 8601 string or null",
    "severity": "critical|high|medium|low|info",
    "keywords": ["string"],
    "summary": "string"
}

Do not include any explanation, only the JSON object."""
    
    async def parse_context(self, user_context: UserContext) -> AgentResult:
        """
        Parse user context into structured data using rule-based extraction.
        
        Args:
            user_context: User-provided context
            
        Returns:
            AgentResult with ParsedContext data
        """
        start_time = datetime.utcnow()
        
        try:
            # Use rule-based extraction instead of LLM
            parsed_context = self._create_fallback_context(user_context)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            print(f"[Context Parser] ✓ Parsed context in {execution_time:.2f}s")
            print(f"[Context Parser]   Service: {parsed_context.service_name}")
            print(f"[Context Parser]   Error codes: {parsed_context.error_codes}")
            print(f"[Context Parser]   Severity: {parsed_context.severity.value}")
            
            return AgentResult(
                agent_name="context_parser",
                success=True,
                data=parsed_context,
                error=None,
                execution_time=execution_time,
                metadata={
                    "extraction_method": "rule_based"
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            print(f"[Context Parser] ✗ Error: {str(e)}")
            
            # Fallback: Create minimal parsed context
            fallback_context = ParsedContext(
                service_name=None,
                error_codes=[],
                timestamp=user_context.timestamp or datetime.utcnow().replace(tzinfo=None),
                severity=SeverityLevel.medium,
                keywords=[],
                summary=user_context.raw_text[:200]
            )
            
            return AgentResult(
                agent_name="context_parser",
                success=False,
                data=fallback_context,
                error=str(e),
                execution_time=execution_time,
                metadata={"fallback": True}
            )
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response JSON.
        
        Args:
            response: LLM response string
            
        Returns:
            Parsed dictionary
        """
        # Try to extract JSON from response
        # Sometimes LLMs add markdown code blocks
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)
        
        # Remove any leading/trailing non-JSON content
        response = response.strip()
        if not response.startswith('{'):
            # Find the first {
            start_idx = response.find('{')
            if start_idx != -1:
                response = response[start_idx:]
        
        return json.loads(response)
    
    def _parse_timestamp(self, timestamp_str: str, fallback: datetime = None) -> datetime:
        """
        Parse timestamp string to datetime.
        
        Args:
            timestamp_str: ISO 8601 timestamp string
            fallback: Fallback timestamp if parsing fails
            
        Returns:
            Parsed datetime
        """
        if not timestamp_str or timestamp_str == "null":
            return fallback or datetime.utcnow()
        
        try:
            # Handle various ISO 8601 formats
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            return datetime.fromisoformat(timestamp_str)
        except Exception:
            return fallback or datetime.utcnow()
    
    def _create_fallback_context(self, user_context: UserContext) -> ParsedContext:
        """
        Create fallback parsed context using simple heuristics.
        
        Args:
            user_context: User context
            
        Returns:
            Basic ParsedContext
        """
        raw_text = user_context.raw_text.lower()
        
        # Simple error code extraction
        error_codes = re.findall(r'err_[\w_]+|error[\s_]?\d+|\d{3}(?:\s+error)?', raw_text, re.IGNORECASE)
        
        # Simple keyword extraction
        technical_keywords = ['error', 'timeout', 'failed', 'crash', 'down', 'slow', 
                            'exception', 'unauthorized', 'forbidden', 'not found']
        keywords = [kw for kw in technical_keywords if kw in raw_text]
        
        # Determine severity from keywords
        severity = SeverityLevel.MEDIUM
        if any(word in raw_text for word in ['critical', 'down', 'crash', 'outage']):
            severity = SeverityLevel.CRITICAL
        elif any(word in raw_text for word in ['urgent', 'high', 'severe']):
            severity = SeverityLevel.HIGH
        
        return ParsedContext(
            service_name=None,
            error_codes=error_codes,
            timestamp=user_context.timestamp or datetime.utcnow(),
            severity=severity,
            keywords=keywords,
            summary=user_context.raw_text[:200]
        )


# Convenience function for standalone usage
async def parse_user_context(user_context: UserContext) -> ParsedContext:
    """
    Standalone function to parse user context.
    
    Args:
        user_context: User-provided context
        
    Returns:
        Parsed context
    """
    agent = ContextParserAgent()
    result = await agent.parse_context(user_context)
    
    if result.success:
        return result.data
    else:
        # Return fallback data even on error
        return result.data
