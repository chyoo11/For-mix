# All-In-One CLI Scaffold (Safe)

A modern, Rich-styled CLI with five placeholder tools and plugin hooks. This project does not include any platform automation logic.

## Features
- Interactive menu and subcommands (Typer + Rich)
- Five placeholder commands:
  - nickname
  - profile-views
  - views
  - copylink
  - like
- Plugin system: drop Python files into `plugins/` to register your own commands.

## Install
```bash
pip install -r requirements.txt
```

## Run
Interactive menu:
```bash
python aio_cli.py
```

Direct subcommand:
```bash
python aio_cli.py nickname --target example --new "New Value"
```

## Plugins
Create a `plugins/` folder next to `aio_cli.py` and add a module like `mytool.py`:
```python
def register(app, menu, console):
    import typer

    @app.command("mytool")
    def mytool_command():
        console.print("My tool running…")

    # Optional: register in interactive menu
    menu["m"] = mytool_command
```

## Notes
- This repository provides only a generic, safe CLI scaffold. You are responsible for ensuring any plugins or custom logic comply with all relevant terms, policies, and laws.