"""
Gemini Agent — MCP Client (using new google.genai SDK)
=======================================================
Setup:
    export GEMINI_API_KEY=your_key_here
    python agent.py
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()  # loads .env into environment
from google import genai
from google.genai import types
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = "http://localhost:8000/mcp"


# ── Convert MCP tools → Gemini FunctionDeclaration format ────────────────────

async def get_mcp_tools(session: ClientSession):
    mcp_tools = (await session.list_tools()).tools

    declarations = []
    for t in mcp_tools:
        properties = {
            k: types.Schema(type="NUMBER")
            for k in t.inputSchema.get("properties", {})
        }
        declarations.append(
            types.FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=types.Schema(
                    type="OBJECT",
                    properties=properties,
                    required=t.inputSchema.get("required", []),
                ),
            )
        )

    return declarations


# ── Agent loop ────────────────────────────────────────────────────────────────

async def agent(prompt: str):
    print(f"\nUser: {prompt}\n")

    async with streamablehttp_client(MCP_URL) as (read, write, *_):
        async with ClientSession(read, write) as session:
            await session.initialize()

            declarations = await get_mcp_tools(session)

            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            tools = types.Tool(function_declarations=declarations)
            config = types.GenerateContentConfig(tools=[tools])

            # Conversation history
            contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

            # ── Agentic loop ──────────────────────────────────────────────
            while True:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=config,
                )

                contents.append(response.candidates[0].content)

                tool_calls = [
                    part.function_call
                    for part in response.candidates[0].content.parts
                    if part.function_call
                ]

                if not tool_calls:
                    break  # final answer ready

                result_parts = []
                for call in tool_calls:
                    args = dict(call.args)
                    print(f"🔧 Calling {call.name}({args})")

                    mcp_result = await session.call_tool(call.name, args)
                    value = mcp_result.content[0].text
                    print(f"   → {value}\n")

                    result_parts.append(types.Part(
                        function_response=types.FunctionResponse(
                            name=call.name,
                            response={"result": value},
                        )
                    ))

                contents.append(types.Content(role="user", parts=result_parts))

            final = response.candidates[0].content.parts[0].text
            print(f"Gemini: {final}")


if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not set.")
        exit(1)

    # asyncio.run(agent("Calculate BODMA, CODMA and PRODMA for a=2, b=3 and explain the results."))
    print("Enter a prompt for the agent \n (e.g. 'Calculate BODMA, CODMA and PRODMA for a=2, b=3 and explain the results.' \n or 'What tools do you have and which are available right now?'):")
    prompt = input("Enter your prompt: ")
    asyncio.run(agent(prompt))