"""
Configuration Management Module

This module handles all application configuration using Pydantic Settings.
It loads environment variables and provides type-safe configuration access.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables or .env file.
    """
    
    # Azure OpenAI / Azure Foundry Configuration
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment_name: str = "gpt-4-1-nano"
    azure_openai_api_version: str = "2024-02-15-preview"
    
    # Azure MCP Configuration
    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: str
    azure_subscription_id: str
    
    # Azure DevOps Configuration
    azure_devops_org_url: str
    azure_devops_pat: str
    
    # App Insights Configuration
    app_insights_workspace_id: str
    app_insights_app_id: Optional[str] = None
    app_insights_connection_string: Optional[str] = None
    
    # GitHub Configuration
    github_token: str
    github_org: str
    github_repo: str
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    log_level: str = "INFO"
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Correlation Engine Configuration
    correlation_time_window_hours: int = 24
    correlation_max_results: int = 10
    enable_ml_correlation: bool = True
    
    # MCP Server URLs (optional - for external MCP servers)
    azure_mcp_server_url: Optional[str] = None
    github_mcp_server_url: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )


# Global settings instance
settings = Settings()
