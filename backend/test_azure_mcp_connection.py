"""
Test Azure MCP Connection

This script tests the Azure MCP integration using the stdio client approach.
"""

import asyncio
import logging
from integrations.azure_mcp import (
    initialize_azure_mcp,
    call_azure_mcp_tool,
    close_azure_mcp,
    _available_tools
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_azure_mcp_connection():
    """Test Azure MCP connection and list available tools."""
    try:
        logger.info("=" * 60)
        logger.info("Testing Azure MCP Connection")
        logger.info("=" * 60)
        
        # Initialize MCP session
        logger.info("\n1. Initializing Azure MCP session...")
        session = await initialize_azure_mcp()
        
        # Import _available_tools after initialization
        from integrations.azure_mcp import _available_tools
        
        logger.info(f"✓ Session initialized successfully")
        
        # List available tools
        logger.info(f"\n2. Available Azure MCP Tools ({len(_available_tools)}):")
        for i, tool in enumerate(_available_tools, 1):
            tool_name = tool['function']['name']
            tool_desc = tool['function']['description']
            logger.info(f"   {i}. {tool_name}")
            logger.info(f"      {tool_desc[:100]}...")
        
        # Test a simple query
        logger.info("\n3. Testing Azure Subscription List...")
        try:
            result = await call_azure_mcp_tool(
                "subscription_list",
                {}
            )
            logger.info(f"✓ Query executed successfully")
            logger.info(f"   Result preview: {str(result)[:200]}...")
        except Exception as e:
            logger.warning(f"⚠ Query test failed (this is expected if not configured): {e}")
        
        logger.info("\n" + "=" * 60)
        logger.info("Azure MCP Connection Test Complete")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error testing Azure MCP connection: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await close_azure_mcp()


async def interactive_mode():
    """Interactive mode to test Azure MCP tools."""
    try:
        logger.info("Starting Interactive Azure MCP Mode...")
        
        # Initialize session
        await initialize_azure_mcp()
        
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
                result = await call_azure_mcp_tool(tool_name, params)
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
        await close_azure_mcp()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_mode())
    else:
        asyncio.run(test_azure_mcp_connection())
