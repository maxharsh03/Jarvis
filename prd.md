1. Purpose

The purpose of Jarvis is to serve as a voice-activated, intelligent personal assistant powered by Ollama, Langchain, and Chroma, with PostgreSQL for structured data and RAG (Retrieval-Augmented Generation). Jarvis should execute tasks, provide accurate information, and maintain conversational memory without asking unnecessary or redundant follow-up questions.

⸻

2. Goals & Objectives
	•	Provide natural, human-like interactions with minimal friction.
	•	Integrate voice input/output with speech recognition (STT) and text-to-speech (TTS).
	•	Enable execution of simple but useful tools (weather, terminal, app launching, email, calendar, web search).
	•	Store and recall session history across conversations.
	•	Use RAG with Chroma + PostgreSQL for smart contextual recall and future personalization.
	•	Ensure responsiveness and minimal latency.

⸻

3. Features

3.1 Core AI & Memory
	•	Model: Ollama (LLaMA 3.2 or future supported LLMs).
	•	Agent Framework: Langchain’s create_tool_calling_agent for tool orchestration.
	•	Memory:
	•	Short-term: ConversationBufferMemory (per session).
	•	Long-term: Chroma (vector DB) + PostgreSQL (structured storage).
	•	RAG: Retrieve relevant user history, emails, calendar events, and past queries.

3.2 Tools & Integrations
	1.	Weather Tool – Fetch current weather by location.
	2.	Terminal Command Tool – Run shell commands safely (sandboxed).
	3.	App Launcher Tool – Open installed applications.
	4.	Email Tool – Connect to Gmail/IMAP API:
	•	Read unread emails.
	•	Summarize inbox.
	•	Search emails by keyword/sender.
	5.	Calendar Tool – Google Calendar or Outlook integration:
	•	Check upcoming events.
	•	Schedule a new event.
	•	Cancel/reschedule event.
	6.	Web Search Tool – Query the web (Firecrawl/SerpAPI/Playwright).
	7.	Smart Lookup Tool – Search Chroma/Postgres history before querying the web.

3.3 Intelligence & UX Requirements
	•	Jarvis must:
	•	Not ask redundant or obvious follow-up questions (e.g., if you say “what’s the weather in Raleigh”, it should not ask “which city?”).
	•	Use contextual inference (location, past preferences, session context).
	•	Keep responses short, smart, and human-like.
	•	Wake Word: "Jarvis"
	•	Shutdown Phrase: "Jarvis shut down"

3.4 Storage
	•	PostgreSQL: Store structured data like user profiles, preferences, calendar events, and task history.
	•	Chroma: Store embeddings of past conversations, documents, and searches for semantic retrieval.
	•	Hybrid Retrieval: Use RAG (Chroma for semantic similarity, PostgreSQL for structured recall).

⸻

4. User Stories
	1.	Weather
	•	As a user, I want to say “Jarvis, what’s the weather in Raleigh?”, and Jarvis should answer instantly without asking me again for the location.
	2.	Terminal Command
	•	As a user, I want to say “Jarvis, run ls in my desktop folder”, and Jarvis should execute and read back the result.
	3.	App Launcher
	•	As a user, I want to say “Jarvis, open Spotify”, and Jarvis should launch the app.
	4.	Email
	•	As a user, I want to say “Jarvis, check my unread emails from today”, and Jarvis should summarize them.
	5.	Calendar
	•	As a user, I want to say “Jarvis, book a meeting with Aryan tomorrow at 2pm”, and Jarvis should create a Google Calendar event.
	6.	Web Search
	•	As a user, I want to say “Jarvis, look up the latest news on Anduril Industries”, and Jarvis should return a short summary.
	7.	RAG Recall
	•	As a user, I want to say “Jarvis, what did I ask you about Anduril last week?”, and Jarvis should retrieve that past query from memory.

⸻

5. Technical Requirements

5.1 Architecture
	•	Frontend: Voice interface (STT + TTS).
	•	Backend: FastAPI server for handling agent requests.
	•	LLM Agent: Langchain orchestrating Ollama + tools.
	•	Database: PostgreSQL for structured data, Chroma for semantic retrieval.
	•	RAG Layer: Combined retrieval before calling the LLM.

5.2 Security & Privacy
	•	Use OAuth2 for Google/Gmail/Calendar integrations.
	•	Terminal commands restricted to safe, user-allowed commands.
	•	Data stored locally (unless user opts into cloud sync).

⸻

6. Success Metrics
	•	Accuracy: ≥ 90% of user queries correctly understood.
	•	Latency: Average response ≤ 2 seconds for tool calls, ≤ 5 seconds for web search.
	•	Memory Recall: Correctly recall past queries ≥ 95% of the time.
	•	User Satisfaction: Subjective measure through daily usage without frustration.

⸻

7. Future Enhancements
	•	Slack/Notion integration.
	•	Multi-modal (image + text + voice).
	•	Personal knowledge ingestion (PDFs, docs).
	•	Advanced task scheduling (recurring events, reminders).
