from fabric.api import *
import base


def local_dockerized_deps():
    env.name = 'local_dockerized_deps'
    env.path = '~/fab_kirin_workspace'  # directory must be available on host
    env.is_local = True

    env.roledefs = {
        'kirin': ['localhost'],
        'kirin-beat': ['localhost']
    }

    env.kirin_host = '172.17.0.1'  # as seen from `ip a` -> docker0 -> inet value (host IP from container)
    env.kirin_host_port = '54746'

    env.docker_image_kirin = 'kirin'
    env.previous_docker_tag = 'local'  # tag of the image to deploy
    env.current_docker_tag = 'local'  # same, as no platform-chaining is done

    env.use_load_balancer = False

    env.navitia_url = 'http://172.17.0.1:5000/'  # Navitia on host, must be reachable from container

    env.postgres_database = '172.17.0.1'
    env.postgres_port = 35432
    env.user_kirin_postgres = 'kirin'
    env.pwd_kirin_postgres = 'kirin'

    env.redis_host = '172.17.0.1'
    env.redis_port = 36379
    env.redis_db = 1

    env.rabbitmq_url = '172.17.0.1'  # Navitia RabbitMQ on host, must be reachable from container
    env.user_rabbitmq = 'navitia'
    env.pwd_rabbitmq = 'navitia'
    env.rabbitmq_vhost = '/'

    env.celery_broker_url = 'pyamqp://guest:guest@172.17.0.1:35672//?heartbeat=60'

    env.use_logger = True
    env.use_syslog = False
