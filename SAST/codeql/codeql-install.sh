#!/bin/bash
VERSION_LIST_FILE=$1

mkdir ./codeql

yq eval -M '{.versions}' $VERSION_LIST_FILE  | xargs -n2 | while read NAME LINK; do

    wget $LINK
    tar -xvzf ./codeql-bundle-linux64.tar.gz -C ./codeql && rm ./codeql-bundle-linux64.tar.gz
    mv ./codeql/codeql ./codeql/$NAME

    ./codeql/$NAME/codeql resolve languages
    ./codeql/$NAME/codeql resolve qlpacks
done
