# coding=utf-8
import json
from fabric.api import *
from importlib import import_module
import abc
import requests
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning


class DeploymentManager(object):
    @abc.abstractmethod
    def enable_node(self, node):
        pass

    @abc.abstractmethod
    def disable_node(self, node):
        pass


class SafeDeploymentManager(DeploymentManager):
    # avoid the message output : InsecureRequestWarning: Unverified HTTPS request is being made.
    # Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/security.html
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    def enable_node(self, node):
        node = hostname2node(node)
        print("The {} node will be enabled".format(node))
        header = {'X-Rundeck-Auth-Token': env.token, 'Content-Type': 'application/json', 'Accept': 'application/json'}
        args = {'argString': '-nodename {} -state enable'.format(node)}

        switch_power_on = requests.post("{}://{}:{}/api/18/job/{}/run"
                                        .format(env.protocol, env.host, env.port, env.job, node),
                                        headers=header, data=json.dumps(args), verify=False)
        time.sleep(2)

        response = json.loads(switch_power_on.text)
        status_execution = requests.get("{}://{}:{}/api/17/execution/{}/state?{}"
                                        .format(env.protocol, env.host, env.port, response['id'], env.job),
                                        headers=header, verify=False)
        res = json.loads(status_execution.text)

        if res['executionState'] == 'SUCCEEDED':
            print("The {} node is enabled".format(node))
        else:
            abort("The {} node is {}, so cannot to be enabled.".format(node, res['executionState']))

    def disable_node(self, node):
        node = hostname2node(node)
        print("The {} node will be disabled".format(node))
        header = {'X-Rundeck-Auth-Token': env.token, 'Content-Type': 'application/json', 'Accept': 'application/json'}
        args = {'argString': '-nodename {} -state disable'.format(node)}

        switch_power_off = requests.post("{}://{}:{}/api/18/job/{}/run"
                                         .format(env.protocol, env.host, env.port, env.job, node),
                                         headers=header, data=json.dumps(args), verify=False)
        time.sleep(2)

        response = json.loads(switch_power_off.text)
        status_execution = requests.get("{}://{}:{}/api/17/execution/{}/state?{}"
                                        .format(env.protocol, env.host, env.port, response['id'], env.job),
                                        headers=header, verify=False)
        res = json.loads(status_execution.text)

        if res['executionState'] == 'SUCCEEDED':
            print("The {} node is disabled".format(node))
        else:
            abort("The {} node is {} to be disabled.".format(node, res['executionState']))


class NoSafeDeploymentManager(DeploymentManager):
    def enable_node(self, node):
        """ Null impl """

    def disable_node(self, node):
        """ Null impl """


def deploy_container_safe(server, f5_nodes_management):
    """ Restart kirin on a specific server,
        in a safe way if load balancers are available
    """
    with settings(host_string=server):
        f5_nodes_management.disable_node(server)
        restart()
        test_deployment()
        f5_nodes_management.enable_node(server)


def deploy_container_safe_all(f5_nodes_management):
    """ Restart kirin on all servers,
    in a safe way if load balancers are available
    """
    for server in env.roledefs['kirin']:
        execute(deploy_container_safe, server, f5_nodes_management)


@task
def deploy():
    """ Deploy kirin """
    if env.use_load_balancer:
        f5_nodes_management = SafeDeploymentManager()
    else:
        f5_nodes_management = NoSafeDeploymentManager()
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


def hostname2node(host):
    """ Return the node name equivalent to hostname"""
    # clean the host which can contain usernames from fabric
    host_only = host.replace(env.user + '@', '').replace(env.hostname_suffix, '')

    return host_only
