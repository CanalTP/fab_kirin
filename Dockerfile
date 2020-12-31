FROM python:3.9.1-slim

# add docker cli
ARG DOCKER_VERSION="5:19.03.13~3-0~debian-buster"
RUN BUILD_DEPENDENCIES="apt-transport-https ca-certificates curl gnupg-agent software-properties-common" \
	&& apt update \
	&& apt install --yes ${BUILD_DEPENDENCIES} \
	&& curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add \
	&& add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
	&& apt update \
	&& apt -y install docker-ce-cli=${DOCKER_VERSION} \
	&& apt -y purge ${BUILD_DEPENDENCIES} \
	&& apt autoremove --yes \
	&& rm -rf /var/lib/apt/lists/*

# install dependencies for kirin fabric
COPY requirements.txt /
RUN pip install -r /requirements.txt -U

# set current workspace in PythonPath to be able to find later configuration files
ENV PYTHONPATH=.

# setup kirin fabric
RUN mkdir /fabfile
COPY fabfile /fabfile
RUN echo "fabfile = /fabfile/fabfile.py" > ~/.fabricrc

ENTRYPOINT [ "fab" ]
