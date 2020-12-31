# fab_kirin
Kirin's deployment mechanisms

## Invocation

### from source code with a working setup

For a regular deployment (on a platform with Kirin already running):
```bash
PYTHONPATH=/path/to/kirin_deployment_conf/ fab use:<platform_file_name> deploy
```

For a first-time deployment on an empty platform:
```bash
PYTHONPATH=/path/to/kirin_deployment_conf/ fab use:<platform_file_name> deploy:first_time=True
```

### using Docker image

Same principle as above for `fabric` usage, but this is an example to focus on specific options to use for Docker:

``` bash
docker run --volume "/var/run/docker.sock:/var/run/docker.sock" --volume "/path/to/folder/containing/kirin/<platform_file_name>.py:/kirin_conf" --workdir "/kirin_conf" navitia/fab_kirin use:<platform_file_name> deploy
```

The Docker socket is required since some Docker commands are run by `fabric`.

The other volume is used to share `<platform_file_name>.py`. The `workdir` option must be set to the same value than the target of the shared volume to make the `<platform_file_name>.py` reachable by `fabric`.

## Usage

### Demo

A demo for local deployment is available, please see [instructions](demo/README.md).

### deployment files

File should look like:

```python
from fabric.api import *
import common


def prod():
    env.name = 'prod'

    env.roledefs = {
        'kirin': ['<user>@<kirin_platform1>', '<user>@<kirin_platform2>'],
        'kirin-beat': ['<user>@<kirin-beat_platform>']  # only one beat can exist
    }

    env.kirin_host = '<kirin_host_name>'

    env.previous_docker_tag = '<prev_tag>'
    env.current_docker_tag = '<prod_tag>'

    env.use_load_balancer = True  # or False

    env.postgres_database = '<SQL_db_platform>'
    env.navitia_url = 'https://api.navitia.io'
    env.rabbitmq_url = '<rabbitmq_platform>'  # rabbitmq where disruptions are published for navitia

    env.celery_broker_url = 'pyamqp://<user>:<mdp>@<platform>:<port>/<vhost>?heartbeat=60'  # beware to open access to vhost for user in rabbitmq (for beat-worker communication)

    env.use_logger = True

    env.cots_par_iv_api_key = '<cots-api-key>'
    env.cots_par_iv_motif_resource_server = '<ParIV-motif-url>'
    env.cots_par_iv_token_server = '<ParIV-token-url>'
    env.cots_par_iv_client_id = '<ParIV-username'
    env.cots_par_iv_client_secret = '<ParIV-password>'

    env.cots_par_iv_circuit_breaker_max_fail = 4
    env.cots_par_iv_circuit_breaker_timeout_s = 60
    env.cots_par_iv_timeout_token = 30*60
    env.cots_par_iv_cache_timeout = 60*60
    env.cots_par_iv_request_timeout = 2
```
