import os
import readline
from langchain.agents import create_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY)

prompt = f"You are a spotify look up tool. Perform queries on a spotify hosted by the specified MCP server given the user's input. print nearly formatted output for the prompt."

async def run_agent():
    async with streamablehttp_client(f"{os.getenv('MCP_URL')}/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await load_mcp_tools(session)
            agent = create_agent(model=llm, tools=tools, system_prompt=prompt, debug=False)

            print(f"Welcome to my spotify querying agent.  The agent will query the spotify to answer queries.")

            while True:
                line = input("llm>> ")
                if line:
                    try:
                        result = await agent.ainvoke({"messages": [("user", line)]})
                        
                        if "messages" in result:
                            messages = result["messages"]
                            if messages:
                                last_message = messages[-1]
                                
                                if hasattr(last_message, 'content'):
                                    content = last_message.content
                                    
                                    # Check if content is the complex list structure from Google/Vertex
                                    if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
                                        # Extract just the 'text' field, ignoring 'extras' and 'signature'
                                        print(content[0].get("text", ""))
                                    
                                    # Check if content is just a standard string
                                    elif isinstance(content, str):
                                        print(content)
                                    
                                    # Fallback for other types
                                    else:
                                        print(content)
                                
                                else:
                                    print(f"{last_message}")
                            else:
                                print("No response from agent")
                        else:
                            print(f"Agent response: {result}")
                    except Exception as e:
                        print(f"Error: {e}")
                else:
                    break

if __name__ == "__main__":
    result = asyncio.run(run_agent())
    print(result)