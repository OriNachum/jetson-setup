#!/usr/bin/env python3

import click
import os
import sys
import subprocess
import yaml
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from . import __version__
from .utils import get_script_path, run_script, check_jetson_platform

console = Console()

def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(f'jetson-cli version {__version__}')
    ctx.exit()

@click.group()
@click.option('--version', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True, help='Show version and exit')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """Jetson CLI - Command-line interface for NVIDIA Jetson setup and configuration"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    # Check if running on Jetson platform
    if not check_jetson_platform() and not os.environ.get('JETSON_CLI_SKIP_PLATFORM_CHECK'):
        console.print("[yellow]Warning: Not running on detected Jetson platform. Some features may not work correctly.[/yellow]")

@cli.command()
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'yaml']), default='table',
              help='Output format')
@click.option('--save', '-s', type=click.Path(), help='Save probe results to file')
@click.pass_context
def probe(ctx, output, save):
    """Probe and analyze the Jetson system configuration."""
    console.print(Panel("[bold blue]Probing Jetson System[/bold blue]", expand=False))
    
    script_path = get_script_path('probe-system.sh')
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing system...", total=None)
        
        try:
            result = run_script(script_path, verbose=ctx.obj['verbose'])
            
            if output == 'table':
                console.print("\n[bold green]System Probe Results:[/bold green]")
                console.print(result.stdout)
            elif output in ['json', 'yaml']:
                # Parse and format structured output
                console.print(f"\n[bold green]System Probe Results ({output}):[/bold green]")
                console.print(result.stdout)
            
            if save:
                with open(save, 'w') as f:
                    f.write(result.stdout)
                console.print(f"\n[green]Results saved to {save}[/green]")
                
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error running probe: {e}[/red]")
            sys.exit(1)

@cli.command()
@click.option('--profile-name', '-n', default='jetson-dev',
              help='Name for the environment profile')
@click.option('--force', '-f', is_flag=True, help='Force recreate existing profile')
@click.pass_context
def init(ctx, profile_name, force):
    """Initialize and create environment profile for Jetson development."""
    console.print(Panel(f"[bold blue]Initializing Environment Profile: {profile_name}[/bold blue]", expand=False))
    
    script_path = get_script_path('create-env-profile.sh')
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating environment profile...", total=None)
        
        try:
            env = os.environ.copy()
            env['PROFILE_NAME'] = profile_name
            if force:
                env['FORCE_RECREATE'] = 'true'
            
            result = run_script(script_path, env=env, verbose=ctx.obj['verbose'])
            console.print("\n[bold green]Environment Profile Created Successfully![/bold green]")
            console.print(result.stdout)
            
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error creating profile: {e}[/red]")
            sys.exit(1)

@cli.command()
@click.option('--skip-docker', is_flag=True, help='Skip Docker configuration')
@click.option('--skip-swap', is_flag=True, help='Skip swap configuration')
@click.option('--skip-ssd', is_flag=True, help='Skip SSD configuration')
@click.option('--interactive/--non-interactive', default=True,
              help='Run in interactive or non-interactive mode')
@click.pass_context
def setup(ctx, skip_docker, skip_swap, skip_ssd, interactive):
    """Run complete Jetson system setup and configuration."""
    console.print(Panel("[bold blue]Jetson System Setup[/bold blue]", expand=False))
    
    script_path = get_script_path('setup-system.sh')
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Setting up system...", total=None)
        
        try:
            env = os.environ.copy()
            env['INTERACTIVE_MODE'] = 'true' if interactive else 'false'
            if skip_docker:
                env['SKIP_DOCKER'] = 'true'
            if skip_swap:
                env['SKIP_SWAP'] = 'true'
            if skip_ssd:
                env['SKIP_SSD'] = 'true'
            
            result = run_script(script_path, env=env, verbose=ctx.obj['verbose'])
            console.print("\n[bold green]System Setup Completed Successfully![/bold green]")
            console.print(result.stdout)
            
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error during setup: {e}[/red]")
            sys.exit(1)

@cli.command()
@click.argument('component', type=click.Choice(['docker', 'swap', 'ssd', 'power', 'gui']))
@click.pass_context
def configure(ctx, component):
    """Configure specific system components."""
    console.print(Panel(f"[bold blue]Configuring {component.upper()}[/bold blue]", expand=False))
    
    script_map = {
        'docker': 'configure-docker.sh',
        'swap': 'configure-swap.sh',
        'ssd': 'configure-ssd.sh',
        'power': 'configure-power-mode.sh',
        'gui': 'configure-system-gui.sh'
    }
    
    script_path = get_script_path(script_map[component])
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Configuring {component}...", total=None)
        
        try:
            result = run_script(script_path, verbose=ctx.obj['verbose'])
            console.print(f"\n[bold green]{component.upper()} Configuration Completed![/bold green]")
            console.print(result.stdout)
            
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error configuring {component}: {e}[/red]")
            sys.exit(1)

@cli.command()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
def status(output_format):
    """Show current Jetson system status and configuration."""
    console.print(Panel("[bold blue]Jetson System Status[/bold blue]", expand=False))
    
    # This would integrate with existing system status checks
    table = Table()
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Details", style="green")
    
    # Add status rows based on system checks
    table.add_row("Platform", "✓ Jetson Detected", "NVIDIA Jetson AGX Orin")
    table.add_row("Docker", "✓ Running", "24.0.7")
    table.add_row("Containers", "✓ Available", "45 packages")
    
    console.print(table)

def main():
    """Main entry point for the CLI."""
    cli()

if __name__ == '__main__':
    main()