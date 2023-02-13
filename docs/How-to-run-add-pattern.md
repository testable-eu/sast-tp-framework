## Prerequisites

- [Proposal for a new testability pattern](https://github.com/testable-eu/sast-testability-patterns/blob/master/docs/testability-patterns-adding.md)

# How to run: Add pattern

## Overview

TP Framework exposes a command to add a new pattern to a TP Catalog. This command will perform a set of operations to transfer the pattern in an organized target folder, assigning to the new added pattern a counter-unique `pattern_id`. Pattern instances will also be assigned a counter-unique `instance_id` within the pattern. An unique id for a pattern instance is given from the combination of `pattern_id` and `instance_id`.

## Command line
To add a new pattern to the catalog you can use the command:

```bash
tpframework add [-h] -p PATTERN_DIR -l LANGUAGE [-j JSON_FILE] [--tp-lib TP_LIB_DIR] [-m]

options:
  -h, --help            show this help message and exit
  -p PATTERN_DIR, --pattern-dir PATTERN_DIR
                        Path to pattern directory
  -l LANGUAGE, --language LANGUAGE
                        Programming Language used in the pattern
  -j JSON_FILE, --json JSON_FILE
                        Path to JSON file containing pattern's metadata
  --tp-lib TP_LIB_DIR   Path to alternative lib, default is placed in `testability_patterns`
  -m, --measure         Measure pattern against all installed SASTs tools
```

The `PATTERN_DIR` and the `LANGUAGE` are mandatory options. The `PATTERN_DIR` needs to comply with the [Testability patterns structure](https://github.com/testable-eu/sast-testability-patterns/blob/master/docs/testability-patterns-structure.md). 

**Warning**: If successful the pattern and all its necessary artifacts will be added to the proper catalog. However any other file/folder in `PATTERN_DIR` that is not a mandatory pattern artifact will simply be ignored. If you want to add those additional files/folders, please do that manually after the pattern has been added.

**Warning**: The command will look for a metadata json file that match the name of the pattern folder. It is possible to specify where metadata are located by adding the `--json path/to/json/file.json` option.

_Optional_: You can specify the flag `--measure` if you want to measure your new pattern with all the tools present in the SAST Arsenal.

_Optional_: By default TP Framework will use `./testability_pattern` folder as TP Catalogs root, but you can specify a different one by adding the _optional_ argument `--tp-lib TP_LIB_DIR` to your command.



