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
ARG DISCOVERY_HOME="${TPF_HOME}/discovery"

COPY tp_framework ${TPF_HOME}/tp_framework
COPY testability_patterns ${TPF_HOME}/testability_patterns

COPY SAST/sast /SAST/sast
COPY SAST/sast.py ${TPF_HOME}/
COPY SAST/requirements.txt ${TPF_HOME}/SAST/

COPY config.py ${TPF_HOME}/config.py
COPY setup.py ${TPF_HOME}/setup.py
COPY pytest.ini ${TPF_HOME}/pytest.ini

ARG TESTS_DIR="qualitytests"
COPY ${TESTS_DIR}/requirements.txt ${TPF_HOME}/${TESTS_DIR}/requirements.txt

ARG REQUIREMENTS_FILE
COPY ${REQUIREMENTS_FILE} ${TPF_HOME}/${REQUIREMENTS_FILE}
RUN pip install -r ${TPF_HOME}/${REQUIREMENTS_FILE}

ARG JOERN_VERSION="v1.1.1709"
RUN echo ${JOERN_VERSION}
COPY discovery ${DISCOVERY_HOME}
RUN chmod +x ${DISCOVERY_HOME}/joern/joern-install.sh
RUN /bin/sh -c 'cd ${DISCOVERY_HOME}/joern/ && ./joern-install.sh --version=${JOERN_VERSION} --install-dir=/opt/joern --reinstall --without-plugins'

# ADD HERE COMMANDS USEFUL FOR OTHER DOCKER-COMPOSE SERVICES

ENV PYTHONPATH "${PYTHONPATH}:${TPF_HOME}/tp_framework"
ENV PYTHONPATH "${PYTHONPATH}:/SAST"

RUN python setup.py develop

ENTRYPOINT [ "bash" ]
