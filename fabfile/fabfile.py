# coding=utf-8


from fabric.api import *
from importlib import import_module
import f5kisio


def deploy_container_safe(server, f5_nodes_management):
    """ Restart kirin on a specific server,
        in a safe way if load balancers are available
    """
    with settings(host_string=server):
        f5_nodes_management.disable_node(server)
        restart()
        test_deployment()
        f5_nodes_management.enable_node(server)


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
        f5_nodes_management = f5kisio.SimpleF5NodesManagment(env.ADC_HOSTNAME, verbose=True)
    else:
        f5_nodes_management = f5kisio.NullF5NodesManagment()
    deploy_container_safe_all(f5_nodes_management)


def remove_targeted_image(id_image):
    """ Remove an image """
    with settings(warn_only=True):
        run('docker rmi {}'.format(id_image))


def remove_targeted_images():
    """ Remove several images """
    images_to_remove = run("docker images | grep kirin | awk '{print $3}' && docker images -f dangling=true -q")
    for image in images_to_remove.split('\n'):
        remove_targeted_image(image)


def start_container():
    """ Start targeted containers in daemon mode and restart them if crash """
    run('docker-compose up --force-recreate -d')


def stop_container():
    """ Stop targeted containers """
    run('docker-compose stop')


def remove_container():
    """ Remove targeted containers without asking confirmation and
    remove volumes associated with containers
    """
    run('docker-compose rm -v -f')


def restart():
    """ Restart containers properly """
    stop_container()
    remove_container()
    remove_targeted_images()
    start_container()


def test_deployment():
    """ Verify api kirin is OK """
    response = local("curl -I {}/status | head -n 1".format(env.kirin_host), capture=True)
    if response.split(' ')[1] != '200':
        abort(response)


@task
def use(module_path, *args):
    pos = module_path.rfind(".")
    if pos == -1:
        path, f_name = module_path, module_path
    else:
        path, f_name = module_path[:pos], module_path[pos+1:]
    module = import_module(path)
    getattr(module, f_name)(*args)
