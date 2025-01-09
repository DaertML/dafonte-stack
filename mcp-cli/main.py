import argparse
import logging
import sys
import anyio
import asyncio
import os
import json
import signal
from config import load_config
from messages.tools import send_call_tool, send_tools_list
from messages.resources import send_resources_list
from messages.prompts import send_prompts_list
from messages.send_initialize_message import send_initialize
from messages.ping import send_ping
from chat_handler import handle_chat_mode
from transport.stdio.stdio_client import stdio_client

# Rich imports
from rich import print
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

# Default path for the configuration file
DEFAULT_CONFIG_FILE = "server_config.json"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

def signal_handler(sig, frame):
    # Ignore subsequent SIGINT signals
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    # pretty exit
    print("\n[bold red]Goodbye![/bold red]")

    # Immediately and forcibly kill the process
    os.kill(os.getpid(), signal.SIGKILL)

# signal handler
signal.signal(signal.SIGINT, signal_handler)

async def handle_command(command: str, read_stream, write_stream):
    """Handle specific commands dynamically."""
    try:
        if command == "ping":
            print("[cyan]\nPinging Server...[/cyan]")
            result = await send_ping(read_stream, write_stream)
            if result:
                ping_md = "## Ping Result\n\n✅ **Server is up and running**"
                print(Panel(Markdown(ping_md), style="bold green"))
            else:
                ping_md = "## Ping Result\n\n❌ **Server ping failed**"
                print(Panel(Markdown(ping_md), style="bold red"))

        elif command == "list-tools":
            print("[cyan]\nFetching Tools List...[/cyan]")
            response = await send_tools_list(read_stream, write_stream)
            tools_list = response.get("tools", [])
            if not tools_list:
                tools_md = "## Tools List\n\nNo tools available."
            else:
                tools_md = "## Tools List\n\n" + "\n".join(
                    [f"- **{t.get('name')}**: {t.get('description', 'No description')}" for t in tools_list]
                )
            print(Panel(Markdown(tools_md), title="Tools", style="bold cyan"))

        elif command == "call-tool":
            tool_name = Prompt.ask("[bold magenta]Enter tool name[/bold magenta]").strip()
            if not tool_name:
                print("[red]Tool name cannot be empty.[/red]")
                return True

            arguments_str = Prompt.ask("[bold magenta]Enter tool arguments as JSON (e.g., {'key': 'value'})[/bold magenta]").strip()
            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError as e:
                print(f"[red]Invalid JSON arguments format:[/red] {e}")
                return True

            print(f"[cyan]\nCalling tool '{tool_name}' with arguments:\n[/cyan]")
            print(Panel(Markdown(f"```json\n{json.dumps(arguments, indent=2)}\n```"), style="dim"))

            result = await send_call_tool(tool_name, arguments, read_stream, write_stream)
            if result.get("isError"):
                print(f"[red]Error calling tool:[/red] {result.get('error')}")
            else:
                response_content = result.get('content', 'No content')
                print(Panel(Markdown(f"### Tool Response\n\n{response_content}"), style="green"))

        elif command == "list-resources":
            print("[cyan]\nFetching Resources List...[/cyan]")
            response = await send_resources_list(read_stream, write_stream)
            resources_list = response.get("resources", [])
            if not resources_list:
                resources_md = "## Resources List\n\nNo resources available."
            else:
                resources_md = "## Resources List\n"
                for r in resources_list:
                    if isinstance(r, dict):
                        json_str = json.dumps(r, indent=2)
                        resources_md += f"\n```json\n{json_str}\n```"
                    else:
                        resources_md += f"\n- {r}"
            print(Panel(Markdown(resources_md), title="Resources", style="bold cyan"))

        elif command == "list-prompts":
            print("[cyan]\nFetching Prompts List...[/cyan]")
            response = await send_prompts_list(read_stream, write_stream)
            prompts_list = response.get("prompts", [])
            if not prompts_list:
                prompts_md = "## Prompts List\n\nNo prompts available."
            else:
                prompts_md = "## Prompts List\n\n" + "\n".join([f"- {p}" for p in prompts_list])
            print(Panel(Markdown(prompts_md), title="Prompts", style="bold cyan"))

        elif command == "chat":
            provider = os.getenv("LLM_PROVIDER", "openai")
            model = os.getenv("LLM_MODEL", "gpt-4o-mini")

            # Clear the screen first
            if sys.platform == "win32":
                os.system("cls")
            else:
                os.system("clear")

            chat_info_text = (
                "Welcome to the Chat!\n\n"
                f"**Provider:** {provider}  |  **Model:** {model}\n\n"
                "Type 'exit' to quit."
            )

            print(Panel(Markdown(chat_info_text), style="bold cyan", title="Chat Mode", title_align="center"))
            await handle_chat_mode(read_stream, write_stream, provider, model)

        elif command in ["quit", "exit"]:
            print("\n[bold red]Goodbye![/bold red]")
            return False

        elif command == "clear":
            if sys.platform == "win32":
                os.system("cls")
            else:
                os.system("clear")

        elif command == "help":
            help_md = """
# Available Commands

- **ping**: Check if server is responsive
- **list-tools**: Display available tools
- **list-resources**: Display available resources
- **list-prompts**: Display available prompts
- **chat**: Enter chat mode
- **clear**: Clear the screen
- **help**: Show this help message
- **quit/exit**: Exit the program

**Note:** Commands use dashes (e.g., `list-tools` not `list tools`).
"""
            print(Panel(Markdown(help_md), style="yellow"))

        else:
            print(f"[red]\nUnknown command: {command}[/red]")
            print("[yellow]Type 'help' for available commands[/yellow]")
    except Exception as e:
        print(f"\n[red]Error executing command:[/red] {e}")

    return True


