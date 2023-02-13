# TP-Framework: Testability Pattern Framework for SAST
[![Python](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/download/releases/3.10/) [![Generic badge](https://img.shields.io/badge/dockerized-yes-<COLOR>.svg)](https://shields.io/) [![GPLv3 license](https://img.shields.io/badge/License-GPLv3-blue.svg)](http://perso.crans.org/besson/LICENSE.html)

TP-Framework relies on [testability patterns](https://github.com/testable-eu/sast-testability-patterns) to reduce false positive/negative rate in SAST analysis over supported programming languages. Testability patterns are code patterns that make difficult for SAST tools to detect a vulnerability.

TP-Framework enables operations such as:
- measurement of SAST tools against a catalog of testability patterns, and 
- discovery of testability patterns within application source code 

In the future, we aim to enable patterns' transformations from the framework to improve the testability of the application to be scanned via SAST.   

**OWASP Project:** This project has a OWASP website available at: https://owasp.org/www-project-testability-patterns-for-web-applications/.


## Quick Start

__Concepts__
- [Testability pattern overview](./docs/Testability-Patterns.md) 
- [Testability pattern structure](./docs/Testability-patterns-structure.md)
- [Catalogs of Testability Patterns](https://github.com/testable-eu/sast-testability-patterns/blob/master/README.md)

__How to__
- [install](./docs/How-to-install.md)
- [run (CLI)](./docs/How-to-run-CLI-Usage.md)
- [add a Testability Pattern](https://github.com/testable-eu/sast-testability-patterns/blob/master/docs/testability-patterns-adding.md)
- [add a SAST tool](./docs/How-to-add-a-SAST-tool.md)
- [write discovery rules in Joern](./docs/How-to-write-discovery-rules-in-Joern.md)

## Testability Patterns

So far, we have created a catalog of testability patterns for the following programming languages:

- Java
- PHP
- JavaScript

The complete list of patterns is available at [Testability Pattern Catalogs for SAST](https://github.com/testable-eu/sast-testability-patterns) repository.


## Running

After following the [installation instructions](./docs/How-to-install.md), you can run the TP-Framework with docker:

```bash
$ docker-compose up --build
$ docker-compose run -d --name <CONTAINER_NAME> tp-framework
$ docker exec -it <CONTAINER_NAME> bash
```

Then, run the following command inside the docker container to see the CLI options.

```bash
tpframework -h
```

## Documentation

Detailed documentation is available in the [docs](./docs/README.md) folder. Also, a related publication presented at NDSS 2022 is available [here](https://www.ndss-symposium.org/wp-content/uploads/2022-150-paper.pdf).


## Contributions

You can contribute to this repository through bug-reports, bug-fixes, new code or new documentation. For any report, please [raise an issue](https://github.com/testable-eu/sast-tp-framework/issues/new) in the repository before submitting a PR. We welcome suggestions and feedback from the community.


## Publications

To see the complete list publications, please visit [https://testable.eu/publications/](https://testable.eu/publications/).


## News

Follow us on Twitter on [@Testable_EU](https://twitter.com/Testable_EU) or check out TESTABLE website available at [https://testable.eu/](https://testable.eu/).


## License

This project is licensed under `GNU AFFERO GENERAL PUBLIC LICENSE V3.0`. See [LICENSE](LICENSE) for more information.

## Acknowledgements

This project received funding from the European Union's Horizon 2020 research and innovation programme under grant agreement No. 101019206.

<p align="center">
  <img src="https://testable.eu/img/eu_flag.png"><br>
  Funded by the European Union
</p>
