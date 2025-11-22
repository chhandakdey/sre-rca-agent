"""
Test script to diagnose GitHub MCP connection issues.
"""

import asyncio
from config import settings
from integrations.github_mcp import call_github_mcp


async def test_github_connection():
    """Test GitHub API connectivity and configuration."""
    
    print("=" * 60)
    print("GitHub MCP Connection Diagnostic Test")
    print("=" * 60)
    print()
    
    # Check configuration
    print("1. Checking configuration...")
    print(f"   - GitHub Token: {'✓ Set' if settings.github_token and settings.github_token != 'your-github-token' else '✗ Not configured'}")
    print(f"   - GitHub Org: {settings.github_org}")
    print(f"   - GitHub Repo: {settings.github_repo}")
    print(f"   - MCP Server URL: {settings.github_mcp_server_url or 'Not set (will use direct API)'}")
    print()
    
    if not settings.github_token or settings.github_token == "your-github-token":
        print("❌ ERROR: GitHub token is not configured!")
        print("   Please set GITHUB_TOKEN in your .env file")
        return
    
    # Test API connectivity
    print("2. Testing GitHub API connectivity...")
    try:
        repository = f"{settings.github_org}/{settings.github_repo}"
        print(f"   Testing with repository: {repository}")
        
        # Try to fetch a small number of commits
        result = await call_github_mcp(
            "list_commits",
            {
                "owner": settings.github_org,
                "repo": settings.github_repo,
                "sha": "main",  # Try main branch
                "per_page": 3
            }
        )
        
        if result:
            print(f"   ✓ Successfully connected! Retrieved {len(result)} commits")
            print()
            print("   Sample commit:")
            if len(result) > 0:
                commit = result[0]
                print(f"   - SHA: {commit.get('sha', 'N/A')[:8]}")
                print(f"   - Message: {commit.get('commit', {}).get('message', 'N/A').split('\\n')[0][:60]}")
                print(f"   - Author: {commit.get('commit', {}).get('author', {}).get('name', 'N/A')}")
        else:
            print("   ⚠ Connection successful but no commits returned")
            
    except ValueError as ve:
        print(f"   ❌ Configuration error: {ve}")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        print()
        print("   Common causes:")
        print("   - Invalid GitHub token")
        print("   - Repository doesn't exist or is private")
        print("   - Network/firewall blocking GitHub API")
        print("   - Incorrect org/repo name")
        print()
        print("   Troubleshooting steps:")
        print("   1. Verify your GitHub token has repo access")
        print("   2. Check repository exists: https://github.com/{}/{}")
        print(f"      (https://github.com/{settings.github_org}/{settings.github_repo})")
        print("   3. Try accessing GitHub API directly:")
        print(f"      curl -H 'Authorization: token YOUR_TOKEN' https://api.github.com/repos/{settings.github_org}/{settings.github_repo}")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_github_connection())
