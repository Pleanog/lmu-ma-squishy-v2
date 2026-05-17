# # tools/squishy_tools.py
# from google.genai import types

# SET_LED_TOOL = types.Tool(
#     function_declarations=[
#         types.FunctionDeclaration(
#             name="set_led_color",
#             description="Sets the color of Squishy's LEDs.",
#             parameters=types.Schema(
#                 type="OBJECT",
#                 properties={
#                     "color": types.Schema(type="STRING", description="The color name (e.g., red, blue, green, happy_yellow).")
#                 },
#                 required=["color"]
#             ),
#             behavior="NON_BLOCKING"
#         )
#     ]
# )

# PLAY_SOUND_TOOL = types.Tool(
#     function_declarations=[
#         types.FunctionDeclaration(
#             name="play_squishy_sound",
#             description="Plays a specific sound from Squishy's internal speaker.",
#             parameters=types.Schema(
#                 type="OBJECT",
#                 properties={
#                     "sound_type": types.Schema(
#                         type="STRING",
#                         description="The type of sound to play (e.g., happy_chime, confused_buzz, frustrated_growl)."
#                     )
#                 },
#                 required=["sound_type"]
#             )
#         )
#     ]
# )

# squishy_tools = [
#     SET_LED_TOOL,
#     PLAY_SOUND_TOOL
# ]


# FILE: app/tools/squishy_tools.py

# This file remains largely the same, but it's now imported by app/gemini/tools.py
# The definition of the tools themselves (their schemas) are here.
# The `app/gemini/tools.py` then aggregates and provides them to GeminiLive.

from google.genai import types

# Define the tools that Gemini can call for Squishy.
# These are the actual tool schemas that Gemini will use to understand available actions.

squishy_tools = [
    types.Tool(
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
    ),
    types.Tool(
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
    ),
    types.Tool(
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
]