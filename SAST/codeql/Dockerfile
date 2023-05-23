################################################################################
# base system
################################################################################

FROM adoptopenjdk/openjdk11

ARG TPF_HOME="/tp-framework"
ARG CODEQL_INTERFACE_DIR="${TPF_HOME}/SAST/codeql"


COPY . ${CODEQL_INTERFACE_DIR}

RUN apt-get update
RUN apt-get install wget

#codeql installation
RUN wget https://github.com/mikefarah/yq/releases/download/v4.2.0/yq_linux_amd64.tar.gz -O - | tar xz && mv yq_linux_amd64 /usr/bin/yq
RUN ${CODEQL_INTERFACE_DIR}/codeql-install.sh ${CODEQL_INTERFACE_DIR}/codeql-versions-list.yaml