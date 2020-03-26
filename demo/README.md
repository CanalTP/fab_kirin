# fab_kirin local demo
Deploy kirin locally

The goal is to showcase local deployment of Kirin using mostly the same mechanism
than for any other platform.  
Please adapt to your needs (location of dependencies, navitia, passwords, params...).
Note that `local_dockerized_deps` overloads `base` values.


## Use

First build a Kirin image from sources, tagged `kirin:local` as described in
https://github.com/CanalTP/kirin#docker.

Provide a Navitia instance, running on `localhost:5000` and reachable from within a container
(maybe change flask's host to `0.0.0.0` to allow that).

Make sure that user `navitia` has read/write access to RabbitMQ's vhost used by
Kraken (`/` in current conf)

Install python dependencies (using a virtualenv is recommended) with:
```bash
cd /path/to/fab_kirin
pip install -r requirements.txt -U
```

Create docker network named `kirin_network`:
```bash
docker network create kirin_network
```

Create and run containers for dependencies:
```bash
docker-compose -f demo/deps/docker-compose_deps.yml up -d
```

For a first-time deployment:
```bash
PYTHONPATH=demo/conf fab use:local_dockerized_deps deploy:first_time=True
```

You should now be able to request successfully (everything should be OK):
```bash
curl localhost:54746/status
```

Enjoy, you can now create a contributor, and use it.
