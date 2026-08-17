"""
Wraps the Groq client and handles tool-calling: the LLM decides when it
needs live financial data, calls the right tool, and then uses the result
to write a natural-language answer.
"""
import json
from groq import Groq

from app.config import GROQ_API_KEY, GROQ_MODEL
from app.tools.financial_data import TOOL_DEFINITIONS, TOOL_FUNCTIONS

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are Atlas, an AI financial assistant that lives inside Telegram.
You talk like an experienced, sharp financial analyst - not a generic chatbot.

Rules:
- Be concise. Finance professionals are busy; get to the point.
- Explain WHY something matters, don't just state facts.
- When you need current prices, company data, or news, use the tools available to you.
  Never make up numbers - if you don't have real data, say so.
- If a request is ambiguous (e.g. "tell me about Apple"), ask a quick clarifying
  question instead of guessing what they want.
- Keep responses conversational, not bullet-point reports, unless the user asks
  for a structured comparison.
- Remember the context of the conversation the user has already given you.
"""


async def get_response(conversation_history: list[dict], user_context: str = "") -> str:
    """
    conversation_history: list of {"role": "user"/"assistant", "content": "..."}
    user_context: known facts about the user (role, watchlist, preferences) to personalize responses
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if user_context:
        messages.append({"role": "system", "content": f"What you know about this user: {user_context}"})
    messages.extend(conversation_history)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        tools=TOOL_DEFINITIONS,
        tool_choice="auto",
        temperature=0.4,
    )

    message = response.choices[0].message

    # If the model wants to call a tool, execute it and feed the result back
    if message.tool_calls:
        messages.append(message)
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            func = TOOL_FUNCTIONS.get(func_name)

            if func:
                result = await func(**func_args)
            else:
                result = {"error": f"Unknown tool: {func_name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": func_name,
                "content": json.dumps(result),
            })

        # Ask the model to turn the tool result into a natural answer
        final_response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.4,
        )
        return final_response.choices[0].message.content

    return message.content
  
async def transcribe_audio(file_path: str) -> str:
    """
    Transcribes a voice message to text using Groq's free Whisper endpoint.
    file_path should point to a local audio file (e.g. downloaded .ogg from Telegram).
    """
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3-turbo",
            response_format="text",
        )
    return transcription if isinstance(transcription, str) else transcription.text


async def analyze_image(image_base64: str, caption: str = "") -> str:
    """
    Sends an image to a Groq vision model for understanding (e.g. a chart,
    screenshot of a report, or company logo/photo the user shares).
    """
    user_text = caption.strip() if caption.strip() else (
        "Describe what's in this image. If it's a financial chart, table, or "
        "report screenshot, summarize the key numbers and what stands out."
    )
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    },
                ],
            }
        ],
        temperature=0.4,
    )
    return response.choices[0].message.content
