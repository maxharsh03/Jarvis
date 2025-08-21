# Jarvis - Voice-Activated AI Assistant

Jarvis is a comprehensive voice-activated AI assistant built with Python, featuring RAG (Retrieval-Augmented Generation) memory, multiple tool integrations, and natural conversation capabilities.

## 🚀 Features

### Core AI & Memory
- **LLM Backend**: Powered by Ollama with LLaMA 3.2
- **Agent Framework**: LangChain tool-calling agent for orchestration
- **Memory System**: 
  - Short-term: ConversationBufferMemory (per session)
  - Long-term: Chroma (vector DB) + SQLite/PostgreSQL
  - RAG: Semantic retrieval of past conversations and knowledge

### Tools & Integrations
1. **Weather Tool** - Current weather by location via WeatherAPI
2. **Terminal Tool** - Safe shell command execution with filtering
3. **App Launcher** - Launch installed applications (macOS/Linux/Windows)
4. **Email Tool** - Gmail/IMAP integration for reading and sending emails
5. **Calendar Tool** - Event management with memory storage
6. **Web Search Tool** - DuckDuckGo search with optional SerpAPI enhancement
7. **Memory Tool** - Smart lookup of past conversations and knowledge

### Voice Interface
- **Speech-to-Text**: Google Speech Recognition
- **Text-to-Speech**: pyttsx3 with voice selection
- **Wake Word**: "Jarvis"
- **Shutdown**: "Jarvis shut down"

## 📋 Prerequisites

1. **Python 3.8+**
2. **Ollama** with LLaMA 3.2 model:
   ```bash
   # Install Ollama: https://ollama.ai
   ollama pull llama3.2
   ollama serve
   ```
3. **System audio** (microphone and speakers)
4. **API Keys** (optional but recommended):
   - WeatherAPI key from [weatherapi.com](https://weatherapi.com)
   - Gmail app password for email features
   - SerpAPI key for enhanced web search

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Jarvis
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv jarvis-env
   source jarvis-env/bin/activate  # On Windows: jarvis-env\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and preferences
   ```

   Required `.env` variables:
   ```env
   # Weather API
   WEATHER_API_KEY=your_weatherapi_key

   # Email (Gmail)
   EMAIL_ADDRESS=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password

   # Optional enhancements
   SERPAPI_API_KEY=your_serpapi_key
   DATABASE_URL=postgresql://user:password@localhost/jarvis

   # User preferences
   USER_NAME=Your Name
   DEFAULT_LOCATION=New York, NY
   TIMEZONE=America/New_York
   ```

5. **Initialize database**:
   ```bash
   python init_db.py
   ```

## 🎤 Usage

### Voice Interface (Main Mode)
```bash
python main.py
```

1. Wait for "🎤 Listening for wake word..."
2. Say "**Jarvis**" to activate
3. Give your command naturally
4. Say "**Jarvis shut down**" to exit

### Example Commands
- **Weather**: "What's the weather in San Francisco?"
- **Email**: "Check my unread emails"
- **Calendar**: "What's on my schedule today?"
- **Web Search**: "Look up the latest news about AI"
- **Terminal**: "List files in my desktop folder"
- **Apps**: "Open Spotify"
- **Memory**: "What did we discuss about the weather yesterday?"

### REST API (Optional)
```bash
python api.py
```

- **API Docs**: http://localhost:8000/docs
- **Chat Endpoint**: POST `/chat`
- **Tools Endpoint**: POST `/tools`
- **Memory Search**: POST `/memory/search`

## 📁 Project Structure

```
Jarvis/
├── main.py                 # Main voice interface
├── api.py                  # FastAPI REST interface
├── init_db.py             # Database initialization
├── requirements.txt       # Python dependencies
├── prd.md                 # Product requirements
├── README.md              # This file
├── .env.example           # Environment template
│
├── db/                    # Database layer
│   ├── __init__.py
│   ├── models.py          # SQLAlchemy models
│   └── memory.py          # RAG memory system
│
├── tools/                 # Tool implementations
│   ├── __init__.py
│   ├── weather.py         # Weather API integration
│   ├── terminal.py        # Safe shell execution
│   ├── app_launcher.py    # Application launcher
│   ├── email.py           # Email management
│   ├── calendar.py        # Calendar integration
│   ├── web_search.py      # Web search capabilities
│   └── memory.py          # Memory/RAG tools
│
├── voice/                 # Voice I/O
│   ├── __init__.py
│   ├── stt.py            # Speech-to-text
│   └── tts.py            # Text-to-speech
│
└── test/                  # Test files
    ├── __init__.py
    └── test_*.py          # Unit tests
```

## ⚙️ Configuration

### Gmail Setup
1. Enable 2-factor authentication
2. Generate an app password: [Google Account Settings](https://myaccount.google.com/apppasswords)
3. Use the app password in `.env` as `EMAIL_PASSWORD`

### Database Options
- **SQLite** (default): Automatic, no setup required
- **PostgreSQL**: Set `DATABASE_URL` in `.env`

### Voice Customization
Edit `voice/tts.py` to change voice preferences:
- Voice selection (Daniel, etc.)
- Speech rate and volume

## 🧠 Memory System

Jarvis uses a hybrid memory approach:

1. **Vector Memory (Chroma)**:
   - Semantic search through conversations
   - Knowledge storage from web searches
   - Content similarity matching

2. **Structured Memory (SQL)**:
   - User profiles and preferences
   - Calendar events and email summaries
   - Task history and statistics

3. **Memory Integration**:
   - Automatic context retrieval before processing commands
   - Cross-session memory persistence
   - Intelligent relevance scoring

## 🔧 Development

### Adding New Tools
1. Create tool in `tools/new_tool.py`:
   ```python
   from langchain.tools import StructuredTool
   from pydantic import BaseModel, Field

   class MyToolInput(BaseModel):
       param: str = Field(..., description="Parameter description")

   def my_tool_function(param: str) -> str:
       return f"Result: {param}"

   my_tool = StructuredTool.from_function(
       name="my_tool",
       description="Tool description",
       func=my_tool_function,
       args_schema=MyToolInput
   )
   ```

2. Add to `main.py` tools list:
   ```python
   from tools.new_tool import my_tool
   
   tools = [
       # ... existing tools
       my_tool
   ]
   ```

### Running Tests
```bash
pytest test/
```

## 🔒 Security

- Terminal commands filtered for dangerous operations
- Email credentials use app passwords (not main password)
- Local data storage by default
- Safe subprocess execution with timeouts

## 📊 Performance

- **Response Time**: < 2 seconds for tool calls, < 5 seconds for web search
- **Memory Usage**: ~200MB base, scales with conversation history
- **Database**: SQLite for local, PostgreSQL for production scale

## 🚫 Limitations

- Google Calendar requires API setup (currently memory-based)
- Web search uses DuckDuckGo (rate limited)
- Voice recognition requires internet connection
- macOS optimized (cross-platform compatible)

## 🔮 Future Enhancements

- [ ] Google Calendar API integration
- [ ] Slack/Discord integrations
- [ ] Multi-modal support (images, documents)
- [ ] Advanced scheduling and reminders
- [ ] Mobile app companion
- [ ] Plugin system for custom tools

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 💬 Support

For issues, questions, or contributions:
- Create an issue on GitHub
- Check the [troubleshooting section](#troubleshooting)
- Review the [PRD](prd.md) for detailed requirements

---

**Built with ❤️ using Python, LangChain, and Ollama**