import urllib.request
import json

import logging
from pathlib import Path
from typing import Sequence
from mcp.server import Server
from mcp.server.session import ServerSession
from mcp.server.stdio import stdio_server
from mcp.types import (
    ClientCapabilities,
    TextContent,
    Tool,
    ListRootsResult,
    RootsCapability,
)
#import requests
from enum import Enum
import git
from pydantic import BaseModel

token = "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImFsYmVmdWVuIiwicm9sZXMiOltdLCJlbWFpbCI6ImFsYmVmdWVuQGdtYWlsLmNvbSIsImlzQm90IjpmYWxzZSwidG9rZW5UeXBlIjoiUEVSU09OQUxfQUNDRVNTIiwiaWF0IjoxNzM0MDEyNTA1LCJleHAiOjE3NDE3ODg1MDV9.JTKsg6xSMkjgKcEkWJk8LwP6A6E1Usoa6fu82wioCx2vB0l6v0KDigxzCgP1zc3VFAHbD5wqIr7rV3BUW1fwon4aMpmfMFYlMq3oZ1P9uHQJci4uS6T_oLlq8nUWbT3pZn_oMP_xyw_rleTX9bK3V3CbNCMKkh4-De5O8VWUqdt1VAPaUSBW22_3CBtR7NtKDjlruBQ82m6v4XVXIP8aH-_CXHhKRJEeKJR-uIP2HFHnoFosFuuaXRolVWkpq4SU64Yh-IzpCR5Msoapdq9RhpC7Apb2zn2ADp7fyxRRQs2uBu7RenB1jwSuXOzc5WiGBa9MDjEWco7rVV7WpIhGjA"

class GetDatabases(BaseModel):
    dbname: str
    fullname: str
    description: str
    version: str
    servicetype: str



async def serve(servicetype: str | None) -> None:
    logger = logging.getLogger(__name__)

    if servicetype is not None:
        try:
            logger.info(f"Looking for weather of {servicetype}")
        except:
            logger.error(f"{servicetype} is not a valid name")
            return

    server = Server("mcp-git")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="GetDatabases",
                description="Shows the DB list",
                inputSchema=GetDatabases.schema(),
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        serviceType = arguments["servicetype"]

        match serviceType:
            case "Databases":

                headers = {"Authorization": "Bearer " + token}
                url = "http://localhost:8585/api/v1/databases"
                request = urllib.request.Request(url, headers=headers)

                with urllib.request.urlopen(request) as response:
                  res = response.read().decode('utf-8')

                json_response = json.loads(res)

                return [TextContent(
                    type="text",
                    text=f"These are the databases: {json_response}."
                )]

            case "Tables":
                headers = {"Authorization": "Bearer " + token}
                url = "http://localhost:8585/api/v1/tables"
                request = urllib.request.Request(url, headers=headers)

                with urllib.request.urlopen(request) as response:
                  res = response.read().decode('utf-8')

                json_response = json.loads(res)

                return [TextContent(
                    type="text",
                    text=f"These are the tables: {json_response}."
                )]

            case _:
                raise ValueError(f"Unknown tool: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
