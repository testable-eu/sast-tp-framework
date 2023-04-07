# How to: Add a SAST tool

The framework uses the arsenal of all the SAST tools provided in the `SAST/` folder.

To add a SAST tools to your arsenal, please follows the steps listed hereafter and detailed in the chapters below:

[**1. File system structure**](#1-file-system-structure): comply with the recommended file system structure

[**2. Config files**](#2-config-files): prepare the config files

[**3. Implement the SAST interface**](#3-implement-the-sast-interface): python interface of the `tp_framework/core/sast.py` needs to be implemented

[**4. Docker**](#4-docker): create a specific dockerfile and add a service to the docker-compose

We illustrate all the steps hereafter by using the CodeQL v2.9.2 SAST tool as example.  

> At the time of writing, CodeQL is free for research and open source, https://codeql.github.com/

## 1. File system structure

The following file system structure is recommended:

```text
|__SAST
   |__sast-config.yaml   
   |__codeql
   |  |__codeql_v2.9.2
   |  |  |__resources
   |  |  |__config.yaml
   |  |  |__codeql.py
   |  |  |__Dockerfile
   |  |  
   |  |__codeql_vX.Y.Z
   |     |__...
   |
   |__another_sast_tool
      |__resources
      |__config.yaml
      ...
```

## 2. Config files

### Main config file

Each SAST tool needs to be declared in the main `SAST/sast-config.yaml`

```yml
tools:
  codeql:
    version:
      2.9.2:
        config: "./codeql/codeql_v2.9.2/config.yaml"
        deploy: true
      X.Y.Z:
        ...
  another_sast_tool:
    version:
      saas:
        config: "./another_sast_tool/config.yaml"
        deploy: false
```

In the above, an entry for CodeQL v2.9.2 is provided that specifies:

- the config file for that tool is `./codeql/codeql_v2.9.2/config.yaml`
- that tool should be deployed.

Some SAST tools are only available as SaaS so that is not possible to use multiple versions for them. The keyword `saas` as version specified that the tool is served as SaaS. When `deploy` is set to `false`, the tool will be neither deployed nor used within the framework.  

### SAST tool config file

Each SAST tool will need to have its own `config.yaml` as follows:

```yaml
name: "codeql"
version: "2.9.2"
supported_languages:
  - "JS"
  - "JAVA"
  - "PYTHON"
  - "RUBY"
  - "CPP"
  - "CSHARP"
  - "GO"
tool_interface: "SAST.codeql.codeql_v2_9_2.codeql.CodeQL_v_2_9_2"
supported_vulnerability:
  xss: "xss"

# Specific SAST config parameters
installation_path: "/codeql"
```

Most of the fields are self-explanatory. Hereafter some details for the others:

- `tool_interface` specifies where is the class instance implementing the SAST tool interface. In this specific case the class `CodeQL_v_2_9_2` is declared in the file `codeql.py` that is in the folder `./SAST.codeql.codeql_v2_9_2/`
- `supported_vulnerability` specifies the mapping between the vulnerabilities targeted by our framework and the way these vulnerabilities are represented within the SAST tool. In the specific example, the `xss` vulnerability is represented with the string `"xss"` in codeql, but other tools represent that with e.g., `"Cross-Site Scripting"`.
- `installation_path` indicates the path where the SAST tool will be installed on the docker container.

## 3. Implement the SAST interface

The python interface of the `SAST` class in `tp_framework/core/sast.py` needs to be implemented. This mainly requires the implementation of the following methods:

- `launcher`: script to scan an application with the SAST tool to add, and
- `inspector`: script to inspect the findings from the SAST tool to add.

### Launcher

The launcher runs the SAST analysis and needs to implement this abstract method:

```python
@abc.abstractmethod
async def launcher(self, src_dir: Path, language: str, **kwargs) -> Path:
    raise NotImplementedError
```

Inputs:

- `src_dir` is the path to the project to be scanned with SAST
- `language` is the programming language targeted by the SAST analysis
- `**kwargs` are specific arguments that could be used by the specific SAST tool

Output:

- path to the result file that will be then inspected

## Inspector

The inspector inspects the output of the SAST analysis to make it available to the tp-framework in a precise normalized format. It implements the following:

```python
@abc.abstractmethod
def inspector(self, sast_res_file: Path, language: str) -> list[Dict]:
    raise NotImplementedError
```

Inputs:

- `sast_res_file`: path to the result file obtained by a launched scan
- `language` is the programming language targeted by the SAST analysis

Output:

- a list of dict entries complying with the format hereafter:

```list
[
 {
   type: "xss",
   file: "foo.php",
   line: "15"
 },
 {
   type: "sqli",
   file: "whatever.php",
   line: "169"
 },

...
]
```

The first entry in the list above specifies that an cross-site scripting (`xss`) finding is reported for file `foo.php` at line `15` (sink of the `xss`)

The types of vulnerabilities (`type`) currently supported by our framework are:
| normalized type   | natural language      |
|-------------------|-----------------------|
| xss               | Cross-Site Scripting  |
| sqli              | SQL Injection         |
| command_injection | Command Injection     |
| path_manipulation | Path Manipulation     |

## 4. Docker

The entire tp-framework is based on docker-compose. The installation of a SAST tool is done as a docker-compose service that invokes a Dockerfile. As such the dockerization of a new SAST tool requires the following sub-steps:

**4.1. docker-compose files**: edit the main `docker-compose` files

**4.2. Dockerfile**: create the `Dockerfile` for the SAST tool

**4.3. Composition/sharing corner-cases**: we experienced some corner-cases situations whose solution can be helpful for you as well

### 4.1. docker-compose files

The `./docker-compose.yml` file in the root folder has to be modified to add the new SAST tool. In particular, a new service is added (cf. `codeql`) specifying the image, the build folder (SAST folder path) and eventually the shared volumes with the framework. This is marked with the `# ADD` comment in the example hereafter:

```yml
version: "3.9"

services:
  codeql: # ADDED: NEW SERVICE FOR SAST TOOL
    image: tpf_codeql
    build:
      context: './SAST/codeql/codeql_v2_9_2'
      dockerfile: "./Dockerfile"
    volumes:
      - codeql_v2_9_2:/codeql
      - codeql_interface_v2_9_2:/tp-framework/SAST/codeql/codeql_v2_9_2

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
      - codeql_interface_v2_9_2:/tp-framework/SAST/codeql/codeql_v2_9_2 # ADDED: "
      - ./testability_patterns:/tp-framework/testability_patterns
      - ./out:/tp-framework/out
      - ./in:/tp-framework/in
    entrypoint: bash

volumes:
  codeql_v2_9_2: # ADDED
  codeql_interface_v2_9_2: # ADDED
```

An `./.env` file is available for environment variables. This can be useful to solve some of the corner-cases we experienced (see section below).

Also notice that the same additions will need to be migrated into the `docker-compose-dev.yml` file (this may be automated one day).

### 4.2. Dockerfile

The Dockerfile shall specify the operations to execute in order to install the SAST tool and make it available for the tp-framework. Hereafter the example for Codeql.

```dockerfile
FROM adoptopenjdk/openjdk11

ARG TPF_HOME="/tp-framework"
ARG CODEQL_INTERFACE_DIR="${TPF_HOME}/SAST/codeql/codeql_v2_9_2"

COPY ./__init__.py ${CODEQL_INTERFACE_DIR}/__init__.py
COPY ./config.yaml ${CODEQL_INTERFACE_DIR}/config.yaml
COPY ./codeql.py ${CODEQL_INTERFACE_DIR}/codeql.py
COPY ./resources ${CODEQL_INTERFACE_DIR}/resources

RUN apt-get update
RUN apt-get install wget

RUN wget https://github.com/github/codeql-action/releases/download/codeql-bundle-20220512/codeql-bundle-linux64.tar.gz
RUN tar -xvzf ./codeql-bundle-linux64.tar.gz

RUN ./codeql/codeql resolve languages
RUN ./codeql/codeql resolve qlpacks
```

### 4.3. Composition/sharing corner-cases

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
