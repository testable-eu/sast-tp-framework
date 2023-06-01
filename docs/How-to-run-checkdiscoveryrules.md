# How to run: Checkdiscoveryrules

## Overview

This commands allows to run the discovery rule on the pattern instance itself.

## Command line

To check discovery rules on your pattern run:

```bash
tpframework checkdiscoveryrules --help
usage: tpframework [OPTIONS] COMMAND checkdiscoveryrules [-h] (--print | --export EXPORTFILE) -l LANGUAGE (-p PATTERN_ID [PATTERN_ID ...] | --pattern-range RANGE_START-RANGE_END | -a)
                                                         [--tp-lib TP_LIB_DIR] [-s NUMBER] [--output-dir OUTPUT_DIR]

options:
  -h, --help            show this help message and exit
  --print               Print measurements on stdout.
  --export EXPORTFILE   Export measurements to the specified csv file.
  -l LANGUAGE, --language LANGUAGE
                        Programming language targeted
  -p PATTERN_ID [PATTERN_ID ...], --patterns PATTERN_ID [PATTERN_ID ...]
                        Specify pattern(s) ID(s) to test for discovery
  --pattern-range RANGE_START-RANGE_END
                        Specify pattern ID range separated by`-` (ex. 10-50)
  -a, --all-patterns    Test discovery for all available patterns
  --tp-lib TP_LIB_DIR   Absolute path to alternative pattern library, default resolves to `./testability_patterns`
  -s NUMBER, --timeout NUMBER
                        Timeout for CPG generation
  --output-dir OUTPUT_DIR
                        Absolute path to the folder where outcomes (e.g., log file, export file if any) will be stored, default resolves to `./out`
```

## Example

Here a simple example that will run checkdiscoveryrules on the first PHP pattern and print the results to the cmd.
`tpframework checkdiscoveryrules -p 1 -l php --print`

Note: Minimum requirement for this command is a pattern, a language and either `--print` or `--export`.

## Required fields in instance `json` metadata

The explanation for the instance `json` metadata can be found [here](https://github.com/testable-eu/sast-testability-patterns/blob/master/docs/testability-patterns-structure.md)