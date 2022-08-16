# Airflux

Airflux is a *very* simple installer and tmux session manager for Airflow.

It exists for those of us who deploy Airflow a lot; maybe you're developing an operator and need to test it by hand on Airflow 1.3, or you manage a collection of Airflow pipelines and need a quick way to start and stop local versions of them.

## Getting started

Install airflux:

```
pip install airflux
```

Airflux uses constraints files to install Airflow for your version of Python. This command will list the versions of Airflow with available constraints files.

```
airflux versions
```

You will probably want to make a directory for your deployment. The script doesn't do this for you.

```
mkdir my-airflow-deployment && cd my-airflow-deployment
```

To download the constraints file and create a local Python environment for Airflow, specify the version number to `airflux new`:

```
airflux new 2.3.3
```

After the installation is complete, start Airflux in a tmux session:

```
airflux start
```

Once inside the tmux session, you can exit it and shut down Airflow:

```
airflux stop
```


To install Airflow into your current directory
