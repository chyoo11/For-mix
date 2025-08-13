#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safe All-In-One CLI Scaffold (5 tools)

This is a modern, extensible CLI with:
- Rich styling
- Interactive menu or direct subcommands
- Plugin hooks for your own implementations

The five built-in commands are placeholders:
1) nickname
2) profile-views
3) views
4) copylink
5) like

Replace the placeholder functions with your own compliant logic, or add plugins in `plugins/`.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, Dict

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

APP = typer.Typer(add_completion=False, help="All-In-One CLI scaffold with five tools and plugin hooks.")
CONSOLE = Console()

BANNER = """
[bold dodger_blue1]
░█████╗░██╗░░██╗██╗░░░██╗░█████╗░
██╔══██╗██║░░██║╚██╗░██╔╝██╔══██╗
██║░░╚═╝███████║░╚████╔╝░██║░░██║
██║░░██╗██╔══██║░░╚██╔╝░░██║░░██║
╚█████╔╝██║░░██║░░░██║░░░╚█████╔╝
░╚════╝░╚═╝░░╚═╝░░░╚═╝░░░░╚════╝░[/]
[dim]All-In-One Toolkit (safe scaffold)[/]
"""

SEPARATOR = "[dim]" + "~" * 64 + "[/]"


@dataclass
class Settings:
    sessions_file: Optional[Path] = None
    theme: str = "default"

    @staticmethod
    def load(config_path: Path = Path("config.yaml")) -> "Settings":
        if yaml is None or not config_path.exists():
            return Settings()
        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            return Settings(
                sessions_file=Path(data.get("sessions_file")) if data.get("sessions_file") else None,
                theme=str(data.get("theme", "default")),
            )
        except Exception:
            return Settings()


SETTINGS = Settings.load()


def _demo_activity(label: str, seconds: float = 1.2) -> None:
    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=CONSOLE,
    ) as progress:
        task = progress.add_task(f"{label}…", total=None)
        time.sleep(seconds)
        progress.remove_task(task)


def _show_header() -> None:
    CONSOLE.print(Panel.fit(BANNER, border_style="cyan"))


def _show_menu() -> None:
    table = Table(title="Select a tool", title_style="bold cyan", show_header=False, box=None)
    table.add_row("[bold green]1[/]", "Nickname (placeholder)")
    table.add_row("[bold green]2[/]", "Profile Views (placeholder)")
    table.add_row("[bold green]3[/]", "Views (placeholder)")
    table.add_row("[bold green]4[/]", "CopyLink (placeholder)")
    table.add_row("[bold green]5[/]", "Like (placeholder)")
    table.add_row("[bold yellow]Q[/]", "Quit")
    CONSOLE.print(table)


# ---------------------------------------------------------------------------
# Placeholder tool implementations
# ---------------------------------------------------------------------------

def _placeholder_impl(name: str, **kwargs) -> None:
    _demo_activity(f"Preparing {name}")
    CONSOLE.print(Panel.fit(
        f"[bold]{name}[/]\n\nThis is a placeholder.\n\n"
        "- Add your compliant implementation in this function, or\n"
        "- Register a plugin in the [bold]plugins/[/] folder to override it.",
        border_style="magenta"
    ))


# Mapping for interactive menu
MENU_ACTIONS: Dict[str, Callable[[], None]] = {}


def _register_menu_item(key: str, fn: Callable[[], None]) -> None:
    MENU_ACTIONS[key.lower()] = fn


# Tool 1: nickname
@APP.command("nickname")
def nickname_command(
    target: str = typer.Option(None, "--target", help="Target identifier (placeholder input)."),
    new_value: str = typer.Option(None, "--new", help="New value (placeholder input)."),
    sessions_file: Optional[Path] = typer.Option(None, "--sessions", help="Path to sessions file (optional placeholder)."),
) -> None:
    _placeholder_impl("Nickname", target=target, new_value=new_value, sessions_file=sessions_file)


# Tool 2: profile-views
@APP.command("profile-views")
def profile_views_command(
    username: str = typer.Option(None, "--username", help="Username (placeholder input)."),
    sessions_file: Optional[Path] = typer.Option(None, "--sessions", help="Path to sessions file (optional placeholder)."),
) -> None:
    _placeholder_impl("Profile Views", username=username, sessions_file=sessions_file)


# Tool 3: views
@APP.command("views")
def views_command(
    item: str = typer.Option(None, "--item", help="Item/video identifier or URL (placeholder)."),
    sessions_file: Optional[Path] = typer.Option(None, "--sessions", help="Path to sessions file (optional placeholder)."),
) -> None:
    _placeholder_impl("Views", item=item, sessions_file=sessions_file)


# Tool 4: copylink
@APP.command("copylink")
def copylink_command(
    item: str = typer.Option(None, "--item", help="Item/video identifier or URL (placeholder)."),
    sessions_file: Optional[Path] = typer.Option(None, "--sessions", help="Path to sessions file (optional placeholder)."),
) -> None:
    _placeholder_impl("CopyLink", item=item, sessions_file=sessions_file)


# Tool 5: like
@APP.command("like")
def like_command(
    item: str = typer.Option(None, "--item", help="Item/video identifier or URL (placeholder)."),
    sessions_file: Optional[Path] = typer.Option(None, "--sessions", help="Path to sessions file (optional placeholder)."),
) -> None:
    _placeholder_impl("Like", item=item, sessions_file=sessions_file)


# ---------------------------------------------------------------------------
# Plugin system (safe, generic)
# ---------------------------------------------------------------------------

def load_plugins() -> None:
    """Dynamically load plugins in ./plugins that can register/override commands.

    A plugin can define a function `register(app: typer.Typer, menu: dict, console: Console) -> None`
    and register new commands or replace MENU_ACTIONS.
    """
    plugins_dir = Path(__file__).parent / "plugins"
    if not plugins_dir.exists() or not plugins_dir.is_dir():
        return

    sys.path.insert(0, str(plugins_dir))
    for py in plugins_dir.glob("*.py"):
        mod_name = py.stem
        try:
            mod = __import__(mod_name)
            if hasattr(mod, "register"):
                mod.register(APP, MENU_ACTIONS, CONSOLE)
        except Exception as exc:  # pragma: no cover
            CONSOLE.print(Panel.fit(f"Plugin '{mod_name}' failed to load: {exc}", border_style="red"))


# ---------------------------------------------------------------------------
# Interactive entrypoint
# ---------------------------------------------------------------------------

def interactive_menu() -> None:
    _show_header()
    _show_menu()

    # Register built-in menu items
    _register_menu_item("1", lambda: nickname_command())
    _register_menu_item("2", lambda: profile_views_command())
    _register_menu_item("3", lambda: views_command())
    _register_menu_item("4", lambda: copylink_command())
    _register_menu_item("5", lambda: like_command())

    while True:
        choice = Prompt.ask("[bold yellow]Enter choice[/]", default="Q")
        if choice.lower() in {"q", "quit", "exit"}:
            CONSOLE.print("[green]Goodbye![/]")
            break
        action = MENU_ACTIONS.get(choice.lower())
        if not action:
            CONSOLE.print("[red]Invalid choice[/]")
            continue
        action()
        CONSOLE.print(SEPARATOR)
        if not Confirm.ask("Run another tool?", default=True):
            break


def main() -> None:
    # Load plugins before CLI execution
    load_plugins()

    # If invoked without subcommands, show interactive menu
    if len(sys.argv) == 1:
        interactive_menu()
    else:
        APP()


if __name__ == "__main__":
    main()