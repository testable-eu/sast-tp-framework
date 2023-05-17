################################################################################
# base system
################################################################################

FROM adoptopenjdk/openjdk11

ARG TPF_HOME="/tp-framework"
ARG CODEQL_INTERFACE_DIR="${TPF_HOME}/SAST/codeql"


COPY . ${CODEQL_INTERFACE_DIR}

RUN apt-get update
RUN apt-get install wget

#codeql v2.9.2
RUN wget https://github.com/github/codeql-action/releases/download/codeql-bundle-20220512/codeql-bundle-linux64.tar.gz
RUN tar -xvzf ./codeql-bundle-linux64.tar.gz && rm ./codeql-bundle-linux64.tar.gz
RUN mv ./codeql ./codeql_v2_9_2

RUN ./codeql_v2_9_2/codeql resolve languages
RUN ./codeql_v2_9_2/codeql resolve qlpacks

#codeql v2.13.1
RUN wget https://github.com/github/codeql-action/releases/download/codeql-bundle-20230428/codeql-bundle-linux64.tar.gz
RUN tar -xvzf ./codeql-bundle-linux64.tar.gz && rm ./codeql-bundle-linux64.tar.gz
RUN mv ./codeql ./codeql_v2_13_1

RUN ./codeql_v2_13_1/codeql resolve languages
RUN ./codeql_v2_13_1/codeql resolve qlpacks