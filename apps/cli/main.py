import json
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from apps.cli.client import OximoronClient
from core.contracts.errors import OximoronException

app = typer.Typer(
    name="oximoron",
    help="OXIMORON: Local-first AI orchestration CLI",
    add_completion=False,
)
console = Console()

def get_client() -> OximoronClient:
    try:
        return OximoronClient()
    except OximoronException as e:
        console.print(f"[bold red]Error:[/bold red] {e.message}")
        sys.exit(1)

@app.command("status")
def status_cmd(
    as_json: bool = typer.Option(False, "--json", help="Output summary as raw JSON"),
):
    """View compact system, supervisor, hardware, and engine status."""
    client = get_client()
    try:
        data = client.get("/status")
        if as_json:
            typer.echo(json.dumps(data, indent=2))
            return

        table = Table(title="OXIMORON Status Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Supervisor ID", str(data.get("supervisor_id", "unknown")))
        table.add_row("Status", str(data.get("status", "ok")))
        table.add_row("CPU Utilization", f"{data.get('cpu_percent', 0)}%")
        table.add_row("RAM Memory", f"{data.get('ram_used_gb', 0)} GB / {data.get('ram_total_gb', 0)} GB")
        table.add_row("GPU Available", "[bold green]Yes[/bold green]" if data.get("gpu_available") else "[yellow]No (CPU-only)[/yellow]")
        table.add_row("Active Engines", str(data.get("active_engines", 0)))
        table.add_row("Active Jobs", str(data.get("active_jobs", 0)))

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Failed to get status:[/bold red] {e}")
        sys.exit(1)

@app.command("models")
def models_cmd(
    scan: bool = typer.Option(False, "--scan", help="Trigger a scan of model directories"),
    role: Optional[str] = typer.Option(None, "--role", help="Filter by role (llm, diffusion_checkpoint, lora, etc.)"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List registered models or trigger a scan."""
    client = get_client()
    try:
        if scan:
            console.print("[yellow]Scanning configured model roots...[/yellow]")
            res = client.post("/models/scan", {})
            console.print(f"[bold green]Scan completed:[/bold green] {res.get('discovered_count', 0)} models discovered.")

        params = {}
        if role:
            params["role"] = role
        models = client.get("/models", params=params)

        if as_json:
            typer.echo(json.dumps(models, indent=2))
            return

        table = Table(title="Registered Model Library")
        table.add_column("Name", style="bold white")
        table.add_column("Role", style="cyan")
        table.add_column("Format", style="magenta")
        table.add_column("Locations", style="dim")

        for m in models:
            loc_count = len(m.get("locations", []))
            table.add_row(
                m.get("name", "unnamed"),
                m.get("role", "unknown"),
                m.get("format", "unknown"),
                f"{loc_count} location(s)",
            )

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Failed to list models:[/bold red] {e}")
        sys.exit(1)

@app.command("engines")
def engines_cmd(
    discover: bool = typer.Option(False, "--discover", help="Discover local candidate engines"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List configured engines or discover installed candidates."""
    client = get_client()
    try:
        if discover:
            console.print("[yellow]Discovering installed engines in approved roots...[/yellow]")
            candidates = client.post("/engines/discover", {})
            if as_json:
                typer.echo(json.dumps(candidates, indent=2))
                return

            table = Table(title="Discovered Engine Candidates")
            table.add_column("Display Name", style="bold cyan")
            table.add_column("Adapter Key", style="green")
            table.add_column("Tasks", style="magenta")

            for c in candidates:
                tasks = ", ".join(c.get("capabilities", {}).get("tasks", []))
                table.add_row(c.get("display_name", ""), c.get("adapter_key", ""), tasks)
            console.print(table)
            return

        engines = client.get("/engines")
        if as_json:
            typer.echo(json.dumps(engines, indent=2))
            return

        table = Table(title="Configured Inference Engines")
        table.add_column("ID", style="dim")
        table.add_column("Display Name", style="bold white")
        table.add_column("Adapter", style="cyan")
        table.add_column("State", style="green")
        table.add_column("Endpoint", style="yellow")

        for e in engines:
            table.add_row(
                e.get("id", "")[:8],
                e.get("display_name", ""),
                e.get("adapter_key", ""),
                e.get("observed_state", "unconfigured"),
                e.get("endpoint") or "-",
            )
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Failed to query engines:[/bold red] {e}")
        sys.exit(1)

@app.command("ask")
def ask_cmd(
    prompt: str = typer.Argument(..., help="Prompt to send to local model"),
    conversation_id: Optional[str] = typer.Option(None, "--conv", help="Existing conversation ID"),
    temperature: float = typer.Option(0.7, "--temperature", "-t", help="Sampling temperature"),
):
    """Submit a local message and stream the response to stdout."""
    client = get_client()
    try:
        payload = {
            "conversation_id": conversation_id,
            "message": prompt,
            "temperature": temperature,
            "stream": True,
        }
        for token in client.stream_chat("/chat", payload):
            sys.stdout.write(token)
            sys.stdout.flush()
        sys.stdout.write("\n")
    except Exception as e:
        console.print(f"\n[bold red]Chat error:[/bold red] {e}")
        sys.exit(1)

@app.command("generate")
def generate_cmd(
    prompt: str = typer.Argument(..., help="Prompt for image generation"),
    negative: str = typer.Option("", "--negative", "-n", help="Negative prompt"),
    width: int = typer.Option(512, "--width", "-w", help="Image width"),
    height: int = typer.Option(512, "--height", "-h", help="Image height"),
    steps: int = typer.Option(20, "--steps", help="Sampling steps"),
    seed: int = typer.Option(-1, "--seed", help="Random seed (-1 for random)"),
):
    """Submit an image generation request to Forge."""
    client = get_client()
    try:
        console.print(f"[yellow]Submitting image generation for:[/yellow] '{prompt}'")
        payload = {
            "prompt": prompt,
            "negative_prompt": negative,
            "width": width,
            "height": height,
            "steps": steps,
            "seed": seed,
        }
        res = client.post("/generate/image", payload)
        console.print(f"[bold green]Generation complete![/bold green] Seed: {res.get('seed')}")
        for art in res.get("artifacts", []):
            console.print(f"Saved: [cyan]{art.get('absolute_path')}[/cyan]")
    except Exception as e:
        console.print(f"[bold red]Generation error:[/bold red] {e}")
        sys.exit(1)

@app.command("logs")
def logs_cmd(
    level: Optional[str] = typer.Option(None, "--level", help="Filter by severity (INFO, WARNING, ERROR)"),
    limit: int = typer.Option(50, "--limit", "-n", help="Number of log entries to retrieve"),
):
    """Inspect local structured diagnostics logs."""
    client = get_client()
    try:
        params = {"limit": limit}
        if level:
            params["level"] = level
        data = client.get("/logs", params=params)
        entries = data.get("entries", [])

        for entry in entries:
            lvl = entry.get("level", "INFO")
            color = "white"
            if lvl == "ERROR":
                color = "bold red"
            elif lvl == "WARNING":
                color = "yellow"
            elif lvl == "INFO":
                color = "cyan"

            console.print(f"[{color}][{entry.get('timestamp')[:19]}] [{lvl}] [{entry.get('component')}][/{color}] {entry.get('message')}")
    except Exception as e:
        console.print(f"[bold red]Failed to retrieve logs:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    app()
