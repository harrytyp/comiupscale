"""
UI — Monkey Island 3 themed terminal UI.

Colour palette inspired by the game's opening screen:
  gold    #D4A017  — headings, highlights
  amber   #C47A1A  — secondary
  wood    #8B5E3C  — borders, panels
  sea     #2E6B5E  — accents, progress bars
  red     #A02020  — errors, warnings
  cream   #F5E6C8  — body text
  dark    #1A1410  — background
"""

import sys
import random

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    TimeRemainingColumn, TimeElapsedColumn, TaskID,
)
from rich.table import Table
from rich.text import Text
from rich.style import Style
from rich.align import Align
from rich.prompt import Prompt, Confirm
from rich.columns import Columns
from rich.syntax import Syntax

# ── Colour palette ───────────────────────────────────
GOLD = "#D4A017"
AMBER = "#C47A1A"
WOOD = "#8B5E3C"
SEA = "#2E6B5E"
RED = "#A02020"
CREAM = "#F5E6C8"
DARK = "#1A1410"
WHITE = "#FFFFFF"

console = Console(highlight=False)

# ── MI3 flavour text pool ────────────────────────────
INSULTS = [
    "You fight like a dairy farmer!",
    "How appropriate. You fight like a cow.",
    "I've spoken with maps more interesting than you.",
    "I've got a hangnail that's tougher than you.",
    "You're the weakest pirate I've ever heard of.",
    "You're as useful as a screen door on a submarine.",
    "I've seen faster snails at a salt lick.",
    "You're as sharp as a sack of wet mice.",
    "You have the manners of a goat.",
    "You're about as stealthy as a stampeding elephant.",
]

ENCOURAGEMENTS = [
    "A pirate's life for thee!",
    "Dead men tell no tales, but this progress bar does.",
    "Arr, that's a fine bit of upscaling!",
    "Shiver me timbers, that's progress!",
    "Three-headed monkey approves.",
    "Another treasure for the pile!",
    "Yo ho ho and a bottle of... pixels!",
    "LeChuck's beard is tingling with anticipation.",
    "Elaine would be impressed.",
    "Guybrush would say 'I'm not scared of you!'",
    "The SCUMM bar is open for business.",
    "This is the way of the pirate king.",
]

ERROR_QUIPS = [
    "Blimey! That's not right.",
    "Even Guybrush could do better than this.",
    "A monkey could've fixed that.",
    "The voodoo lady didn't see that coming.",
    "That's almost as bad as LeChuck's fashion sense.",
]

DONE_MESSAGES = [
    "You've completed the insult sword fighting! Now go find Elaine.",
    "Another successful raid on the pixel seas!",
    "The Secret of Monkey Island… upscaled!",
    "The Curse of the HD Monkey Island is complete!",
    "Guybrush would be proud. Maybe even Elaine.",
]


# ── ASCII Art ────────────────────────────────────────

def _render_logo():
    """Generate the splash logo — COMI + UPSCALED in figlet 'big' font."""
    import pyfiglet
    lines_comi = pyfiglet.figlet_format("COMI", font="big").splitlines()
    lines_up = pyfiglet.figlet_format("UPSCALED", font="big").splitlines()
    lines_m3 = pyfiglet.figlet_format("MONKEY 3", font="big").splitlines()
    # Pad to same height
    h = max(len(lines_comi), len(lines_up), len(lines_m3))
    for lst in [lines_comi, lines_up, lines_m3]:
        while len(lst) < h:
            lst.append(" " * (len(lst[0]) if lst else 0))
    # Side-by-side with spacing
    result = []
    for i in range(h):
        line = f"[gold]{lines_comi[i]:<28} {lines_up[i]:<40} {lines_m3[i]}[/]"
        result.append(line)
    return "\n".join(result)


LOGO = _render_logo()

MURRAY = r"""[sea]              ░░░░░
            ░▒▒▒▒▒▒▒░
         ░░▒▒▒▒▒▒▒▒▒▒░
       ░▒▒▒▒▒▒▒▒▒▒▒▒▒▒░
     ░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░
   ░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░
  ░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░
  ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
 ░▒▒▒▒▒▒▒▒▒▒░░░░▒▒▒▒▒▒▒▒░░░▒░
 ▒▒▒▒▒▒▒▒▒▒▒░    ▒▒▒▒▒▒░  ░▒░
 ▒▒▒▒▒▒▒▒▒▒░      ░▒▒░    ░▒
░▒▒▒▒▒▒▒▒▒▒░      ░▒▒░    ░
░▒▒▒▒▒▒▒▒▒▒░      ░▒▒░
 ░▒▒▒▒▒░░▒▒░      ▒░░░        [gold]I'm back![/]
   ▒▒▒▒░░▒▒░     ░▒░  ░░░░░
   ░▒▒▒░░▒▒▒░░░░░▒░   ░▒▒▒▒░
        ░▒▒▒▒▒▒▒▒▒▒░▒░▒▒▒▒▒▒
        ░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░
         ░▒▒░░░░▒▒▒▒▒▒▒▒▒
                 ░░░░░░░░
         ░░░░    ░░░░░░░░
         ▒▒░
         ░▒░     ░    ░
         ▒▒▒░  ░░░░░░░░░░░
         ▒▒▒▒░░▒░░░░░░░░░░░░
         ░░▒▒░░▒▒▒░▒▒▒▒▒▒▒░░
                   ░░░░░░░[/]"""

