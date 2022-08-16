#!/usr/bin/env python
import os
import libtmux
import sys
import rich_click as click
from rich_click import style
import git
import requests
import shutil
import subprocess
import venv

python_version = "{}.{}".format(sys.version_info[0], sys.version_info[1])
cwd = os.getcwd()


def _get_version_list():
    constraints = []
    remotes = (
        git.cmd.Git()
        .ls_remote("--tags", "https://github.com/apache/airflow")
        .split("\n")
    )
    for remote in remotes:
        if "^{}" in remote:
            continue
        constraint = remote.split("constraints-")
        if len(constraint) > 1:
            if constraint[1] == "latest":
                continue
            click.echo(constraint[1])
            constraints.append(constraint[1])
    return constraints


def _resolve_constraint_url(version):
    constraint_file = "constraints-" + python_version + ".txt"
    constraint_url = (
        f"https://raw.githubusercontent.com/apache/airflow/constraints-"
        + version
        + "/"
        + constraint_file
    )
    return [constraint_url, constraint_file]


def _abort(message):
    click.echo()
    click.echo(
        style("Aborting:", bg="red", fg="white", bold=True) + " " + message + "\n"
    )
    exit(1)


@click.command()
def versions():
    """List the currently available Airflow versions"""
    vers = _get_version_list()
    click.echo("\n".join(vers))


