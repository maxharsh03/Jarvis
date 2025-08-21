from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
import subprocess
import os
import platform

class AppLauncherInput(BaseModel):
    app_name: str = Field(..., description="The name of the application to launch")

def launch_application(app_name: str) -> str:
    """Launch an installed application by name."""
    try:
        system = platform.system()
        
        if system == "Darwin":  # macOS
            # Try to open with 'open' command
            result = subprocess.run(
                ["open", "-a", app_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return f"✅ Successfully launched {app_name}"
            else:
                # Try alternative approach for common apps
                common_apps = {
                    "spotify": "Spotify",
                    "chrome": "Google Chrome",
                    "firefox": "Firefox",
                    "safari": "Safari",
                    "vscode": "Visual Studio Code",
                    "code": "Visual Studio Code",
                    "terminal": "Terminal",
                    "finder": "Finder",
                    "mail": "Mail",
                    "calendar": "Calendar",
                    "notes": "Notes",
                    "calculator": "Calculator",
                    "slack": "Slack",
                    "discord": "Discord",
                    "zoom": "zoom.us",
                    "teams": "Microsoft Teams"
                }
                
                actual_name = common_apps.get(app_name.lower(), app_name)
                result = subprocess.run(
                    ["open", "-a", actual_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    return f"✅ Successfully launched {actual_name}"
                else:
                    return f"❌ Could not find or launch application: {app_name}. Make sure it's installed."
        
        elif system == "Linux":
            # Use xdg-open or direct command
            commands_to_try = [
                ["xdg-open", app_name],
                [app_name.lower()],
                [app_name]
            ]
            
            for cmd in commands_to_try:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        return f"✅ Successfully launched {app_name}"
                except:
                    continue
            
            return f"❌ Could not find or launch application: {app_name}"
        
        elif system == "Windows":
            # Use start command
            result = subprocess.run(
                ["start", "", app_name],
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return f"✅ Successfully launched {app_name}"
            else:
                return f"❌ Could not find or launch application: {app_name}"
        
        else:
            return f"❌ Unsupported operating system: {system}"
            
    except subprocess.TimeoutExpired:
        return f"❌ Timeout while trying to launch {app_name}"
    except Exception as e:
        return f"❌ Error launching application: {str(e)}"

# Create the Langchain tool
app_launcher_tool = StructuredTool.from_function(
    name="launch_application",
    description="Launch installed applications like Spotify, Chrome, VSCode, etc. Just provide the app name.",
    func=launch_application,
    args_schema=AppLauncherInput
)