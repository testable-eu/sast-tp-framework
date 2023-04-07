# How to run: Manual discovery

## Overview

This command allows to execute discovery rules on a target application source code. This command is very useful to test new discovery rules before associating them to pattern instances.

## Command line

To execute discovery rules against a targeted application source code run this command:

```text
tpframework manual-discovery [-h] -t TARGET_DIR -l LANGUAGE -m METHOD -r RULES_PATH [RULES_PATH ...]
                                                      [-s NUMBER]

options:
  -h, --help            show this help message and exit
  -t TARGET_DIR, --target TARGET_DIR
                        Path to discovery target folder
  -l LANGUAGE, --language LANGUAGE
                        Programming Language used in the target source code
  -m METHOD, --method METHOD
                        Discovery method to perform discovery operation
  -r RULES_PATH [RULES_PATH ...], --rules RULES_PATH [RULES_PATH ...]
                        Path to file(s) or directory containing a set of discovery rules
  -s NUMBER, --timeout NUMBER
                        Timeout for CPG generation
```

Most of the options are mandatory. The command needs to know where the source code is (`TARGET_DIR`), which programming language we are targeting (`LANGUAGE`), which discovery rules we want to execute (`RULES_PATH` list), and which method (`METHOD`) these rules are based on (e.g., `joern`).

## Example

For instance, the following will execute the scala discovery rule `3_instance_80_callback_functions.sc` using `joern` on the PHP files in the project `/myproject`:

`tpframework manual-discovery -t /myproject -l PHP -m joern -r testability_patterns/PHP/80_callback_functions/3_instance_80_callback_functions/3_instance_80_callback_functions.sc`

## Required fields in instance `json` metadata

The explanation for the instance `json` metadata can be found [here](https://github.com/testable-eu/sast-testability-patterns/blob/master/docs/testability-patterns-structure.md)
TODO: write here which json fields are required so that the framework can implement manual discover
