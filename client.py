import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv
from config_manager import ConfigManager
import subprocess

load_dotenv()


class MCPClient:
    def __init__(self):
        self.sessions: dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()

    async def connect_to_servers(self):
        mcp_servers = ConfigManager.get_servers()

        for name, server in mcp_servers.items():
            command = server["command"]
            args = server["args"]
            env = server.get("env")

            server_params = StdioServerParameters(command=command, args=args, env=env)
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport
            session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
            await session.initialize()

            response = await session.list_tools()
            for tool in response.tools:
                print(f"Loaded tool '{tool.name}' from server '{name}'")
                self.sessions[tool.name] = session

    async def process_query(self, query: str) -> str:
        messages = [{"role": "user", "content": query}]
        available_tools = []

        for session in set(self.sessions.values()):
            response = await session.list_tools()
            for tool in response.tools:
                available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })

        model = ConfigManager.get_env().get("model", "claude-3-5-sonnet-20241022")
        response = self.anthropic.messages.create(
            model=model,
            max_tokens=1000,
            messages=messages,
            tools=available_tools
        )

        final_response = []
        assistant_message_content = []

        for content in response.content:
            if content.type == 'text':
                final_response.append(content.text)
                assistant_message_content.append(content)

            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input

                if tool_name not in self.sessions:
                    raise ValueError(f"Tool '{tool_name}' is not registered.")

                result = await self.sessions[tool_name].call_tool(tool_name, tool_args)

                final_response.append(f"[Tool '{tool_name}' called with args {tool_args}]")
                assistant_message_content.append(content)

                messages.append({"role": "assistant", "content": assistant_message_content})
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": content.id,
                        "content": result.content
                    }]
                })

                response = self.anthropic.messages.create(
                    model=model,
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools
                )
                final_response.append(response.content[0].text)

        return "\n".join(final_response)

    async def chat_loop(self):
        print("\nEntering LLM Agent Chat Mode. Type 'quit' to exit.")
        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == 'quit':
                break
            try:
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\nError: {e}")

    async def cleanup(self):
        await self.exit_stack.aclose()


# ----- Menu Utilities -----

def show_environment():
    env = ConfigManager.get_env()
    print("\nCurrent Environment Configuration:")
    for key, value in env.items():
        print(f"  {key}: {value}")


def edit_environment():
    env = ConfigManager.get_env()
    print("\nEdit Environment Variables (press Enter to keep current value):")
    for key in env:
        new_val = input(f"{key} [{env[key]}]: ").strip()
        if new_val:
            env[key] = new_val
    ConfigManager.save({**ConfigManager.load(), "environment": env})
    print("Environment updated.")


def install_mcp_server():
    print("\nInstall MCP Server")
    package = input("Enter sensor name (e.g. MPU6050): ").strip()
    if package:
        subprocess.run(["pip", "install", package])
        print("Installation complete.")


# ----- Main Menu -----

async def main_menu():
    while True:
        print("\nMCP-IoT Client Main Menu")
        print("1. Show Environment Profile")
        print("2. Edit Environment Profile")
        print("3. Install MCP Server")
        print("4. Start Claude Chat Mode")
        print("5. Exit")

        choice = input("Select an option (1-5): ").strip()

        if choice == '1':
            show_environment()
        elif choice == '2':
            edit_environment()
        elif choice == '3':
            install_mcp_server()
        elif choice == '4':
            client = MCPClient()
            try:
                await client.connect_to_servers()
                await client.chat_loop()
            finally:
                await client.cleanup()
        elif choice == '5':
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please try again.")


# ----- Entry Point -----

if __name__ == "__main__":
    asyncio.run(main_menu())