"""
Test script to debug GitHub commit fetching
"""
import asyncio
from datetime import datetime
from models import UserContext, ParsedContext
from agents.github_fetcher import GitHubFetcherAgent

async def test_github_fetch():
    # Create a parsed context
    parsed_context = ParsedContext(
        service_name="SimpleSRETestApp",
        timestamp=datetime(2025, 11, 21, 14, 0, 0),
        keywords=["error", "timeout"],
        error_codes=["500"],
        severity="high",
        summary="Testing GitHub fetch"
    )
    
    # Initialize agent
    print("Initializing GitHub Fetcher Agent...")
    agent = GitHubFetcherAgent()
    
    # Fetch commits
    print("Fetching commits...")
    result = await agent.fetch_commits(parsed_context, time_window_hours=720)  # 30 days
    
    # Print results
    print(f"\n{'='*60}")
    print(f"Success: {result.success}")
    print(f"Error: {result.error}")
    print(f"Execution Time: {result.execution_time:.2f}s")
    print(f"Commits Found: {len(result.data.commits) if result.data else 0}")
    print(f"{'='*60}\n")
    
    if result.data and result.data.commits:
        print("Commits:")
        for i, commit in enumerate(result.data.commits[:5], 1):
            print(f"{i}. {commit.sha[:7]} - {commit.message.split(chr(10))[0][:60]}")
            print(f"   Author: {commit.author}")
            print(f"   Time: {commit.timestamp}")
    else:
        print("No commits found!")
        print(f"Agent output details: {result.metadata}")

if __name__ == "__main__":
    asyncio.run(test_github_fetch())