async def get_input():
    """Get input asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input().strip().lower())


async def interactive_mode(read_stream, write_stream):
    """Run the CLI in interactive mode."""
    welcome_text = """
# Welcome to the Interactive MCP Command-Line Tool

Type 'help' for available commands or 'quit' to exit.
"""
    print(Panel(Markdown(welcome_text), style="bold cyan"))

    while True:
        try:
            command = Prompt.ask("[bold green]\n>[/bold green]").strip().lower()
            if not command:
                continue
            should_continue = await handle_command(command, read_stream, write_stream)
            if not should_continue:
                return
        except EOFError:
            break
        except Exception as e:
            print(f"\n[red]Error:[/red] {e}")


class GracefulExit(Exception):
    """Custom exception for handling graceful exits."""
    pass


async def main(config_path: str, server_name: str, command: str = None) -> None:
    """Main function to manage server initialization, communication, and shutdown."""
    # Clear screen before rendering anything
    if sys.platform == "win32":
        os.system("cls")
    else:
        os.system("clear")

    # Load server configuration
    server_params = await load_config(config_path, server_name)

    # Establish stdio communication
    async with stdio_client(server_params) as (read_stream, write_stream):
        # Initialize the server
        init_result = await send_initialize(read_stream, write_stream)
        if not init_result:
            print("[red]Server initialization failed[/red]")
            return

        if command:
            # Single command mode
            await handle_command(command, read_stream, write_stream)
        else:
            # Interactive mode
            await interactive_mode(read_stream, write_stream)

        loop = asyncio.get_event_loop()
        
        # Try closing streams with a timeout
        with anyio.move_on_after(1):  # wait up to 1 second
            await read_stream.aclose()
            await write_stream.aclose()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Command-Line Tool")

    parser.add_argument(
        "--config-file",
        default=DEFAULT_CONFIG_FILE,
        help="Path to the JSON configuration file containing server details.",
    )

    parser.add_argument(
        "--server",
        required=True,
        help="Name of the server configuration to use from the config file.",
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["ping", "list-tools", "list-resources", "list-prompts"],
        help="Command to execute (optional - if not provided, enters interactive mode).",
    )

    parser.add_argument(
        "--provider",
        choices=["openai", "ollama"],
        default="openai",
        help="LLM provider to use. Defaults to 'openai'.",
    )

    parser.add_argument(
        "--model",
        help=(
            "Model to use. Defaults to 'gpt-4o-mini' for 'openai' and 'qwen2.5-coder' for 'ollama'."
        ),
    )

    args = parser.parse_args()

    model = args.model or ("gpt-4o-mini" if args.provider == "openai" else "qwen2.5-coder")
    os.environ["LLM_PROVIDER"] = args.provider
    os.environ["LLM_MODEL"] = model

    try:
        result = anyio.run(main, args.config_file, args.server, args.command)
        sys.exit(result)
    except Exception as e:
        print(f"[red]Error occurred:[/red] {e}")
        sys.exit(1)
