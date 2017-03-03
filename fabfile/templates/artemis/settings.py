#URI for postgresql
# postgresql://<user>:<password>@<host>:<port>/<dbname>
#http://docs.sqlalchemy.org/en/rel_0_9/dialects/postgresql.html#psycopg2
SQLALCHEMY_DATABASE_URI = 'postgresql://{{env.user_kirin_postgres}}:{{env.pwd_kirin_postgres}}' \
                          '@{{env.tyr_postgres_database}}/{{env.kirin_postgres_database}}'

NAVITIA_URL = '{{env.navitia_url}}'

NAVITIA_INSTANCE = '{{env.navitia_instance}}'

NAVITIA_TOKEN = '{{env.navitia_token}}'

CONTRIBUTOR = 'realtime.ire'

DEBUG = False

#rabbitmq connections string: http://kombu.readthedocs.org/en/latest/userguide/connections.html#urls
RABBITMQ_CONNECTION_STRING = 'pyamqp://{{env.user_rabbitmq}}:{{env.pwd_rabbitmq}}@{{env.rabbitmq_url}}:5672//'

#amqp exhange used for sending disruptions
EXCHANGE = 'navitia'

ENABLE_RABBITMQ = True
