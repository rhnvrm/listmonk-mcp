"""Generate the reference from public MCP registrations; no credentials needed."""

import asyncio
from pathlib import Path

from listmonk_mcp.server import mcp


async def main() -> None:
    tools = await mcp.list_tools()
    resources = await mcp.list_resources()
    templates = await mcp.list_resource_templates()
    lines = [
        "# Tools and resources",
        "",
        f"v0.2.0 registers **{len(tools)} tools**, **{len(resources)} resources**, and **{len(templates)} resource templates**.",
        "",
        "This reference is generated from the registered MCP schemas. Tools are available only to the extent permitted by the configured Listmonk API user. Sends, imports, settings changes, and maintenance take effect on that instance.",
        "",
        "## Tools",
        "",
    ]
    for tool in tools:
        schema = tool.inputSchema
        required = set(schema.get("required", []))
        lines += [f"### `{tool.name}`", "", tool.description or "", ""]
        for name, prop in schema.get("properties", {}).items():
            default = f"; default `{prop['default']}`" if "default" in prop else ""
            lines.append(
                f"- `{name}`: {'required' if name in required else 'optional'}{default}"
            )
        lines.append("")
    lines += ["## Resources", ""]
    lines += [
        f"- `{resource.uri}` — {resource.description or resource.name}"
        for resource in resources
    ]
    lines += ["", "## Resource templates", ""]
    lines += [
        f"- `{template.uriTemplate}` — {template.description or template.name}"
        for template in templates
    ]
    Path("docs/tools.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
