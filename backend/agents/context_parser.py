"""
Context Parser Agent

This agent parses and understands free-text user input using LLM-based extraction,
extracting structured entities like service names, error codes, timestamps, and severity levels.
"""

from typing import Dict, Any
from datetime import datetime
import json
import re
from openai import AzureOpenAI

from models import UserContext, ParsedContext, SeverityLevel, AgentResult
from config import settings


class ContextParserAgent:
    """
    Agent responsible for parsing user context into structured data.
    
    This agent uses Azure OpenAI (GPT-4) to understand natural language descriptions
    of incidents and extract key entities for downstream processing.
    """
    
    def __init__(self):
        """Initialize the Context Parser Agent with Azure OpenAI client"""
        self.client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint
        )
        self.model = settings.azure_openai_deployment_name
    
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
        Parse user context into structured data using LLM-based extraction.
        
        Args:
            user_context: User-provided context
            
        Returns:
            AgentResult with ParsedContext data
        """
        start_time = datetime.utcnow()
        
        try:
            # Build the prompt with current context
            current_time = user_context.timestamp or datetime.utcnow()
            user_prompt = f"""Current Time: {current_time.isoformat()}

Incident Report:
{user_context.raw_text}

Parse this incident report and extract structured information."""

            print(f"[Context Parser] 🤖 Using LLM to parse context...")
            
            # Call Azure OpenAI for intelligent parsing
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=500,
                response_format={"type": "json_object"}  # Ensure JSON response
            )
            
            # Extract and parse the response
            llm_response = response.choices[0].message.content
            parsed_data = self._parse_llm_response(llm_response)
            
            # Build ParsedContext from LLM output
            parsed_context = ParsedContext(
                service_name=parsed_data.get("service_name"),
                error_codes=parsed_data.get("error_codes", []),
                timestamp=self._parse_timestamp(
                    parsed_data.get("timestamp"),
                    fallback=current_time.replace(tzinfo=None)
                ),
                severity=SeverityLevel(parsed_data.get("severity", "medium")),
                keywords=parsed_data.get("keywords", []),
                summary=parsed_data.get("summary", user_context.raw_text[:200])
            )
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            print(f"[Context Parser] ✓ Parsed context in {execution_time:.2f}s")
            print(f"[Context Parser]   Service: {parsed_context.service_name}")
            print(f"[Context Parser]   Error codes: {parsed_context.error_codes}")
            print(f"[Context Parser]   Severity: {parsed_context.severity.value}")
            print(f"[Context Parser]   Keywords: {', '.join(parsed_context.keywords[:5])}")
            
            return AgentResult(
                agent_name="context_parser",
                success=True,
                data=parsed_context,
                error=None,
                execution_time=execution_time,
                metadata={
                    "extraction_method": "llm_based",
                    "model": self.model,
                    "tokens_used": response.usage.total_tokens
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            print(f"[Context Parser] ✗ LLM parsing failed: {str(e)}")
            print(f"[Context Parser] ⚠️  Falling back to rule-based extraction...")
            
            # Fallback: Use rule-based extraction
            fallback_context = self._create_fallback_context(user_context)
            
            return AgentResult(
                agent_name="context_parser",
                success=True,  # Still successful, just used fallback
                data=fallback_context,
                error=None,
                execution_time=execution_time,
                metadata={
                    "extraction_method": "rule_based_fallback",
                    "llm_error": str(e)
                }
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
            timestamp_str: ISO 8601 timestamp string or None
            fallback: Fallback timestamp if parsing fails
            
        Returns:
            Parsed datetime (timezone-naive)
        """
        if not timestamp_str or timestamp_str == "null":
            return (fallback or datetime.utcnow()).replace(tzinfo=None)
        
        try:
            # Handle various ISO 8601 formats
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(timestamp_str)
            # Return timezone-naive datetime
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except Exception:
            return (fallback or datetime.utcnow()).replace(tzinfo=None)
    
    def _create_fallback_context(self, user_context: UserContext) -> ParsedContext:
        """
        Create fallback parsed context using simple rule-based heuristics.
        
        This is used when LLM parsing fails.
        
        Args:
            user_context: User context
            
        Returns:
            Basic ParsedContext
        """
        raw_text = user_context.raw_text
        raw_text_lower = raw_text.lower()
        
        # Simple error code extraction (case-insensitive)
        error_codes = list(set(re.findall(
            r'err_[\w_]+|error[\s_]?\d+|\d{3}(?:\s+error)?', 
            raw_text, 
            re.IGNORECASE
        )))
        
        # Simple service name extraction (common patterns)
        service_name = None
        service_patterns = [
            r'(?:service|api|app)[\s:-]+(\w+(?:-\w+)*)',
            r'(\w+(?:-\w+)*?)[\s-](?:service|api)',
            r'in\s+(?:the\s+)?(\w+(?:-\w+)*)\s+(?:service|api|component)'
        ]
        for pattern in service_patterns:
            match = re.search(pattern, raw_text_lower)
            if match:
                service_name = match.group(1).strip()
                break
        
        # Simple keyword extraction
        technical_keywords = [
            'error', 'timeout', 'failed', 'crash', 'down', 'slow', 
            'exception', 'unauthorized', 'forbidden', 'not found',
            'database', 'connection', 'gateway', 'authentication',
            '500', '502', '503', '504', '400', '401', '403', '404'
        ]
        keywords = [kw for kw in technical_keywords if kw in raw_text_lower]
        
        # Determine severity from keywords
        severity = SeverityLevel.MEDIUM
        if any(word in raw_text_lower for word in ['critical', 'down', 'crash', 'outage', 'production down']):
            severity = SeverityLevel.CRITICAL
        elif any(word in raw_text_lower for word in ['urgent', 'high', 'severe', '500', 'failed']):
            severity = SeverityLevel.HIGH
        elif any(word in raw_text_lower for word in ['warning', 'slow', 'degraded']):
            severity = SeverityLevel.LOW
        
        # Generate summary (first 200 chars or first sentence)
        summary = raw_text[:200]
        first_sentence = re.split(r'[.!?]\s+', raw_text)
        if first_sentence and len(first_sentence[0]) < 200:
            summary = first_sentence[0]
        
        return ParsedContext(
            service_name=service_name,
            error_codes=error_codes,
            timestamp=(user_context.timestamp or datetime.utcnow()).replace(tzinfo=None),
            severity=severity,
            keywords=keywords,
            summary=summary
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
