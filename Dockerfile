FROM python:3.10

WORKDIR /tp-framework

RUN apt-get update

RUN echo "deb https://repo.scala-sbt.org/scalasbt/debian all main" | tee /etc/apt/sources.list.d/sbt.list
RUN echo "deb https://repo.scala-sbt.org/scalasbt/debian /" | tee /etc/apt/sources.list.d/sbt_old.list
RUN curl -sL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2EE0EA64E40A89B84B2DF73499E82A75642AC823" | gpg --no-default-keyring --keyring gnupg-ring:/etc/apt/trusted.gpg.d/scalasbt-release.gpg --import
RUN chmod 644 /etc/apt/trusted.gpg.d/scalasbt-release.gpg

RUN apt-get update
RUN apt-get install openjdk-11-jdk -y
RUN apt-get install php -y
RUN apt-get install sbt -y
RUN apt-get install gradle -y
RUN apt-get install maven -y
# discovery, joern: js2cpg
RUN apt-get install nodejs
RUN apt-get install npm

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
RUN ${DISCOVERY_HOME}/joern/joern/joern-install.sh
RUN ln -s /opt/joern/joern-cli/joern /usr/local/bin/joern
RUN chmod +x ${DISCOVERY_HOME}/joern/querydb-php/install.sh
RUN ${DISCOVERY_HOME}/joern/querydb-php/install.sh
#install js2cpg
RUN /bin/sh -c 'cd ${DISCOVERY_HOME}/joern/js2cpg/; sbt stage'


# ADD HERE COMMANDS USEFUL FOR OTHER DOCKER-COMPOSE SERVICES
#

ENV PYTHONPATH "${PYTHONPATH}:${TPF_HOME}/tp_framework"

RUN python setup.py develop

ENTRYPOINT [ "bash" ]