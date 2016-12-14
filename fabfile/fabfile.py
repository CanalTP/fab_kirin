# coding=utf-8


from fabric.api import *
from importlib import import_module
from f5_kisio.f5kisio import *


def deploy_container_safe(server, f5NodesManagment):
    """ Restart kirin on a specific server,
        in a safe way if load balancers are available
    """
    with settings(host_string=server):
        f5NodesManagment.disable_node(server)
        restart()
        f5NodesManagment.enable_node(server)


def deploy_container_safe_all(f5NodesManagment):
    """ Restart kirin on all servers,
    in a safe way if load balancers are available
    """
    for server in env.roledefs['kirin']:
        execute(deploy_container_safe, server, f5NodesManagment)


@task
def deploy():
    """ Deploy kirin """
    if env.use_load_balancer:
        f5NodesManagment = SimpleF5NodesManagment(True)
    else:
        f5NodesManagment = NullF5NodesManagment()
    deploy_container_safe_all(f5NodesManagment)


def start():
    """ Start targeted containers in daemon mode and restart them if crash """
    run('docker-compose up --force-recreate -d')


def stop():
    """ Stop targeted containers """
    run('docker-compose stop')


def remove():
    """ Remove targeted containers without asking confirmation and
    remove volumes associated with containers
    """
    run('docker-compose rm -v -f')


def restart():
    """ Restart containers properly """
    stop()
    remove()
    start()


@task
def use(module_path, *args):
    pos = module_path.rfind(".")
    if pos == -1:
        path, f_name = module_path, module_path
    else:
        path, f_name = module_path[:pos], module_path[pos+1:]
    module = import_module(path)
    getattr(module, f_name)(*args)
