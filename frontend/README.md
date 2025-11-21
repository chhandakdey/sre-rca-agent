# SRE RCA Teams Bot - Frontend

A Microsoft Teams bot that provides an interactive interface for the SRE Root Cause Analysis (RCA) multi-agent system. This bot allows users to analyze incidents, query deployments, and get AI-powered recommendations directly within Microsoft Teams.

## 🎯 Features

- **Interactive Chat Interface**: Communicate with the RCA system through Teams
- **Real-time Analysis**: Get instant root cause analysis for incidents
- **Adaptive Cards**: Rich, interactive cards for displaying results
- **Command Support**: Easy-to-use commands for common operations
- **Backend Integration**: Seamless communication with FastAPI backend
- **Pure Python**: Built with Python Bot Framework SDK

## 📋 Prerequisites

- Python 3.9 or higher
- Microsoft Teams account
- Azure Bot Service registration (for production deployment)
- Access to the backend API service

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd frontend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
copy .env.example .env
```

Edit `.env` with your configuration:

```env
# Microsoft Teams Bot Configuration
BOT_ID=your-bot-id-here
BOT_PASSWORD=your-bot-password-here

# Bot Server Configuration
BOT_PORT=3978

# Backend API Configuration
BACKEND_API_URL=http://localhost:8000
BACKEND_API_TIMEOUT=30000
```

### 3. Update Teams Manifest

Edit `config/manifest.json` and replace:
- `YOUR-UNIQUE-GUID-HERE` with a new GUID
- `YOUR-BOT-ID-HERE` with your Bot ID

Generate a new GUID using:
```bash
node -e "console.log(require('crypto').randomUUID())"
```

### 4. Run the Bot Locally

```bash
python src/app.py
```

Or set the Python path and run:

```bash
set PYTHONPATH=%CD%\src
python src/app.py
```

The bot will start on `http://localhost:3978`

## 🧪 Testing with Bot Framework Emulator

1. Download [Bot Framework Emulator](https://aka.ms/botframework-emulator)
2. Open the emulator and connect to `http://localhost:3978/api/messages`
3. Enter your Bot ID and Password if configured
4. Start chatting with the bot

## 📦 Deploy to Microsoft Teams

### Step 1: Create Bot Registration in Azure

1. Go to [Azure Portal](https://portal.azure.com)
2. Create a new **Azure Bot** resource
3. Note the **Bot ID** and **Bot Password**
4. Update your `.env` file with these credentials

### Step 2: Configure Messaging Endpoint

In Azure Bot configuration, set the messaging endpoint to:
```
https://your-domain.com/api/messages
```

For local testing with ngrok:
```bash
ngrok http 3978
```
Then use: `https://your-ngrok-url.ngrok.io/api/messages`

### Step 3: Package and Upload to Teams

1. Create app icons (192x192 color.png and 32x32 outline.png)
2. Place icons in the `config/` folder
3. Zip the manifest and icons:
   ```powershell
   cd config
   Compress-Archive -Path manifest.json,color.png,outline.png -DestinationPath TeamsAppPackage.zip
   ```
4. Upload `TeamsAppPackage.zip` to Teams:
   - Open Teams
   - Go to Apps → Manage your apps
   - Click "Upload an app" → "Upload a custom app"
   - Select the zip file

### Step 4: Start Using the Bot

Once uploaded, you can:
- Add the bot to personal chats
- Add the bot to team channels
- Add the bot to group chats

## 💬 Using the Bot

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/help` | Show available commands | `/help` |
| `/analyze` | Start root cause analysis | `/analyze API errors after deployment` |
| `/status` | Check ongoing analysis status | `/status` |

### Example Conversations

**Basic Analysis:**
```
User: API is returning 500 errors in production
Bot: 🔍 Starting root cause analysis...
Bot: [Shows analysis results with root causes and recommendations]
```

**Using Commands:**
```
User: /analyze Database timeouts after latest deployment
Bot: [Performs analysis and shows results]

User: /status
Bot: 📊 Analysis Status
     ID: abc-123-def
     Status: completed
     ...
```

## 🏗️ Architecture

```
frontend/
├── src/
│   ├── app.py            # Main entry point
│   ├── bot.py            # Bot activity handler
│   ├── backend_client.py # Backend API client
│   └── __init__.py       # Package initialization
├── config/
│   └── manifest.json     # Teams app manifest
├── requirements.txt
├── .env.example
└── README.md
```

### Component Overview

- **app.py**: Initializes the aiohttp server and Bot Framework adapter
- **bot.py**: Handles Teams activities, messages, and user interactions
- **backend_client.py**: httpx-based async client for communicating with the FastAPI backend
- **manifest.json**: Teams app configuration and metadata

## 🔧 Configuration

### Backend API Client

The `backend_client.py` module provides async methods to interact with the backend:

```python
from backend_client import BackendApiClient

client = BackendApiClient()

# Analyze incident
result = await client.analyze_incident(user_context)

# Check analysis status
status = await client.get_analysis_status(analysis_id)

# Search GitHub issues
issues = await client.search_github(query, filters)

# Query deployments
deployments = await client.query_deployments(project, filters)

# Query Application Insights logs
logs = await client.query_logs(kql_query, options)

# Close client when done
await client.close()
```

### Adaptive Cards

The bot uses Adaptive Cards for rich, interactive messages. Cards are defined in `bot.py` as Python dictionaries and include:
- Welcome cards
- Help cards
- Analysis result cards
- Status cards

Customize these cards to match your branding and requirements.

## 🔐 Security Best Practices

1. **Never commit `.env` file** - Use `.env.example` as a template
2. **Use Azure Key Vault** for production secrets
3. **Implement authentication** for sensitive operations
4. **Validate user inputs** before sending to backend
5. **Use HTTPS** for all production deployments
6. **Rotate Bot Password** regularly

## 🐛 Troubleshooting

### Bot not responding in Teams

1. Check that the bot is running: `http://localhost:3978/health`
2. Verify Bot ID and Password in `.env`
3. Ensure messaging endpoint is correctly configured in Azure Bot
4. Check bot logs in the console for errors
5. Test with: `python src/app.py`

### Backend connection errors

1. Verify `BACKEND_API_URL` in `.env`
2. Ensure backend service is running
3. Check network/firewall settings
4. Test backend health endpoint: `GET http://localhost:8000/health`

### Teams manifest upload fails

1. Validate manifest JSON syntax
2. Ensure all required fields are filled
3. Check that icons are correct size (192x192 and 32x32)
4. Verify GUID is unique and valid

## 📚 Additional Resources

- [Bot Framework Documentation](https://docs.microsoft.com/en-us/azure/bot-service/)
- [Teams Bot Development](https://docs.microsoft.com/en-us/microsoftteams/platform/bots/what-are-bots)
- [Adaptive Cards Designer](https://adaptivecards.io/designer/)
- [Bot Framework Emulator](https://github.com/microsoft/BotFramework-Emulator)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

[Your License Here]

## 🆘 Support

For issues and questions:
- Create an issue in the repository
- Contact the SRE team
- Check backend documentation at `../backend/README.md`
