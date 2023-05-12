################################################################################
# base system
################################################################################

FROM adoptopenjdk/openjdk11

ARG TPF_HOME="/tp-framework"
ARG CODEQL_INTERFACE_DIR="${TPF_HOME}/SAST/codeql/codeql_v2_13_1"

COPY ./__init__.py ${CODEQL_INTERFACE_DIR}/__init__.py
COPY ./config.yaml ${CODEQL_INTERFACE_DIR}/config.yaml
COPY ./codeql.py ${CODEQL_INTERFACE_DIR}/codeql.py
COPY ./resources ${CODEQL_INTERFACE_DIR}/resources

RUN apt-get update
RUN apt-get install wget

RUN wget https://github.com/github/codeql-action/releases/download/codeql-bundle-20230428/codeql-bundle-linux64.tar.gz
RUN tar -xvzf ./codeql-bundle-linux64.tar.gz

RUN ./codeql/codeql resolve languages
RUN ./codeql/codeql resolve qlpacks