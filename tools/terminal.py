from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
import subprocess

# === 1. Safety Filter ===
def requires_confirmation(command: str) -> bool:
    """Check if a command is potentially dangerous."""
    dangerous_keywords = ['rm -rf', 'reboot', 'shutdown', 'mkfs', 'dd', 'chmod 777', ':(){', 'kill -9', '&gt;', 'curl', 'wget', 'sudo', 'su ', 'doas', 'pkexec']
    return any(word in command.lower() for word in dangerous_keywords)

# === 2. Input Schema for Executing Shell Commands ===
class TerminalCommandInput(BaseModel):
    command: str = Field(..., description="The shell command to run safely.")

# === 3. Shell Execution Function ===
def run_terminal_command(command: str) -> str:
    """Safely executes a terminal command if it passes safety check."""
    if requires_confirmation(command):
        return f"⚠️ This command appears dangerous and requires manual review:\n\n{command}"
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30  # 30 second timeout
        )
        return result.stdout.strip() if result.stdout else "✅ Command executed successfully with no output."
    except subprocess.TimeoutExpired:
        return f"❌ Command timed out after 30 seconds: {command}"
    except subprocess.CalledProcessError as e:
        return f"❌ Error executing command:\n{e.stderr.strip() if e.stderr else 'Command failed'}"
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"

# === 4. Langchain Tool: Execute Shell Command ===
run_terminal_command_tool = StructuredTool.from_function(
    name="run_terminal_command",
    description="Execute terminal commands safely. Convert natural language requests like 'list files on desktop' to actual commands like 'ls ~/Desktop'. Use this for system tasks, file operations, and running scripts.",
    func=run_terminal_command,
    args_schema=TerminalCommandInput
)