Problem Statement:
Jarvis currently feels unintelligent because it loses context across turns, misroutes tool calls, and fails silently when inputs are incomplete.

Pain Points:
	1.	Memory is shallow
	•	Current: ConversationBufferMemory
	•	Issue: No threading of active tasks (e.g., creating a calendar event).
	2.	Schema mapping is vague
	•	The LLM guesses how to fill tool parameters (title, description, time).
	3.	Tool routing is loose
	•	Jarvis sometimes picks the wrong tool when input is vague (e.g., “I’m going to the gym” → sends an email instead of creating a reminder).
	4.	No validation layer
	•	If required tool fields are missing, Jarvis still tries → leading to failures.

Goals:
	•	Improve memory handling (retain “active task” state).
	•	Enforce strict schema validation for tools.
	•	Add intent classification/routing before tool calls.
	•	Improve error handling & clarification prompts.

Requirements:
	1.	Memory & Context
	•	Replace ConversationBufferMemory with ConversationSummaryBufferMemory or LangGraph-style state machine memory.
	•	Track structured “active task” states (e.g., {"task": "create_calendar_event", "title": "Jim", "date": "tomorrow"}).
	2.	Tool Schemas
	•	Define tools with Pydantic schemas requiring fields like title, date, time.
	•	Reject incomplete inputs and trigger clarifications.
	3.	Intent Classification
	•	Add a lightweight classifier/router chain to decide if the request is for calendar, email, search, terminal, etc.
	•	Reduce tool misfires.
	4.	Validation & Error Handling
	•	Wrap tool execution with try/except.
	•	If fields are missing, respond naturally:
“I didn’t catch the title for your event — what should I call it?”
