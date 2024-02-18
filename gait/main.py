import typer

app = typer.Typer()


@app.command()
def sa():
    typer.echo("SA")


@app.command()
def as_bro():
    typer.echo("AS")
