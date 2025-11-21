"""
Microsoft Teams Bot - Main Entry Point

This is the entry point for the SRE RCA Teams bot application.
"""

import os
import sys
from dotenv import load_dotenv
from aiohttp import web
from aiohttp.web import Request, Response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity

from bot import SREBot

# Load environment variables
load_dotenv()

# Create adapter
settings = BotFrameworkAdapterSettings(
    app_id=os.getenv('BOT_ID'),
    app_password=os.getenv('BOT_PASSWORD')
)
adapter = BotFrameworkAdapter(settings)


# Error handler
async def on_error(context, error):
    print(f'\n [on_error] unhandled error: {error}', file=sys.stderr)
    
    # Send error message to user
    await context.send_activity('The bot encountered an error or bug.')
    await context.send_activity('Please try again later or contact support if the issue persists.')

adapter.on_turn_error = on_error

# Create bot instance
bot = SREBot()


# Bot message handler
async def messages(req: Request) -> Response:
    """Handle incoming messages from Teams."""
    if req.content_type == 'application/json':
        body = await req.json()
    else:
        return Response(status=415)
    
    activity = Activity().deserialize(body)
    auth_header = req.headers.get('Authorization', '')
    
    try:
        response = await adapter.process_activity(activity, auth_header, bot.on_turn)
        if response:
            return Response(status=response.status, text=response.body)
        return Response(status=200)
    except Exception as e:
        print(f'Error processing activity: {e}', file=sys.stderr)
        return Response(status=500)


# Health check handler
async def health(req: Request) -> Response:
    """Health check endpoint."""
    return web.json_response({
        'status': 'healthy',
        'service': 'sre-rca-teams-bot',
        'timestamp': str(__import__('datetime').datetime.utcnow())
    })


# Create application
app = web.Application()
app.router.add_post('/api/messages', messages)
app.router.add_get('/health', health)


if __name__ == '__main__':
    PORT = int(os.getenv('BOT_PORT', 3978))
    
    print(f'\nStarting SRE RCA Teams Bot on port {PORT}')
    print('\nGet Bot Framework Emulator: https://aka.ms/botframework-emulator')
    print('\nTo test your bot in Teams, sideload the app manifest from the /config folder.')
    
    try:
        web.run_app(app, host='0.0.0.0', port=PORT)
    except Exception as e:
        print(f'Error starting bot: {e}', file=sys.stderr)
        sys.exit(1)
