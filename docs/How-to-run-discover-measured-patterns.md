# How to run: Discover measured patterns

## Overview

This commands allows to discover pattern instances not supported by any of the tools in the arsenal. This requires the pattern instances intended to be discovered to be associated with discovery rules. 

## Command line

To discover patterns, that have been already measured with the SAST arsenal, within a project source code run:

```bash
tpframework discovery [-h] (-p PATTERN_ID [PATTERN_ID ...] | --pattern-range RANGE_START-RANGE_END | -a) -t TARGET_DIR [--tools TOOLS [TOOLS ...]] -l LANGUAGE [--tp-lib TP_LIB_DIR]

options:
  -h, --help            show this help message and exit
  -p PATTERN_ID [PATTERN_ID ...], --patterns PATTERN_ID [PATTERN_ID ...]
                        Specify pattern(s) ID(s) to discover on the target
  --pattern-range RANGE_START-RANGE_END
                        Specify pattern ID range separated by`-` (ex. 10-50)
  -a, --all-patterns    Run discovery for all available patterns
  -t TARGET_DIR, --target TARGET_DIR
                        Path to discovery target folder
  --tools TOOLS [TOOLS ...]
                        List of SAST Tools for discovering pattern not supported
  -l LANGUAGE, --language LANGUAGE
                        Programming Language used in the target source code
  --tp-lib TP_LIB_DIR   Path to alternative lib, default is placed in `./testability_patterns`
```

**Warning**: This command works only for those patterns that have been already measured.

## Example

Here a simple example that will run discovery for patterns 1 and 2 of the PHP catalog within the project `myproject`:
`tpframework discovery -p 1 2 -l PHP -t /myproject`

## Required fields in instance `json` metadata

The explanation for the instance `json` metadata can be found [here](https://github.com/testable-eu/sast-testability-patterns/blob/master/docs/testability-patterns-structure.md)
TODO: write here which json fields are required so that the framework can implement discover
