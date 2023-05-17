################################################################################
# base system
################################################################################

FROM alpine

ARG TPF_HOME="/tp-framework"
ARG CODEQL_CORE_INTERFACE_DIR="${TPF_HOME}/SAST/codeql/core"

COPY ./__init__.py ${CODEQL_CORE_INTERFACE_DIR}/__init__.py
COPY ./codeql_core.py ${CODEQL_CORE_INTERFACE_DIR}/codeql_core.py
COPY ./resources ${CODEQL_CORE_INTERFACE_DIR}/resources

