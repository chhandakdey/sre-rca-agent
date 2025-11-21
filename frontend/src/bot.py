"""
Teams Bot Activity Handler

This module defines the bot's behavior and handles Teams activities.
"""

import os
from datetime import datetime
from typing import Dict, Any

from botbuilder.core import ActivityHandler, TurnContext, MessageFactory, CardFactory
from botbuilder.schema import ChannelAccount, Activity, ActivityTypes

from backend_client import BackendApiClient


class SREBot(ActivityHandler):
    """SRE Root Cause Analysis Bot for Microsoft Teams."""
    
    def __init__(self):
        super().__init__()
        self.backend_client = BackendApiClient()
        # Store active analysis sessions (in production, use persistent storage like Redis)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def on_turn(self, turn_context: TurnContext):
        """Handle incoming activities."""
        await super().on_turn(turn_context)
    
    async def on_message_activity(self, turn_context: TurnContext):
        """Handle message activities from users."""
        text = turn_context.activity.text.strip().lower() if turn_context.activity.text else ""
        
        # Parse commands
        if text in ['help', '/help']:
            await self.send_help_card(turn_context)
        elif text in ['status', '/status']:
            await self.handle_status_command(turn_context)
        elif text.startswith('analyze') or text.startswith('/analyze'):
            await self.handle_analyze_command(turn_context, text)
        else:
            # Default: treat as analysis request
            await self.perform_analysis(turn_context, turn_context.activity.text)
    
    async def on_members_added_activity(self, members_added: list[ChannelAccount], turn_context: TurnContext):
        """Handle members added to the conversation."""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await self.send_welcome_message(turn_context)
    
    async def send_welcome_message(self, turn_context: TurnContext):
        """Send welcome message with instructions."""
        welcome_card = {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "👋 Welcome to SRE RCA Bot!",
                    "size": "Large",
                    "weight": "Bolder"
                },
                {
                    "type": "TextBlock",
                    "text": "I help you analyze incidents and find root causes using AI-powered analysis.",
                    "wrap": True
                },
                {
                    "type": "TextBlock",
                    "text": "**Quick Start:**",
                    "weight": "Bolder",
                    "spacing": "Medium"
                },
                {
                    "type": "TextBlock",
                    "text": "• Describe your incident or error\n• Use `/analyze` followed by your description\n• Use `/status` to check ongoing analysis\n• Use `/help` for more information",
                    "wrap": True
                }
            ]
        }
        
        message = Activity(
            type=ActivityTypes.message,
            attachments=[CardFactory.adaptive_card(welcome_card)]
        )
        await turn_context.send_activity(message)
    
    async def send_help_card(self, turn_context: TurnContext):
        """Send help card with available commands."""
        help_card = {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "📖 Available Commands",
                    "size": "Large",
                    "weight": "Bolder"
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "/help", "value": "Show this help message"},
                        {"title": "/analyze", "value": "Start root cause analysis"},
                        {"title": "/status", "value": "Check analysis status"}
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": "**Example Usage:**",
                    "weight": "Bolder",
                    "spacing": "Medium"
                },
                {
                    "type": "TextBlock",
                    "text": "`/analyze API errors in production after deployment`",
                    "wrap": True,
                    "fontType": "Monospace"
                },
                {
                    "type": "TextBlock",
                    "text": "Or simply describe your issue, and I'll analyze it automatically!",
                    "wrap": True,
                    "isSubtle": True
                }
            ]
        }
        
        message = Activity(
            type=ActivityTypes.message,
            attachments=[CardFactory.adaptive_card(help_card)]
        )
        await turn_context.send_activity(message)
    
    async def handle_analyze_command(self, turn_context: TurnContext, text: str):
        """Handle analyze command."""
        # Extract description after command
        import re
        description = re.sub(r'^/?analyze\s*', '', text, flags=re.IGNORECASE).strip()
        
        if not description:
            await turn_context.send_activity(
                'Please provide a description of the incident. Example: `/analyze API errors after deployment`'
            )
            return
        
        await self.perform_analysis(turn_context, description)
    
    async def handle_status_command(self, turn_context: TurnContext):
        """Handle status command."""
        user_id = turn_context.activity.from_property.id
        session = self.active_sessions.get(user_id)
        
        if not session:
            await turn_context.send_activity(
                "You don't have any active analysis sessions. Start one by describing an incident!"
            )
            return
        
        try:
            status = await self.backend_client.get_analysis_status(session['analysis_id'])
            await self.send_status_card(turn_context, status)
        except Exception as e:
            await turn_context.send_activity(f"❌ Failed to retrieve status: {str(e)}")
    
    async def perform_analysis(self, turn_context: TurnContext, description: str):
        """Perform root cause analysis."""
        user_id = turn_context.activity.from_property.id
        
        # Send typing indicator
        typing_activity = Activity(type=ActivityTypes.typing)
        await turn_context.send_activity(typing_activity)
        
        try:
            # Build user context matching backend's UserContext model
            user_context = {
                "raw_text": description,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send initial message
            await turn_context.send_activity("🔍 Starting root cause analysis...")
            
            # Call backend API
            result = await self.backend_client.analyze_incident(user_context)
            
            # Store session
            self.active_sessions[user_id] = {
                'analysis_id': result.get('analysis_id'),
                'timestamp': datetime.utcnow()
            }
            
            # Send results
            await self.send_analysis_results(turn_context, result)
            
        except Exception as e:
            print(f'Analysis error: {e}')
            await turn_context.send_activity(f"❌ Analysis failed: {str(e)}")
    
    async def send_analysis_results(self, turn_context: TurnContext, result: Dict[str, Any]):
        """Send analysis results as adaptive card."""
        # Extract metadata
        metadata = result.get('investigation_metadata', {})
        processing_time = metadata.get('duration_seconds')
        top_confidence = metadata.get('top_confidence', 'none')
        
        # Get summary
        summary = result.get('summary', 'Analysis completed successfully.')
        
        # Get top suspects
        top_suspects = result.get('top_suspects', [])
        
        # Build the card body
        card_body = [
            {
                "type": "TextBlock",
                "text": "✅ Root Cause Analysis Complete",
                "size": "Large",
                "weight": "Bolder",
                "color": "Good"
            },
            {
                "type": "FactSet",
                "facts": [
                    {"title": "Request ID", "value": metadata.get('request_id', 'N/A')},
                    {"title": "Top Confidence", "value": top_confidence.upper()},
                    {"title": "Processing Time", "value": f"{processing_time:.2f}s" if processing_time else "N/A"},
                    {"title": "Commits Found", "value": str(metadata.get('github_commits', 0))},
                    {"title": "Suspects Found", "value": str(len(top_suspects))}
                ]
            },
            {
                "type": "TextBlock",
                "text": "**Analysis Summary:**",
                "weight": "Bolder",
                "spacing": "Medium"
            },
            {
                "type": "TextBlock",
                "text": summary,
                "wrap": True
            }
        ]
        
        # Add suspects section if any found
        if top_suspects:
            card_body.append({
                "type": "TextBlock",
                "text": "**Top Suspected Causes:**",
                "weight": "Bolder",
                "spacing": "Medium"
            })
            
            for i, suspect in enumerate(top_suspects[:3], 1):  # Show top 3
                suspect_section = {
                    "type": "Container",
                    "spacing": "Small",
                    "separator": True,
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": f"**{i}. {suspect.get('cause_description', 'Unknown')}**",
                            "wrap": True
                        },
                        {
                            "type": "TextBlock",
                            "text": f"Confidence: {suspect.get('confidence_level', 'unknown').upper()}",
                            "size": "Small",
                            "color": "Attention" if suspect.get('confidence_level') == 'low' else "Good"
                        },
                        {
                            "type": "TextBlock",
                            "text": f"💡 {suspect.get('reasoning', 'No reasoning provided')}",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        }
                    ]
                }
                
                # Add evidence if available
                evidence = suspect.get('evidence', [])
                if evidence:
                    evidence_text = "Evidence: " + "; ".join(evidence[:3])
                    suspect_section["items"].append({
                        "type": "TextBlock",
                        "text": evidence_text,
                        "wrap": True,
                        "size": "Small",
                        "isSubtle": True
                    })
                
                # Add error logs if available
                related_logs = suspect.get('related_logs', [])
                if related_logs:
                    # Show error summary
                    error_summary = f"🔴 {len(related_logs)} error log(s) found"
                    suspect_section["items"].append({
                        "type": "TextBlock",
                        "text": error_summary,
                        "wrap": True,
                        "size": "Small",
                        "weight": "Bolder",
                        "color": "Attention"
                    })
                    
                    # Show first 2 error logs with details
                    for log_idx, log in enumerate(related_logs[:2], 1):
                        api_endpoint = log.get('service_name', 'N/A')
                        error_code = log.get('error_code', 'N/A')
                        message = log.get('message', '')[:150]
                        timestamp = log.get('timestamp', '')[:19]
                        
                        log_text = (
                            f"Log #{log_idx} ({timestamp}):\n"
                            f"API: {api_endpoint}\n"
                            f"Error: {error_code}\n"
                            f"Message: {message}..."
                        )
                        
                        suspect_section["items"].append({
                            "type": "TextBlock",
                            "text": log_text,
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small",
                            "fontType": "Monospace",
                            "isSubtle": True
                        })
                
                # Add commit info if available
                related_commits = suspect.get('related_commits', [])
                if related_commits:
                    # Show commit summary
                    commit_summary = f"📝 {len(related_commits)} related commit(s)"
                    suspect_section["items"].append({
                        "type": "TextBlock",
                        "text": commit_summary,
                        "wrap": True,
                        "size": "Small",
                        "weight": "Bolder",
                        "color": "Accent"
                    })
                    
                    # Show first 2 commits with details
                    for commit_idx, commit in enumerate(related_commits[:2], 1):
                        commit_sha = commit.get('sha', '')[:7]
                        commit_msg = commit.get('message', '')
                        commit_author = commit.get('author', 'Unknown')
                        commit_time = commit.get('timestamp', '')[:19]
                        files_changed = commit.get('files_changed', [])
                        additions = commit.get('additions', 0)
                        deletions = commit.get('deletions', 0)
                        commit_url = commit.get('url', '')
                        branch = commit.get('branch', 'unknown')
                        
                        commit_text = (
                            f"Commit #{commit_idx} ({commit_time}):\n"
                            f"SHA: {commit_sha} | Branch: {branch}\n"
                            f"Author: {commit_author}\n"
                            f"Message: {commit_msg}\n"
                            f"Changes: +{additions} -{deletions} in {len(files_changed)} file(s)"
                        )
                        
                        suspect_section["items"].append({
                            "type": "TextBlock",
                            "text": commit_text,
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small",
                            "fontType": "Monospace"
                        })
                        
                        # Show changed files
                        if files_changed:
                            files_text = "Files: " + ", ".join(files_changed[:5])
                            if len(files_changed) > 5:
                                files_text += f" (+{len(files_changed) - 5} more)"
                            
                            suspect_section["items"].append({
                                "type": "TextBlock",
                                "text": files_text,
                                "wrap": True,
                                "size": "Small",
                                "isSubtle": True
                            })
                        
                        # Add link to view commit on GitHub
                        if commit_url:
                            suspect_section["items"].append({
                                "type": "ActionSet",
                                "actions": [
                                    {
                                        "type": "Action.OpenUrl",
                                        "title": f"View Commit {commit_sha}",
                                        "url": commit_url
                                    }
                                ]
                            })
                
                card_body.append(suspect_section)
        
        card = {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": card_body
        }
        
        message = Activity(
            type=ActivityTypes.message,
            attachments=[CardFactory.adaptive_card(card)]
        )
        await turn_context.send_activity(message)
        
        # Send recommendations if available
        recommendations = result.get('recommendations', [])
        if recommendations:
            await turn_context.send_activity("\n**📋 Recommendations:**")
            for rec in recommendations:
                await turn_context.send_activity(f"• {rec}")
    
    async def send_status_card(self, turn_context: TurnContext, status: Dict[str, Any]):
        """Send status card."""
        message = (
            f"📊 **Analysis Status**\n\n"
            f"ID: {status.get('analysis_id')}\n"
            f"Status: {status.get('status')}\n"
            f"Created: {status.get('created_at')}"
        )
        await turn_context.send_activity(message)
