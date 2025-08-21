Observed Issues:
	•	Calendar tool incorrectly mapped “Jim”(this should actually by gym) → description instead of title.
	•	Date resolution was hardcoded (2024-03-07) instead of calculating “tomorrow.”
	•	When user said “planet for 3:00 p.m.” (should actually be planned), Jarvis lost context of previous calendar event.
	•	“I’m going to the gym” triggered the email tool instead of reminder/calendar.
	•	Gmail API failed due to invalid to field ([user's email]).

Likely Causes:
	1.	ConversationBufferMemory doesn’t persist structured task context.
	2.	LLM free-forms tool input mapping → no strict validation.
	3.	Tools are all available at once → agent misroutes requests.
	4.	No validation layer → agent submits incomplete tool calls.

Proposed Fixes:
	1.	Memory
	•	Swap ConversationBufferMemory → ConversationSummaryBufferMemory.
	•	Add structured state tracking for in-progress tasks.
	•	Consider LangGraph or explicit finite-state machine for multi-step flows.
	2.	Tool Schema Improvements
	•	Use @tool with Pydantic schema enforcement (title, date, time = required).
	•	Reject tool calls missing mandatory arguments.
	3.	Intent Routing
	•	Add a pre-agent intent classifier → route to “calendar” vs “email” vs “search.”
	•	Could use MultiPromptChain or a simple rules-based classifier.
	4.	Validation/Error Handling
	•	If tool input is incomplete: ask clarification instead of failing.
	•	Example: If title is missing → ask “What should I call the event?”
