from pathlib import Path

from invoke import task


@task
def lint(c):
    """Run flake8 and mypy."""
    script_dir = Path(__file__).parent
    with c.cd(script_dir):
        c.run("flake8 cldb tools")
        c.run("mypy cldb tools")