TAGLINE = "[sea italic]You must gather your pixels before venturing forth...[/]"

THREE_HEADED_MONKEY = r"""
[amber]                   .---.
                  /     \
     .---.       /       \       .---.
    /     \     /         \     /     \
   /   o   \   /   o   o   \   /   o   \
   |   |   |   |   |   |   |   |   |   |
   |  _|_  |   |  _|_ _|_  |   |  _|_  |
   |       |   |           |   |       |
   |       |   |           |   |       |
   |_______|   |___________|   |_______|
[/]"""


# ── UI Functions ─────────────────────────────────────

def title_screen():
    """Display the splash screen — call once at startup."""
    console.clear()
    console.print()
    console.print(Align.center(Text(LOGO, no_wrap=True)))
    console.print()
    console.print(Align.center(Text(TAGLINE, style="italic")))
    console.print()
    console.print(Align.center(Text(MURRAY, no_wrap=True)))
    console.print()


def panel(title, content, style=GOLD, border_style=WOOD):
    """Render a panel with MI3-styled border."""
    panel = Panel(
        Text(content) if isinstance(content, str) else content,
        title=title,
        title_align="left",
        border_style=border_style,
        padding=(1, 2),
    )
    console.print(panel)


def section(title):
    """Print a section header."""
    console.print()
    console.print(Text(f"  ═══ {title} ═══", style=f"bold {GOLD}"))


def progress_bar(description, total, transient=False) -> Progress:
    """Create a themed progress bar."""
    return Progress(
        TextColumn(f"[bold {GOLD}]{description}[/]"),
        BarColumn(bar_width=None, style=SEA, complete_style=GOLD, finished_style=SEA),
        TextColumn(f"[{CREAM}]{'{task.percentage:>3.0f}%'}[/]"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=transient,
    )


def quip():
    """Print a random pirate quip."""
    q = random.choice(ENCOURAGEMENTS)
    console.print(Text(f"  ☠  {q}", style=f"italic {AMBER}"))


def insult():
    """Print a random insult (for errors/warnings)."""
    i = random.choice(INSULTS)
    console.print(Text(f"  ⚔  {i}", style=f"bold {RED}"))


def show_murray():
    """Print Murray the Demonic Skull."""
    console.print()
    console.print(Align.center(Text(MURRAY, no_wrap=True)))
    console.print()

def done_message():
    """Print a random completion message."""
    d = random.choice(DONE_MESSAGES)
    console.print()
    console.print(Align.center(Text(f"  🏴  {d}  🏴", style=f"bold {GOLD}")))
    show_murray()


def header(text):
    """Page header with gold bar."""
    console.print()
    console.print(Text(f"  {'─' * 50}", style=WOOD))
    console.print(Text(f"  {text}", style=f"bold {GOLD}"))


def ask(text, default=None):
    """Prompt user for input with pirate styling."""
    return Prompt.ask(f"  [{GOLD}]☠[/] {text}", default=default)


def confirm(text, default=True) -> bool:
    """Yes/no confirmation."""
    return Confirm.ask(f"  [{GOLD}]☠[/] {text}", default=default)


def info(text):
    console.print(f"  [{SEA}]*[/] {text}")


def success(text):
    console.print(f"  [{GOLD}]✓[/] {text}")


def warn(text):
    console.print(f"  [{AMBER}]![/] {text}")


def error(text):
    console.print(f"  [{RED}]✗[/] {text}")


def summary_table(items: dict):
    """Render a summary table of key=value pairs."""
    table = Table(box=None, show_header=False, border_style=WOOD)
    table.add_column("Item", style=f"bold {CREAM}")
    table.add_column("Status", style=GOLD)
    for k, v in items.items():
        table.add_row(f"  {k}", str(v))
    console.print(Panel(table, border_style=WOOD, padding=(1, 2)))


def show_monkey():
    """Print the three-headed monkey ASCII."""
    console.print(Align.center(Text(THREE_HEADED_MONKEY, no_wrap=True)))
