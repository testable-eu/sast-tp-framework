#!/usr/bin/env bash

VERSION_LIST_FILE=$1
CODEQL_DIR=/codeql

mkdir $CODEQL_DIR

# Make sure the file contains a newline at the end
echo -en '\n' >> "$VERSION_LIST_FILE"

name=""
link=""
# Read the VERSION_LIST_FILE line by line
while IFS=: read -r key value; do
  # Remove leading/trailing spaces from the key and value (remove " as well)
  key=$(echo "$key" | xargs)
  value=$(echo "$value" | xargs | tr -d '\"')

  # Check if the line contains "link" or "name" field
  if [[ "$key" == "link" ]]; then
    link=$value
  elif [[ "$key" == "name" ]]; then
    name=$value
  fi

  # Check if both name and link are set
  if [[ -n "$name" && -n "$link" ]]; then
    # Download the codeql version using wget, extract it and move it to the codeql directory
    echo "Downloading $name from $link"
    wget -q "$link"
    tar -xzf ./codeql-bundle-linux64.tar.gz -C "$CODEQL_DIR"
    mv "$CODEQL_DIR/codeql" "$CODEQL_DIR/$name"

    # setup codeql version
    "$CODEQL_DIR/$name/codeql" resolve languages
    "$CODEQL_DIR/$name/codeql" resolve qlpacks

    # remove the downloaded .tar.gz
    rm ./codeql-bundle-linux64.tar.gz

    # Reset the variables for the next entry
    name=""
    link=""
  fi
done < "$VERSION_LIST_FILE"
