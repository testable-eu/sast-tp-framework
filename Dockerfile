FROM malt33/php-cpg

WORKDIR /tp-framework

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata

RUN apt-get update
RUN apt-get install python3 python3-pip python-is-python3 -y
RUN apt-get install php -y
RUN apt-get install gradle -y
RUN apt-get install maven -y
# discovery, joern: js2cpg
RUN apt-get install nodejs -y
RUN apt-get install npm -y
# sudo required to correctly set up symlinks with joern-install.sh
RUN apt-get install sudo -y

ARG TPF_HOME="/tp-framework"
ARG SAST_DIR="${TPF_HOME}/SAST"
ARG DISCOVERY_HOME="${TPF_HOME}/discovery"

COPY tp_framework ${TPF_HOME}/tp_framework
COPY testability_patterns ${TPF_HOME}/testability_patterns

COPY config.py ${TPF_HOME}/config.py
COPY setup.py ${TPF_HOME}/setup.py
COPY pytest.ini ${TPF_HOME}/pytest.ini
COPY SAST/requirements.txt ${SAST_DIR}/requirements.txt
COPY SAST/sast-config.yaml ${SAST_DIR}/sast-config.yaml

ARG TESTS_DIR
COPY ${TESTS_DIR} ${TPF_HOME}/${TESTS_DIR}

ARG REQUIREMENTS_FILE
COPY ${REQUIREMENTS_FILE} ${TPF_HOME}/${REQUIREMENTS_FILE}
RUN pip install -r ${TPF_HOME}/${REQUIREMENTS_FILE}

COPY discovery ${DISCOVERY_HOME}
RUN chmod +x ${DISCOVERY_HOME}/joern/joern/joern-install.sh
RUN /bin/sh -c 'cd ${DISCOVERY_HOME}/joern/joern/ && ./joern-install.sh --version=v1.1.1269 --install-dir=/opt/joern'

#install js2cpg
RUN /bin/sh -c 'cd ${DISCOVERY_HOME}/joern/js2cpg/; sbt stage'


# ADD HERE COMMANDS USEFUL FOR OTHER DOCKER-COMPOSE SERVICES
#

ENV PYTHONPATH "${PYTHONPATH}:${TPF_HOME}/tp_framework"

RUN python setup.py develop

ENTRYPOINT [ "bash" ]