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


class DeploymentManager(object):
    @abc.abstractmethod
    def enable_node(self, node):
        pass

    @abc.abstractmethod
    def disable_node(self, node):
        pass


class NoSafeDeploymentManager(DeploymentManager):
    def enable_node(self, node):
        """ Null impl """

    def disable_node(self, node):
        """ Null impl """


def check_node(query, header=None):
    """
    poll on state of execution until it gets a 'succeeded' status
    """
    response = None
    try:
        if header:
            response = requests.get(query, headers=header, verify=False)
        else:
            response = requests.get(query)
        print('waiting for enable node ...')
    except Exception as e:
        print("Error : {}".format(e))

    # Return full response
    return response


class SafeDeploymentManager(DeploymentManager):
    # avoid the message output : InsecureRequestWarning: Unverified HTTPS request is being made.
    # Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/security.html
    requests.packages.urllib3.disable_warnings()

    HTTP_HEADER = {'Content-Type': 'application/json',
                   'Accept': 'application/json',
                   'X-Rundeck-Auth-Token': env.rundeck_token}

    def enable_node(self, node):
        node = hostname2node(node)
        print("The {} node will be enabled".format(node))

        args = {'argString': '-nodename {} -state enable'.format(node)}

        switch_power_on = requests.post("{}/api/18/job/{}/run"
                                        .format(env.rundeck_url, env.rundeck_job, node),
                                        headers=self.HTTP_HEADER, data=json.dumps(args), verify=False)
        response = switch_power_on.json()

        request = '{}/api/18/execution/{}/state?{}'.format(env.rundeck_url, response['id'], env.rundeck_job)

        try:
            Retrying(stop_max_delay=60000, wait_fixed=500,
                     retry_on_result=lambda status: check_node(request, self.HTTP_HEADER).json()
                     .get('executionState') != 'SUCCEEDED').call(check_node, request)
        except Exception as e:
            abort("The {} node cannot be enabled:\n{}".format(node, e))

        print("The {} node is enabled".format(node))

    def disable_node(self, node):
        node = hostname2node(node)
        print("The {} node will be disabled".format(node))

        args = {'argString': '-nodename {} -state disable'.format(node)}

        switch_power_off = requests.post("{}/api/18/job/{}/run"
                                         .format(env.rundeck_url, env.rundeck_job, node),
                                         headers=self.HTTP_HEADER, data=json.dumps(args), verify=False)
        response = switch_power_off.json()

        request = '{}/api/18/execution/{}/state?{}'.format(env.rundeck_url, response['id'], env.rundeck_job)

        try:
            Retrying(stop_max_delay=60000, wait_fixed=500,
                     retry_on_result=lambda status: check_node(request, self.HTTP_HEADER).json()
                     .get('executionState') != 'SUCCEEDED').call(check_node, request)
        except Exception as e:
            abort("The {} node cannot be disabled:\n{}".format(node, e))

        print("The {} node is disabled".format(node))


def deploy_kirin_container_safe(server, node_manager):
    """ Restart kirin on a specific server,
        in a safe way if load balancers are available
    """
    with settings(host_string=server):
        node_manager.disable_node(server)
        migrate('docker-compose_kirin.yml')
        restart('docker-compose_kirin.yml')
        test_deployment()
        node_manager.enable_node(server)


def deploy_kirin_beat_container_safe(server):
    """ Restart kirin on a specific server
    """
    with settings(host_string=server):
        restart('docker-compose_kirin-beat.yml')


def update_kirin():
    """ Retrieve new kirin image
    To tag the image, we pull the previous tag, tag it as our own and push it
    """
    run('docker pull {image}:{prev_tag}'.format(image=env.docker_image_kirin, prev_tag=env.previous_docker_tag))
    run('docker tag {image}:{prev_tag} {image}:{new_tag}'
        .format(image=env.docker_image_kirin, prev_tag=env.previous_docker_tag, new_tag=env.current_docker_tag))
    run('docker push {image}:{new_tag}'.format(image=env.docker_image_kirin, new_tag=env.current_docker_tag))


@task
def deploy():
    """
    Deploy Kirin services
    """
    deploy_kirin()
    deploy_kirin_beat()


@task()
@roles('kirin-beat')
def deploy_kirin_beat():
    """
    Deploy Kirin beat
    :return:
    """
    if len(env.roledefs['kirin-beat']) != 1:
        abort('Error : Only one beat can exist, you provided kirin-beat role on {}'.format(env.roledefs['kirin-beat']))

    upload_template('kirin.env', '{}'.format(env.path), context={'env': env})
    upload_template('docker-compose_kirin-beat.yml', '{}'.format(env.path), context={'env': env})

    # Deploy NewRelic
    if env.new_relic_key:
        upload_template('newrelic.ini', '{}'.format(env.path), context={'env': env})

    update_kirin()

    deploy_kirin_beat_container_safe(env.host_string)

    # need to wait between both node execution because using same token
    time.sleep(5)


@task()
@roles('kirin')
def deploy_kirin():
    """
    Deploy Kirin
    :return:
    """

    if env.use_load_balancer:
        node_manager = SafeDeploymentManager()
    else:
        node_manager = NoSafeDeploymentManager()

    upload_template('kirin.env', '{}'.format(env.path), context={'env': env})
    upload_template('docker-compose_kirin.yml', '{}'.format(env.path), context={'env': env})

    # Deploy NewRelic
    if env.new_relic_key:
        upload_template('newrelic.ini', '{}'.format(env.path), context={'env': env})
    update_kirin()

    deploy_kirin_container_safe(env.host_string, node_manager)

    # need to wait between both node execution because using same token
    time.sleep(5)


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


def migrate(compose_file, revision='head'):
    run('docker-compose -f {} run --rm --no-deps kirin ./manage.py db upgrade {}'.format(compose_file, revision))


def restart(compose_file):
    """ Restart containers properly """
    stop_container(compose_file)
    remove_container(compose_file)
    remove_targeted_images()
    start_container(compose_file)


def test_deployment():
    """ Verify api kirin is OK """

    header = {'Host': env.kirin_host}
    request = 'http://{}/status'.format(env.host_string)

    try:
        Retrying(stop_max_delay=30000,
                 wait_fixed=100,
                 retry_on_result=lambda status: check_node(request, header).status_code != 200)\
            .call(check_node, request)
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
