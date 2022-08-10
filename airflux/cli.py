#!/usr/bin/env python
import os

import libtmux
import sys
import rich_click as click
import git
import requests


@click.command()
def get_versions():
    """List the currently available Airflow versions"""
    constraints = []
    remotes = git.cmd.Git().ls_remote("--tags", "https://github.com/apache/airflow").split('\n')
    for remote in remotes:
        if '^{}' in remote: continue
        constraint = remote.split('constraints-')
        if len(constraint) > 1:
            if '^{}' in remote: continue
            click.echo(constraint[1])
            constraints.append(constraint[1])
    return constraints


@click.command()
@click.argument("version", metavar='<version>')
def new_project(version):
    """Initiate a new project based on <version>"""
    cwd = os.getcwd()

    click.echo("Setting up a project in: " + cwd)

    # Grab the right constraint file
    python_version = '{}.{}'.format(sys.version_info[0], sys.version_info[1])
    constraint_file = "constraints-" + python_version + ".txt"
    constraint_url = f"https://raw.githubusercontent.com/apache/airflow/constraints-" + version + "/" + constraint_file
    requirements_file = "requirements.txt"

    click.echo("  using constraint: " + constraint_url)

    if os.path.exists(constraint_file):
        click.echo("  there is already a constraints file here, aborting")
        exit(1)

    if os.path.exists(requirements_file):
        click.echo("  there is already a requirements.txt file here, aborting")
        exit(1)

    response = requests.get(constraint_url)
    if response.status_code == 200:
        with open(constraint_file, "w") as f:
            f.write(response.text)
            f.close()
    else:
        click.echo("  check your version, that constraint file doesn't load")
        exit(1)

    click.echo("  constraint file created")

    with open(requirements_file, "w") as f:
        f.write("apache-airflow==" + version + '\n')
        f.close()

    click.echo("  requirements.txt created")

    with open(".env", "w") as f:
        f.write("AIRFLOW_HOME=" + cwd + '\n')
        f.close()

    click.echo("  .env file created")

    click.echo()
    click.echo("Airflow has been configured  To finish the installation, run:")
    click.echo("  python -m venv venv")
    click.echo("  source venv/bin/activate")
    click.echo("  pip install -r requirements.txt -c " + constraint_file)
    click.echo()
    click.echo("airflow db init")
    click.echo()
    click.echo("airflow users create \\")
    click.echo("    --username airflow \\")
    click.echo("    --firstname Air \\")
    click.echo("    --lastname Flow \\")
    click.echo("    --role Admin \\")
    click.echo("    --email example@yourplace.org")

    return


@click.command()
def stop():
    """Stop a running tmux session running Airflow components"""
    server = libtmux.Server()
    session = server.find_where({"session_name": "Airflux"})
    window = session.find_where({'window_name': 'Main'})

    scheduler_pane = window.select_pane(2)
    scheduler_pane.send_keys('^C')
    scheduler_pane.send_keys('exit')

    webserver_pane = window.select_pane(1)
    webserver_pane.send_keys('^C')
    webserver_pane.send_keys('exit')

    session.kill_session()


@click.command()
def start():
    """Start a tmux session running Airflow components"""
    #    export TMUX_TMPDIR=~/.tmux/tmp
    #     if [ -e ~/.tmux/tmp ]; then
    #         rm -rf ~/.tmux/tmp
    #     fi
    #     mkdir -p ~/.tmux/tmp
    #     chmod 777 -R ~/.tmux/tmp

    server = libtmux.Server()
    session = server.new_session(session_name="Airflux", kill_session=True, attach=False)
    session.set_option("mouse", "on")

    window = session.new_window(attach=True, window_name="Main")

    main_pane = window.attached_pane
    main_pane.send_keys('clear')

    scheduler_pane = main_pane.split_window(vertical=True)
    scheduler_pane.send_keys('airflow scheduler')

    webserver_pane = main_pane.split_window(vertical=False)
    webserver_pane.send_keys('airflow webserver')

    if sys.version_info >= (3, 7):
        triggerer_pane = scheduler_pane.split_window(vertical=False)
        triggerer_pane.send_keys('airflow triggerer')

    server.attach_session(target_session="Airflux")


@click.group()
@click.version_option("0.0.1")
def main():
    pass


main.add_command(start)
main.add_command(stop)
main.add_command(new_project)
main.add_command(get_versions)

if __name__ == "__main__":
    main()
