import json
import click
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.tree import Tree
from rich.text import Text

console = Console()

class HelpTreeHandler:
    """
    Implements the HelpTree protocol for CLI introspection.
    Supports sub-path targeting and refined ANSI rendering.
    """

    TREE_ALIGN_WIDTH = 28
    MIN_DOTS = 4

    def __init__(self, cli_group: click.Group):
        self.cli_group = cli_group

    def generate_map(self, ctx: click.Context) -> Dict[str, Any]:
        """Recursively build the full command map."""
        return self._process_command(self.cli_group, ctx, prog_name="code-index")

    def _process_command(self, cmd: click.Command, ctx: click.Context, prog_name: str) -> Dict[str, Any]:
        name = cmd.name or prog_name
        params_suffix = ""
        options = []
        arguments = []
        
        for param in cmd.get_params(ctx):
            if isinstance(param, click.Option):
                options.append(param)
            else:
                arguments.append(param)
                if param.required:
                    params_suffix += f" <{param.name.upper()}>"
                else:
                    params_suffix += f" [{param.name.upper()}]"
        
        if options:
            params_suffix += " [flags]"

        cmd_info = {
            "name": name,
            "signature": f"{name}{params_suffix}",
            "help": cmd.help or "",
            "params": []
        }

        for param in cmd.get_params(ctx):
            param_info = {
                "name": param.name,
                "opts": param.opts,
                "help": getattr(param, 'help', '') or "",
                "type": str(param.type),
                "is_option": isinstance(param, click.Option)
            }
            cmd_info["params"].append(param_info)

        if isinstance(cmd, click.Group):
            cmd_info["commands"] = []
            for sub_name in sorted(cmd.list_commands(ctx)):
                sub_cmd = cmd.get_command(ctx, sub_name)
                if sub_cmd:
                    cmd_info["commands"].append(self._process_command(sub_cmd, ctx, sub_name))

        return cmd_info

    def _select_sub_map(self, cmd_map: Dict[str, Any], path: List[str]) -> Dict[str, Any]:
        """Navigate to a specific subcommand path within the map."""
        current = cmd_map
        for part in path:
            found = False
            for sub in current.get("commands", []):
                if sub["name"] == part:
                    current = sub
                    found = True
                    break
            if not found:
                break
        return current

    def render_ansi(self, cmd_map: Dict[str, Any], path: Optional[List[str]] = None):
        """Render the command map (or sub-map) in ANSI style."""
        target_map = self._select_sub_map(cmd_map, path or [])
        
        # Header
        console.print(f"[bold #7ee7e6]{target_map['name']}[/bold #7ee7e6]")
        
        # Options for the current level
        for param in target_map.get("params", []):
            if param["is_option"]:
                opts_str = ", ".join(param["opts"])
                help_text = param["help"].split('.')[0] if param["help"] else ""
                console.print(f"  [#7ee7e6]{opts_str}[/#7ee7e6] [dim]…[/dim] [italic #90a2af]{help_text}[/italic #90a2af]")
        
        console.print("")
        
        # Sub-tree
        self._write_rich_tree(target_map, "")
        
        console.print(f"\nUse `code-index {' '.join(path or [])} <COMMAND> --help` for full details.")

    def _write_rich_tree(self, cmd_info: Dict[str, Any], prefix: str):
        subcommands = cmd_info.get("commands", [])
        if not subcommands:
            return

        for idx, sub_cmd in enumerate(subcommands):
            is_last = idx + 1 == len(subcommands)
            branch = "└── " if is_last else "├── "
            
            sig = sub_cmd["signature"]
            help_summary = sub_cmd['help'].split('.')[0] if sub_cmd['help'] else ""
            
            name_part = sub_cmd["name"]
            params_part = sub_cmd["signature"][len(name_part):]
            
            styled_sig = Text()
            styled_sig.append(name_part, style="bold #7ee7e6")
            styled_sig.append(params_part, style="normal")
            
            if help_summary:
                dot_count = max(self.MIN_DOTS, self.TREE_ALIGN_WIDTH - len(sig))
                dots = "." * dot_count
                
                line = Text(prefix + branch)
                line.append(styled_sig)
                line.append(f" {dots} ", style="dim")
                line.append(help_summary, style="italic #90a2af")
            else:
                line = Text(prefix + branch)
                line.append(styled_sig)
            
            console.print(line)

            extension = "    " if is_last else "│   "
            self._write_rich_tree(sub_cmd, prefix + extension)

    def render_json(self, cmd_map: Dict[str, Any], path: Optional[List[str]] = None):
        """Render the command map (or sub-map) as raw JSON."""
        target_map = self._select_sub_map(cmd_map, path or [])
        print(json.dumps(target_map, indent=2))