@click.command()
@click.argument("version", metavar="<version>")
@click.option(
    "--username",
    default="airflow",
    help="the username to use when creating the initial user",
    metavar="<string>",
)
@click.option(
    "--firstname",
    default="Admin",
    help="the initial user's first name",
    metavar="<string>",
)
@click.option(
    "--lastname",
    default="User",
    help="the initial user's last name",
    metavar="<string>",
)
@click.option(
    "--email",
    default="admin@example.com",
    help="the initial user's email address",
    metavar="<string>",
)
@click.option(
    "--password",
    default="airflow",
    help="the initial user's password",
    metavar="<string>",
)
def new(version, username, firstname, lastname, email, password):
    """Initiate a new project based on <version>"""
    if sys.version_info <= (2, 7):
        _abort(
            "Airflow requires at least Python 2.7; you are on "
            + style(python_version, fg="red")
            + "."
        )

    click.echo(
        "\nSetting up a new Airflow project in: " + style(cwd, fg="yellow", bold=True)
    )

    # See if we're gonna stomp anything
    [constraint_url, constraint_file] = _resolve_constraint_url(version)
    requirements_file = "requirements.txt"
    venv_dir = os.path.join(cwd, "venv")

    if os.path.exists(constraint_file):
        _abort(
            "there is already a constraints file at "
            + style(cwd + "/" + constraint_file, fg="yellow")
        )

    if os.path.exists(requirements_file):
        _abort("there is already a requirements.txt file in " + style(cwd, fg="yellow"))

    if os.path.exists(venv_dir):
        _abort(
            "there is already a virtual environment in " + style(venv_dir, fg="yellow")
        )

    # Download and save the constraint file
    click.echo(
        "-- Fetching constraint file and writing to ./" + constraint_file + "... ",
        nl=False,
    )

    response = requests.get(constraint_url)
    if response.status_code == 200:
        with open(constraint_file, "w") as f:
            f.write(response.text)
            f.close()
    else:
        click.echo("❌")
        _abort(
            "unable to find a constraints file for Airflow version "
            + version
            + " and Python version "
            + python_version
        )

    click.echo("📋")

    # Create a requirements file
    click.echo(
        "-- Writing requirements file to ./" + requirements_file + "... ", nl=False
    )

    # TODO: catch an error here
    with open(requirements_file, "w") as f:
        f.write("apache-airflow==" + version + "\n")
        f.close()

    click.echo("🥡")

    # Add AIRFLOW_HOME to .env for convenience
    click.echo(
        "-- Writing " + style("AIRFLOW_HOME=" + cwd, fg="blue") + " to .env... ",
        nl=False,
    )

    # TODO: catch an error here
    with open(".env", "w") as f:
        f.write("AIRFLOW_HOME=" + cwd + "\n")
        f.close()

    click.echo("🌐")

    # Create our virtual environment
    click.echo("-- Creating a virtual environment in " + venv_dir + "... ", nl=False)
    venv.create(venv_dir, with_pip=True)
    click.echo("🪣")

    # Install python packages
    click.echo()
    click.echo("Installing Python packages... ", nl=False)

    pip_install = subprocess.run(
        ["venv/bin/pip", "install", "-r", requirements_file, "-c", constraint_file],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    if pip_install.returncode:
        click.echo("❌")
        click.echo_via_pager(pip_install.stdout.strip("\n"))
        _abort("pip install was unsuccessful")

    click.echo("📦")

    # Initialize Airflow
    click.echo("Initializing Airflow... ", nl=False)

    db_init = subprocess.run(
        [
            "venv/bin/airflow",
            "db",
            "init",
        ],
        cwd=cwd,
        env={"AIRFLOW_HOME": cwd},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    if db_init.returncode:
        click.echo("❌")
        click.echo_via_pager(db_init.stdout.strip("\n"))
        _abort(style("airflow db init", fg="blue") + " was unsuccessful")

    click.echo("🚀")

    # Create an Airflow user
    click.echo(
        "Creating Airflow user "
        + style(username + " (" + email + ")", fg="yellow")
        + "... ",
        nl=False,
    )

    user_create = subprocess.run(
        [
            "venv/bin/airflow",
            "users",
            "create",
            "--username",
            username,
            "--firstname",
            firstname,
            "--lastname",
            lastname,
            "--password",
            password,
            "--role",
            "Admin",
            "--email",
            email,
        ],
        cwd=cwd,
        env={"AIRFLOW_HOME": cwd},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    if user_create.returncode:
        click.echo("❌")
        click.echo_via_pager(user_create.stdout.strip("\n"))
        _abort(style("airflow users create", fg="blue") + " was unsuccessful.")

    click.echo("🧑")

    click.echo()
    click.echo("Airflow is ready. To start it up in a tmux session, run:")
    click.echo()
    click.echo("\t% airflux start")

    return


@click.command()
def stop():
    """Stop a running tmux session running Airflow components"""
    server = libtmux.Server()
    session = server.find_where({"session_name": "Airflux"})
    window = session.find_where({"window_name": "Main"})

    scheduler_pane = window.select_pane(2)
    scheduler_pane.send_keys("^C")
    scheduler_pane.send_keys("exit")

    webserver_pane = window.select_pane(1)
    webserver_pane.send_keys("^C")
    webserver_pane.send_keys("exit")

    session.kill_session()


@click.command()
def start():
    """Start a tmux session running Airflow components"""
    tmux_dir = os.getenv("HOME") + "/.tmux/tmp"

    if os.path.exists(tmux_dir):
        shutil.rmtree(tmux_dir)

    os.makedirs(tmux_dir, 0o777)

    server = libtmux.Server()

    session = server.new_session(
        session_name="Airflux", kill_session=True, attach=False
    )
    session.set_option("mouse", "on")
    session.set_environment("AIRFLOW_HOME", cwd)
    session.set_environment("TMUX_TMPDIR", tmux_dir)

    window = session.new_window(attach=True, window_name="Main")

    main_pane = window.attached_pane
    main_pane.send_keys("clear")
    main_pane.send_keys("source venv/bin/activate")

    scheduler_pane = main_pane.split_window(vertical=True)
    scheduler_pane.send_keys("source venv/bin/activate")
    scheduler_pane.send_keys("airflow scheduler")

    webserver_pane = main_pane.split_window(vertical=False)
    webserver_pane.send_keys("source venv/bin/activate")
    webserver_pane.send_keys("airflow webserver")

    if sys.version_info >= (3, 7):
        triggerer_pane = scheduler_pane.split_window(vertical=False)
        triggerer_pane.send_keys("source venv/bin/activate")
        triggerer_pane.send_keys("airflow triggerer")

    server.attach_session(target_session="Airflux")


@click.group()
@click.version_option("1.0.0")
def main():
    pass


main.add_command(start)
main.add_command(stop)
main.add_command(new)
main.add_command(versions)

if __name__ == "__main__":
    main()
