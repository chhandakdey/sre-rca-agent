"""
Azure MCP Conversational Example

This example demonstrates how to use Azure MCP with Azure OpenAI 
in a conversational loop, similar to the reference implementation.
"""

import asyncio
import json
import logging
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

from integrations.azure_mcp import (
    initialize_azure_mcp,
    call_azure_mcp_tool,
    close_azure_mcp,
    _available_tools
)
from config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


async def conversational_azure_mcp():
    """
    Run a conversational loop with Azure OpenAI using Azure MCP tools.
    
    This is similar to the reference implementation provided.
    """
    try:
        # Initialize Azure OpenAI client
        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_deployment_name,
            api_key=settings.azure_openai_api_key
        )
        
        logger.info("✓ Azure OpenAI client initialized")
        
        # Initialize Azure MCP session
        await initialize_azure_mcp()
        logger.info(f"✓ Azure MCP initialized with {len(_available_tools)} tools")
        
        # Display available tools
        logger.info("\nAvailable Azure MCP Tools:")
        for i, tool in enumerate(_available_tools[:10], 1):  # Show first 10
            logger.info(f"  {i}. {tool['function']['name']}")
        if len(_available_tools) > 10:
            logger.info(f"  ... and {len(_available_tools) - 10} more tools")
        
        # Start conversational loop
        messages = []
        logger.info("\n" + "=" * 60)
        logger.info("Azure MCP Conversational Agent Ready")
        logger.info("=" * 60)
        logger.info("Ask questions about your Azure resources!")
        logger.info("Type 'quit' to exit\n")
        
        while True:
            try:
                # Get user input
                user_input = input("\n🔵 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    logger.info("\nGoodbye!")
                    break
                
                if not user_input:
                    continue
                
                messages.append({"role": "user", "content": user_input})
                
                # Keep calling API until no more tool calls
                iteration = 0
                while True:
                    iteration += 1
                    logger.debug(f"\n[Iteration {iteration}] Calling Azure OpenAI...")
                    
                    response = client.chat.completions.create(
                        model=settings.azure_openai_deployment_name,
                        messages=messages,
                        tools=_available_tools
                    )
                    
                    # Process the model's response
                    response_message = response.choices[0].message
                    messages.append(response_message)
                    
                    # Check if model wants to call tools
                    if response_message.tool_calls:
                        logger.info(f"\n🔧 Executing {len(response_message.tool_calls)} tool call(s)...")
                        
                        for tool_call in response_message.tool_calls:
                            tool_name = tool_call.function.name
                            function_args = json.loads(tool_call.function.arguments)
                            
                            logger.info(f"   - {tool_name}")
                            logger.debug(f"     Args: {json.dumps(function_args, indent=2)}")
                            
                            try:
                                # Call the Azure MCP tool
                                result = await call_azure_mcp_tool(tool_name, function_args)
                                
                                # Extract text content from result
                                if isinstance(result, dict) or isinstance(result, list):
                                    content_text = json.dumps(result, indent=2)
                                else:
                                    content_text = str(result)
                                
                                logger.debug(f"     Result: {content_text[:200]}...")
                                
                                # Add the tool response to the messages
                                messages.append({
                                    "tool_call_id": tool_call.id,
                                    "role": "tool",
                                    "name": tool_name,
                                    "content": content_text,
                                })
                                
                            except Exception as e:
                                logger.error(f"     ❌ Error: {e}")
                                # Add error response
                                messages.append({
                                    "tool_call_id": tool_call.id,
                                    "role": "tool",
                                    "name": tool_name,
                                    "content": f"Error executing tool: {str(e)}",
                                })
                    else:
                        # No more tool calls, print the response and break
                        assistant_message = response_message.content
                        print(f"\n🤖 Assistant: {assistant_message}")
                        break
                
            except KeyboardInterrupt:
                logger.info("\n\nInterrupted by user")
                break
            except Exception as e:
                logger.error(f"\n❌ Error in conversation loop: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await close_azure_mcp()
        logger.info("\n✓ Azure MCP session closed")


async def quick_test():
    """Quick test of a single Azure query."""
    try:
        logger.info("Running quick test...")
        
        # Initialize clients
        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_deployment_name,
            api_key=settings.azure_openai_api_key
        )
        
        await initialize_azure_mcp()
        
        # Test query
        messages = [
            {"role": "user", "content": "List my Azure subscriptions"}
        ]
        
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=messages,
            tools=_available_tools
        )
        
        response_message = response.choices[0].message
        
        if response_message.tool_calls:
            logger.info(f"Model wants to call: {response_message.tool_calls[0].function.name}")
            
            tool_call = response_message.tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            
            result = await call_azure_mcp_tool(tool_call.function.name, function_args)
            logger.info(f"Result: {result}")
        else:
            logger.info(f"Response: {response_message.content}")
        
    except Exception as e:
        logger.error(f"Error in quick test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await close_azure_mcp()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        asyncio.run(quick_test())
    else:
        asyncio.run(conversational_azure_mcp())
