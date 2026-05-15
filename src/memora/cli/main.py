"""CLI entry point — Typer + Rich."""

from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="memora", help="Memora personal knowledge base")
console = Console()


def _run(coro):
    """Run an async function in the event loop."""
    return asyncio.run(coro)


@app.command()
def ingest(path: str = typer.Argument(..., help="File path to ingest")):
    """Ingest a document into the knowledge base."""
    from memora.app import create_app

    async def _ingest():
        a = await create_app()
        doc = await a.rag.ingest(path)
        console.print(f"[green]Ingested:[/green] {doc.title} ({doc.chunk_count} chunks)")
        await a.shutdown()

    _run(_ingest())


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    scope: str = typer.Option("all", help="Search scope: all/memory/knowledge/prompt"),
    top_k: int = typer.Option(5, help="Max results"),
):
    """Search across memories, documents, and prompts."""
    from memora.app import create_app

    async def _search():
        a = await create_app()
        results = await a.search.search(query, scope=scope, top_k=top_k)
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return

        table = Table(title=f"Search results for: {query}")
        table.add_column("Type", style="cyan")
        table.add_column("Content", style="white")
        table.add_column("Score", style="green")

        for r in results:
            table.add_row(r.source_type, r.content[:80], f"{r.relevance_score:.2f}")

        console.print(table)
        await a.shutdown()

    _run(_search())


@app.command("memory")
def memory_cmd(
    action: str = typer.Argument(..., help="Action: list/add/delete/recall"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Memory content"),
    memory_type: str = typer.Option("fact", "--type", "-t", help="Memory type"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Recall query"),
    limit: int = typer.Option(20, help="List limit"),
):
    """Manage memories."""
    from memora.app import create_app
    from memora.models.memory import Memory, MemoryType

    async def _memory():
        a = await create_app()

        if action == "list":
            memories = await a.memory.list(limit=limit)
            if not memories:
                console.print("[yellow]No memories found.[/yellow]")
                return
            table = Table(title="Memories")
            table.add_column("Type", style="cyan")
            table.add_column("Content", style="white")
            table.add_column("Source", style="dim")
            for m in memories:
                table.add_row(m.memory_type.value, m.content[:60], m.source)
            console.print(table)

        elif action == "add":
            if not content:
                console.print("[red]--content is required for add[/red]")
                raise typer.Exit(1)
            m = Memory(content=content, memory_type=MemoryType(memory_type), source="cli")
            await a.memory.save(m)
            console.print(f"[green]Saved:[/green] [{memory_type}] {content}")

        elif action == "delete":
            if not content:
                console.print("[red]--content (memory id) is required for delete[/red]")
                raise typer.Exit(1)
            ok = await a.memory.delete(content)
            if ok:
                console.print(f"[green]Deleted memory {content}[/green]")
            else:
                console.print(f"[red]Memory {content} not found[/red]")

        elif action == "recall":
            if not query:
                console.print("[red]--query is required for recall[/red]")
                raise typer.Exit(1)
            results = await a.memory.recall(query, top_k=limit)
            for r in results:
                console.print(f"  [{r.memory_type.value}] {r.content}")

        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            console.print("  Available: list, add, delete, recall")

        await a.shutdown()

    _run(_memory())


@app.command()
def prompt(
    action: str = typer.Argument(..., help="Action: list/add/get/score"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Prompt name"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Prompt content"),
    score_val: Optional[float] = typer.Option(None, "--score", "-s", help="Score (1-5)"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Version number"),
    limit: int = typer.Option(20, help="List limit"),
):
    """Manage prompts."""
    from memora.app import create_app

    async def _prompt():
        a = await create_app()

        if action == "list":
            prompts = await a.prompt.list()
            if not prompts:
                console.print("[yellow]No prompts found.[/yellow]")
                return
            table = Table(title="Prompts")
            table.add_column("Name", style="cyan")
            table.add_column("Version", style="green")
            table.add_column("Tags", style="dim")
            for p in prompts:
                table.add_row(p.name, str(p.latest_version), ",".join(p.tags))
            console.print(table)

        elif action == "add":
            if not name or not content:
                console.print("[red]--name and --content are required[/red]")
                raise typer.Exit(1)
            p = await a.prompt.save(name, content)
            console.print(f"[green]Saved:[/green] {p.name} v{p.latest_version}")

        elif action == "get":
            if not name:
                console.print("[red]--name is required[/red]")
                raise typer.Exit(1)
            p, v = await a.prompt.get(name, version)
            console.print(f"[cyan]{p.name}[/cyan] v{v.version}")
            console.print(f"Content: {v.content}")
            if v.variables:
                console.print(f"Variables: {v.variables}")
            if v.score:
                console.print(f"Score: {v.score}")

        elif action == "score":
            if not name or score_val is None or version is None:
                console.print("[red]--name, --version, and --score are required[/red]")
                raise typer.Exit(1)
            await a.prompt.score(name, version, score_val)
            console.print(f"[green]Scored {name} v{version}: {score_val}[/green]")

        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            console.print("  Available: list, add, get, score")

        await a.shutdown()

    _run(_prompt())


@app.command()
def stats():
    """Show knowledge base statistics."""
    from memora.app import create_app

    async def _stats():
        a = await create_app()

        mem = await a.storage.db.fetch_one("SELECT COUNT(*) as cnt FROM memories")
        docs = await a.storage.db.fetch_one("SELECT COUNT(*) as cnt FROM documents")
        chunks = await a.storage.db.fetch_one("SELECT COUNT(*) as cnt FROM document_chunks")
        prompts = await a.storage.db.fetch_one("SELECT COUNT(*) as cnt FROM prompts")

        table = Table(title="Memora Statistics")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="green")
        table.add_row("Memories", str(mem["cnt"] if mem else 0))
        table.add_row("Documents", str(docs["cnt"] if docs else 0))
        table.add_row("Document Chunks", str(chunks["cnt"] if chunks else 0))
        table.add_row("Prompts", str(prompts["cnt"] if prompts else 0))
        console.print(table)

        await a.shutdown()

    _run(_stats())


@app.command()
def serve():
    """Start MCP Server."""
    from memora.app import create_app
    from memora.mcp.server import create_mcp_server

    async def _serve():
        a = await create_app()
        mcp = create_mcp_server(a)
        console.print(f"[green]Starting MCP Server: {mcp.name}[/green]")
        await mcp.run_async()

    _run(_serve())
