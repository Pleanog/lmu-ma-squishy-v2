# tools/squishy_tools.py
from google.genai import types

SET_LED_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="set_led_color",
            description="Sets the color of Squishy's LEDs.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "color": types.Schema(type="STRING", description="The color name (e.g., red, blue, green, happy_yellow).")
                },
                required=["color"]
            ),
            behavior="NON_BLOCKING"
        )
    ]
)

PLAY_SOUND_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="play_squishy_sound",
            description="Plays a specific sound from Squishy's internal speaker.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "sound_type": types.Schema(
                        type="STRING",
                        description="The type of sound to play (e.g., happy_chime, confused_buzz, frustrated_growl)."
                    )
                },
                required=["sound_type"]
            )
        )
    ]
)

squishy_tools = [
    SET_LED_TOOL,
    PLAY_SOUND_TOOL
]