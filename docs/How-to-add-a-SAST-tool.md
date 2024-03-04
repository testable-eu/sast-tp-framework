# How to: Add a SAST tool

The framework uses the arsenal of all the SAST tools provided in the `SAST` module.

To add a SAST tools to your arsenal, please follows the steps listed hereafter and detailed in the chapters below:

[**1. Add sast tool the SAST module**](https://github.com/testable-eu/SAST/blob/main/README.md): Add the tool here.

[**2. Docker**](#2-docker): create a specific dockerfile and add a service to the docker-compose

## 2. Docker

The entire tp-framework is based on docker-compose. The installation of a SAST tool is done as a docker-compose service that invokes a Dockerfile. As such the dockerization of a new SAST tool requires the following sub-steps:

**4.1. docker-compose files**: edit the main `docker-compose` files

**4.2. Composition/sharing corner-cases**: we experienced some corner-cases situations whose solution can be helpful for you as well

### 4.1. docker-compose files

The `./docker-compose.yml` file in the root folder has to be modified to add the new SAST tool. In particular, a new service is added (cf. `codeql`) specifying the image, the build folder (SAST folder path) and eventually the shared volumes with the framework. This is marked with the `# ADD` comment in the example hereafter:

```yml
version: "3.9"

services:
  codeql: # ADDED: NEW SERVICE FOR SAST TOOL
    image: tpf_codeql
    build:
      context: './SAST/sast/codeql/codeql_v2_9_2'
      dockerfile: "./Dockerfile"
      args: 
        HOME: '/SAST'
    volumes:
      - codeql_v2_9_2:/codeql

  tp-framework:
    build:
      context: .
      args:
        REQUIREMENTS_FILE: "requirements.txt"
        TESTS_DIR: "config.py" # fake tests directory to prevent copying `tests` in production
      dockerfile: "./Dockerfile"
    env_file:
      - ./.env
    volumes:
      - codeql_v2_9_2:/codeql # ADDED: SAST TOOL VOLUME USED BY tp-framework SERVICE
      - ./testability_patterns:/tp-framework/testability_patterns
      - ./out:/tp-framework/out
      - ./in:/tp-framework/in
    entrypoint: bash

volumes:
  codeql_v2_9_2: # ADDED
```

An `./.env` file is available for environment variables. This can be useful to solve some of the corner-cases we experienced (see section below).

Also notice that the same additions will need to be migrated into the `docker-compose-dev.yml` file (this may be automated one day).

### 4.2. Composition/sharing corner-cases

We experienced some corner-cases situations whose solutions can be helpful for you as well. Here some cases:

#### SAST tool requiring some sensitive info

Let us assume your SAST tool requires some info that should not be hardcoded in the docker files, for instance some credential.

- create a specific `.env.sast_to_add.template` file into the folder `.env.templates` to add few environment variables

```env
SAST_USER_VAR=<SAST_USER_VAR_VALUE>
SAST_PWD_VAR=<SAST_PWD_VAR_VALUE>
```

- of course do not provide the real values for those variables as you do not want those sensitive values to end up in a repository or similar
- at deployment time all these environment variables will be properly migrated into the main `.env` file and their values will be instantiated

```env
SAST_USER_VAR=john@example.com
SAST_PWD_VAR=abcd1234
```

- The python code implemented for your SAST tool can make use of these values by using:

```env
SAST_USER_VAR= os.environ["SAST_USER_VAR"]
SAST_PWD_VAR= os.environ["SAST_PWD_VAR"]
```

#### SAST tool requiring specific python packages

The installation of the python packages is done only once by the `Dockerfile` of the tp-framework. As such installing these python packages via the SAST tool `Dockerfile` would not work.

- add the python packages that your SAST tool requires within `SAST\requirements.txt`
- do not point to another `sast-tool-specific-requirements.txt` file as it will not work

#### SAST tool requiring specific commands to be executed in the main Dockerfile

Some SAST tools may require commands to be executed in the `./Dockerfile` of the tp-framework. For instance, a SaaS SAST tool may require some certificates to be properly invoked.

- open the `./Dockerfile` and add the needed commands in the specific section, as here:

```dockerfile
...
# ADD HERE COMMANDS USEFUL FOR OTHER DOCKER-COMPOSE SERVICES
## SAST tool foo service
COPY --from=tpf_foo /usr/local/share/ca-certificates /usr/local/share/ca-certificates
RUN update-ca-certificates
##
#
...
```
