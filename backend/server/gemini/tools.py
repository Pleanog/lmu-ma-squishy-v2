# FILE: app/gemini/tools.py

from google.genai import types

# Define the tools that Gemini can call
# These are the same tools from the original squishy_tools.py,
# but now part of the `gemini` module and used by the shared session.

# The schemas are what Gemini sees and uses to decide when to call a tool.

# Example: set_led_color
set_led_color_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="set_led_color",
            description="Sets the color of Squishy's LED. Can be used to indicate emotion, state, or as a visual response.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "color": types.Schema(
                        type=types.Type.STRING,
                        description="The color to set the LED. Common colors like 'red', 'green', 'blue', 'yellow', 'purple', 'white', 'off' are supported."
                    )
                },
                required=["color"]
            )
        )
    ]
)

# Example: play_squishy_sound
play_squishy_sound_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="play_squishy_sound",
            description="Plays a specific sound through Squishy's speaker. Can be used for feedback, alerts, or expressive noises.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "sound_type": types.Schema(
                        type=types.Type.STRING,
                        description="The type of sound to play. Examples: 'happy', 'sad', 'alert', 'confirm', 'error', 'chime'."
                    )
                },
                required=["sound_type"]
            )
        )
    ]
)

# Example: vibrate_squishy
vibrate_squishy_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="vibrate_squishy",
            description="Activates Squishy's vibration motor. Can be used for tactile feedback or as a physical response.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "pattern": types.Schema(
                        type=types.Type.STRING,
                        description="The vibration pattern. Examples: 'short_pulse', 'long_buzz', 'heartbeat', 'alert_vibrate'."
                    )
                },
                required=["pattern"]
            )
        )
    ]
)

# List of all available tools
SQUISHY_TOOLS = [
    set_led_color_tool,
    play_squishy_sound_tool,
    vibrate_squishy_tool,
]