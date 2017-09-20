# coding=utf-8
import json
from fabric.api import *
from importlib import import_module
import abc
import requests
import time
from retrying import Retrying
from fabric.contrib.files import upload_template as _upload_template
import os
from jinja2 import Environment, FileSystemLoader


env.use_syslog = True

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
    requests.packages.urllib3.disable_warnings()

    def enable_node(self, node):
        node = hostname2node(node)
        print("The {} node will be enabled".format(node))
        header = {'X-Rundeck-Auth-Token': env.rundeck_token, 'Content-Type': 'application/json', 'Accept': 'application/json'}
        args = {'argString': '-nodename {} -state enable'.format(node)}

        switch_power_on = requests.post("{}/api/18/job/{}/run"
                                        .format(env.rundeck_url, env.rundeck_job, node),
                                        headers=header, data=json.dumps(args), verify=False)
        response = switch_power_on.json()

        def check_node(query):
            """
            poll on state of execution until it gets a 'succeded' status
            """
            try:
                response = requests.get(query, headers=header, verify=False)
                print('waiting for enable node ...')
            except Exception as e:
                print("Error : {}".format(e))
                exit(1)

            return response.json()
        request = '{}/api/18/execution/{}/state?{}'.format(env.rundeck_url, response['id'], env.rundeck_job)

        try:
            Retrying(stop_max_delay=10000, wait_fixed=500,
                     retry_on_result=lambda status: check_node(request).get('executionState') != 'SUCCEEDED')\
                .call(check_node, request)
        except:
            abort("The {} node cannot be enabled.".format(node))

        print("The {} node is enabled".format(node))

    def disable_node(self, node):
        node = hostname2node(node)
        print("The {} node will be disabled".format(node))
        header = {'X-Rundeck-Auth-Token': env.rundeck_token, 'Content-Type': 'application/json', 'Accept': 'application/json'}
        args = {'argString': '-nodename {} -state disable'.format(node)}

        switch_power_off = requests.post("{}/api/18/job/{}/run"
                                         .format(env.rundeck_url, env.rundeck_job, node),
                                         headers=header, data=json.dumps(args), verify=False)
        response = switch_power_off.json()

        def check_node(query):
            """
            poll on state of execution until it gets a 'succeded' status
            """
            try:
                response = requests.get(query, headers=header, verify=False)
                print('waiting for disable node ...')
            except Exception as e:
                print("Error : {}".format(e))
                exit(1)

            return response.json()
        request = '{}/api/18/execution/{}/state?{}'.format(env.rundeck_url, response['id'], env.rundeck_job)

        try:
            Retrying(stop_max_delay=10000, wait_fixed=500,
                     retry_on_result=lambda status: check_node(request).get('executionState') != 'SUCCEEDED')\
                .call(check_node, request)
        except:
            abort("The {} node cannot be disabled.".format(node))

        print("The {} node is disabled".format(node))


class NoSafeDeploymentManager(DeploymentManager):
    def enable_node(self, node):
        """ Null impl """

    def disable_node(self, node):
        """ Null impl """


def deploy_kirin_container_safe(server, node_manager):
    """ Restart kirin on a specific server,
        in a safe way if load balancers are available
    """
    with settings(host_string=server):
        node_manager.disable_node(server)
        restart('docker-compose_kirin.yml')
        test_deployment()
        node_manager.enable_node(server)


def deploy_kirin_beat_container_safe(server, node_manager):
    """ Restart kirin on a specific server,
        in a safe way if load balancers are available
    """
    with settings(host_string=server):
        restart('docker-compose_kirin-beat.yml')


def deploy_container_safe_all(node_manager):
    """ Restart kirin on all servers,
    in a safe way if load balancers are available
    """
    for server in env.roledefs['kirin']:
        execute(deploy_kirin_container_safe, server, node_manager)
        # need to wait between both node execution because using same token
        time.sleep(5)
    for server in env.roledefs['kirin-beat']:
        execute(deploy_kirin_beat_container_safe, server, node_manager)
        # need to wait between both node execution because using same token
        time.sleep(5)


def update_kirin():
    """ Retrieve new kirin image
    To tag the image, we pull the previous tag, tag it as our own and push it
    """
    run('docker pull {image}:{prev_tag}'.format(image=env.docker_image_kirin, prev_tag=env.previous_docker_tag))
    run('docker tag {image}:{prev_tag} {image}:{new_tag}'
        .format(image=env.docker_image_kirin, prev_tag=env.previous_docker_tag, new_tag=env.current_docker_tag))
    run('docker push {image}:{new_tag}'.format(image=env.docker_image_kirin, new_tag=env.current_docker_tag))


@task
@roles('kirin')
def deploy():
    """ Deploy kirin """
    if 'kirin-beat' in env.roledefs and len(env.roledefs['kirin-beat']) != 1:
        print('Error : Only one beat can exist, you provided kirin-beat role to {}'
              .format(env.roledefs['kirin-beat']))
        exit(1)
    if env.use_load_balancer:
        node_manager = SafeDeploymentManager()
    else:
        node_manager = NoSafeDeploymentManager()
    run('rm -f {}/docker-compose.yml'.format(env.path)) #just to remove deprecated compose
    upload_template('kirin.env', '{}'.format(env.path), context={'env': env})
    upload_template('docker-compose_kirin.yml', '{}'.format(env.path), context={'env': env})
    upload_template('docker-compose_kirin-beat.yml', '{}'.format(env.path), context={'env': env})
    update_kirin()
    deploy_container_safe_all(node_manager)


def remove_targeted_image(id_image):
    """ Remove an image """
    with settings(warn_only=True):
        run('docker rmi {}'.format(id_image))


def remove_targeted_images():
    """ Remove several images """
    images_to_remove = run("docker images | grep kirin | awk '{print $3}' && docker images -f dangling=true -q")
    for image in images_to_remove.split('\n'):
        remove_targeted_image(image.strip('\r'))


def start_container(compose_file):
    """ Start targeted containers in daemon mode and restart them if crash """
    run('docker-compose -f {} up --force-recreate -d'.format(compose_file))


def stop_container(compose_file):
    """ Stop targeted containers """
    run('docker-compose -f {} stop'.format(compose_file))


def remove_container(compose_file):
    """ Remove targeted containers without asking confirmation and
    remove volumes associated with containers
    """
    run('docker-compose -f {} rm -v -f'.format(compose_file))


def restart(compose_file):
    """ Restart containers properly """
    stop_container(compose_file)
    remove_container(compose_file)
    remove_targeted_images()
    start_container(compose_file)


def test_deployment():
    """ Verify api kirin is OK """
    def check_status(query):
        """
        poll on state of execution until it gets a 'OK' status
        """
        try:
            response = requests.get(query)
            print('waiting to check status ...')
        except Exception as e:
            print("Error : {}".format(e))
            exit(1)

        return response.status_code
    request = 'http://{}/status'.format(env.kirin_host)

    try:
        Retrying(stop_max_delay=5000,
                 wait_fixed=100,
                 retry_on_result=lambda status: check_status(request) != 200)\
            .call(check_status, request)
    except Exception as e:
        abort(e)
    print("{} is OK".format(request))


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
    # for example : user@hostname.suffix -> hostname
    host_only = host.replace(env.user + '@', '').replace(env.hostname_suffix_to_remove, '')

    return host_only


def upload_template(filename, destination, context=None, **kwargs):
    kwargs['use_jinja'] = True
    kwargs['template_dir'] = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')
    kwargs['context'] = context
    kwargs['use_sudo'] = False
    kwargs['backup'] = False
    _upload_template(filename, destination, **kwargs)
