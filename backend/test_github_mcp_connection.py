"""
Test GitHub MCP Connection

This script tests the GitHub MCP integration using the stdio client approach.
"""

import asyncio
import logging
from integrations.github_mcp import (
    initialize_github_mcp,
    call_github_mcp_tool,
    close_github_mcp,
    _available_tools
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_github_mcp_connection():
    """Test GitHub MCP connection and list available tools."""
    try:
        logger.info("=" * 60)
        logger.info("Testing GitHub MCP Connection")
        logger.info("=" * 60)
        
        # Initialize MCP session
        logger.info("\n1. Initializing GitHub MCP session...")
        session = await initialize_github_mcp()
        
        # Import _available_tools after initialization
        from integrations.github_mcp import _available_tools
        
        logger.info(f"✓ Session initialized successfully")
        
        # List available tools
        logger.info(f"\n2. Available GitHub MCP Tools ({len(_available_tools)}):")
        for i, tool in enumerate(_available_tools, 1):
            tool_name = tool['function']['name']
            tool_desc = tool['function']['description']
            logger.info(f"   {i}. {tool_name}")
            logger.info(f"      {tool_desc[:100]}...")
        
        # Test getting file contents
        logger.info("\n3. Testing Get File Contents...")
        try:
            result = await call_github_mcp_tool(
                "get_file_contents",
                {
                    "owner": "chhandakdey",
                    "repo": "SimpleSRETestApp",
                    "path": "README.md"
                }
            )
            logger.info(f"✓ File retrieval executed successfully")
            logger.info(f"   Result preview: {str(result)[:200]}...")
        except Exception as e:
            logger.warning(f"⚠ File retrieval test failed: {e}")
        
        logger.info("\n" + "=" * 60)
        logger.info("GitHub MCP Connection Test Complete")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error testing GitHub MCP connection: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await close_github_mcp()


async def interactive_mode():
    """Interactive mode to test GitHub MCP tools."""
    try:
        logger.info("Starting Interactive GitHub MCP Mode...")
        
        # Initialize session
        await initialize_github_mcp()
        
        # Import _available_tools after initialization
        from integrations.github_mcp import _available_tools
        
        logger.info("\nAvailable tools:")
        for i, tool in enumerate(_available_tools, 1):
            logger.info(f"{i}. {tool['function']['name']}")
        
        logger.info("\nEnter 'quit' to exit\n")
        
        while True:
            try:
                user_input = input("\nEnter tool name (or number) to test: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                # Check if input is a number
                if user_input.isdigit():
                    tool_idx = int(user_input) - 1
                    if 0 <= tool_idx < len(_available_tools):
                        tool_name = _available_tools[tool_idx]['function']['name']
                    else:
                        logger.error("Invalid tool number")
                        continue
                else:
                    tool_name = user_input
                
                # Get parameters
                params_input = input("Enter parameters as JSON (or press Enter for empty): ").strip()
                if params_input:
                    import json
                    params = json.loads(params_input)
                else:
                    params = {}
                
                # Call the tool
                logger.info(f"\nCalling {tool_name}...")
                result = await call_github_mcp_tool(tool_name, params)
                logger.info(f"Result:\n{result}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
        
        logger.info("\nExiting interactive mode...")
        
    except Exception as e:
        logger.error(f"Error in interactive mode: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await close_github_mcp()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_mode())
    else:
        asyncio.run(test_github_mcp_connection())
