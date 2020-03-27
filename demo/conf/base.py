from fabric.api import *

env.docker_image_kirin = 'navitia/kirin'

env.kirin_host = 'localhost'  # global host
env.kirin_host_port = '9090'
env.kirin_docker_port = '9090'

env.path = '~/fab_kirin_workspace'  # directory must be available on host
env.is_local = False

env.new_relic_key = None

env.postgres_database = 'localhost'  # Postgres, must be reachable from container
env.postgres_port = 5432
env.user_kirin_postgres = 'kirin'
env.pwd_kirin_postgres = 'kirin'
env.kirin_postgres_database = 'kirin'

env.rundeck_token = None

env.rabbitmq_url = 'localhost'  # Navitia RabbitMQ, must be reachable from container
env.rabbitmq_port = 5672
env.user_rabbitmq = 'navitia'
env.pwd_rabbitmq = 'navitia'
env.rabbitmq_vhost = 'navitia'  # vhost to communicate with Navitia (Kraken)
env.heartbeat_rabbitmq = 180

# Kirin's Celery RabbitMQ, must be reachable from container
env.celery_broker_url = 'pyamqp://kirin:kirin@localhost:5672//?heartbeat=60'

env.use_logger = False
env.use_syslog = True
env.use_json = True

env.redis_host = 'localhost'  # Redis, must be reachable from container
env.redis_port = 6379
env.redis_password = ''  # No password is needed by default

env.docker_network = 'kirin_network'

env.cots_par_iv_circuit_breaker_max_fail = 4
env.cots_par_iv_circuit_breaker_timeout_s = 60
env.cots_par_iv_timeout_token = 30*60
env.cots_par_iv_cache_timeout = 60*60
env.cots_par_iv_request_timeout = 2
env.gtfs_rt_timeout = 5


# Deprecated vars (TODO: remove)
env.cots_contributor = None
env.navitia_instance = None

env.navitia_gtfs_rt_instance = None
env.navitia_gtfs_rt_token = None
env.gtfs_rt_contributor = None
env.gtfs_rt_feed_url = None
