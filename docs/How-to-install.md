We recommend using docker compose to install our framework, as explained hereafter.  

### 0. Requirements

#### General requirements
- [Docker](https://docs.docker.com/get-docker/).
- [Joern CPG for PHP](https://github.com/joernio/querydb-php): you need to have access to this private repository (authentication through SSH). If you have not, get in touch with us. 

#### SAST Tools requirements 

Our public framework is set to work with the SAST tools listed below.   

- CodeQL v2.9.2: open source, no specific requirements. 

You can contribute by [adding an interface to a new SAST tool](./How-to-add-a-SAST-tool.md). If you do so, add the tool to the list here and report its requirements (if any).

### 1. Cloning

Clone our repository in your `<REPO>` folder and update submodules to last version with:
```buildoutcfg
git clone -c core.autocrlf=false --recurse-submodules git@github.wdf.sap.corp:sast-testability-patterns/tp-framework.git
git submodule update --remote
```

Note that some submodules will also be pulled, including:
- [Joern CPG for PHP](https://github.com/joernio/querydb-php)
- [Joern CPG for JS](https://github.com/ShiftLeftSecurity/js2cpg)
- [Joern](https://github.com/joernio/joern)
- [Testability Pattern Library](https://github.com/testable-eu/sast-tp-framework)

### 2. Setup

#### SAST Tools
Some SAST tools may require a little setup before running. If you add a SAST tool report here those setup steps.  

#### Environment variables
Create the file `./.env` necessary for docker. This will be the concatenation of all the files you have in 
`./.env.templates`.   Even if there are no specific environment variables, you need to create an empty `./.env` 
file (e.g., `touch .env`). 
   
### 3. Docker compose: build 
By running the following, the TP framework will be built and ready to be run 
```bash
docker-compose up --build
```

> [NOTE] the build command may take a while, even 20 minutes

### 4. Docker compose: run
By running the following, the TP-framework will be running and a shell terminal will be started:  
```bash
docker-compose run -d --name <CONTAINER_NAME> tp-framework
docker exec -it <CONTAINER_NAME> bash
```

### 5. How to run - overview
The complete documentation about how-to-run this framework is available [here](./How-to-run-CLI-Usage.md). 

Here we only provide a little overview of the framework and ensure that it works fine.

If you followed the instruction above, the tp-framework is running via docker compose 
- linux based environment
- a few volumes are exposed to the host machine to enable the user to (i) access from the host machine SAST reports and other artifacts generated via the framework, (ii) add an application source code to be analysed via the framework, etc.

The framework CLI can be called with the command `tpframework`

You can run the following to see the help and ensure the framework is properly working and print the usage.  
```bash
tpframework -h
```

## FAQ 

### About:  4. Docker compose: run
- avoid to run from git bash terminal, as the shell is not started