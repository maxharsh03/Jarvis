import pytest
from agents.nlp import nlp_agent  # Adjust if needed

# All commands to classify into
COMMANDS = [
    "check email",
    "send email",
    "get current weather",
    "get weather forecast",
    "schedule calendar",
    "check calendar",
    "plan calendar",
    "terminal",
    "execute script",
    "open file",
    "open application",
    "word definition",
    "web search",
]

# Test cases as (input_text, expected_tool)
TEST_CASES = [
    # check email
    ("any new emails?", "check email"),
    ("did I get any messages?", "check email"),
    ("show me my inbox", "check email"),

    # send email
    ("email my boss about tomorrow", "send email"),
    ("shoot a note to Sarah", "send email"),
    ("compose a message for my team", "send email"),

    # get current weather
    ("what's the weather like outside?", "get current weather"),
    ("temperature right now", "get current weather"),
    ("tell me the current conditions", "get current weather"),

    # get weather forecast
    ("will it rain tomorrow?", "get weather forecast"),
    ("give me the weekend forecast", "get weather forecast"),
    ("weather prediction for next week", "get weather forecast"),

    # schedule calendar
    ("set up a meeting with John next Friday", "schedule calendar"),
    ("put a call on my calendar", "schedule calendar"),
    ("book a lunch meeting", "schedule calendar"),

    # check calendar
    ("what's on my schedule today?", "check calendar"),
    ("show me today's agenda", "check calendar"),
    ("any events coming up?", "check calendar"),

    # plan calendar
    ("help me organize my week", "plan calendar"),
    ("suggest a good time for meetings", "plan calendar"),
    ("plan out next Monday", "plan calendar"),

    # terminal
    ("open the terminal", "terminal"),
    ("start command line", "terminal"),
    ("launch shell", "terminal"),

    # execute script
    ("run my backup script", "execute script"),
    ("start the deployment script", "execute script"),
    ("trigger the Python file", "execute script"),

    # open file
    ("open budget.xlsx", "open file"),
    ("launch the PDF from yesterday", "open file"),
    ("access the report file", "open file"),

    # open application
    ("start Spotify", "open application"),
    ("launch VSCode", "open application"),
    ("open the calendar app", "open application"),

    # word definition
    ("what does ephemeral mean?", "word definition"),
    ("define asynchronous", "word definition"),
    ("meaning of 'serendipity'", "word definition"),

    # web search
    ("who won the 2024 election?", "web search"),
    ("search for python list comprehensions", "web search"),
    ("look up nearest sushi restaurants", "web search"),
]


@pytest.mark.parametrize("input_text,expected_tool", TEST_CASES)
def test_nlp_agent_tool_detection(input_text, expected_tool):
    result = nlp_agent(input_text)
    actual_tool = result.get("tool", "unknown").lower()
    confidence = result.get("confidence", 0.0)

    assert actual_tool == expected_tool.lower(), (
        f"\n❌ FAIL: {input_text}\n"
        f"Expected: {expected_tool}, Got: {actual_tool}\n"
        f"Confidence: {confidence:.2f}"
    )
