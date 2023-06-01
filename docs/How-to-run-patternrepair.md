# How to run: Patternrepair

## Overview

This commands should help you reviewing your testability catalogue and keep it nice and tidy.
It might also help you, repair patterns, that are broken.

## Command line

To start repairing/reviewing your patterns runs:

```bash
tpframework patternrepair --help
usage: tpframework [OPTIONS] COMMAND patternrepair [-h] -l LANGUAGE (-p PATTERN_ID [PATTERN_ID ...] | --pattern-range RANGE_START-RANGE_END | -a) [--tp-lib TP_LIB_DIR]
                                                   [--output-dir OUTPUT_DIR] [--masking-file MASKING_FILE] [--measurement-results MEASUREMENT_DIR]
                                                   [--checkdiscoveryrules-results CHECKDISCOVERYRULES_FILE] [--skip-readme]

options:
  -h, --help            show this help message and exit
  -l LANGUAGE, --language LANGUAGE
                        Programming language targeted
  -p PATTERN_ID [PATTERN_ID ...], --patterns PATTERN_ID [PATTERN_ID ...]
                        Specify pattern(s) ID(s) to test for discovery
  --pattern-range RANGE_START-RANGE_END
                        Specify pattern ID range separated by`-` (ex. 10-50)
  -a, --all-patterns    Test discovery for all available patterns
  --tp-lib TP_LIB_DIR   Absolute path to alternative pattern library, default resolves to `./testability_patterns`
  --output-dir OUTPUT_DIR
                        Absolute path to the folder where outcomes (e.g., log file, export file if any) will be stored, default resolves to `./out`
  --masking-file MASKING_FILE
                        Absolute path to a json file, that contains a mapping, if the name for some measurement tools should be kept secret, default is None
  --measurement-results MEASUREMENT_DIR
                        Absolute path to the folder where measurement results are stored, default resolves to `./measurements`
  --checkdiscoveryrules-results CHECKDISCOVERYRULES_FILE
                        Absolute path to the csv file, where the results of the `checkdiscoveryrules` command are stored, default resolves to `./checkdiscoveryrules.csv`
  --skip-readme         If set, the README generation is skipped.
```

Note: At the moment only `patternrepair` for PHP is supported. Support your own language by writing an `InstanceRepair` class, that inherits from `InstanceRepair`.

The `patternrepair` enforces the pattern structure as described [here](https://github.com/testable-eu/sast-testability-patterns/blob/master/docs/testability-patterns-structure.md).
To do so, it is seperated into different steps:

- `PatternRepair`: This will check the pattern JSON file, correct the references to the instance json files.
- `InstanceRepair`: This will check and correct the instance json file for each instance. At the moment, only PHP patterns are supported.
  - It generates opcode for every PHP file.
  - It checks for the comments `// source` and `// sink` in the file in order to fill in the source and sink line in the correspoding instance json file.
- `READMEGenerator`: This creates a README file for a pattern based on the JSON files. If you want to skip the generation of the README file, use the `--skip-readme` flag. As the README includes results of `measure` and `checkdiscoveryresults`, valid filepaths for these must be provided, when generating a README file.

## Example

Note: Minimum requirement for this command is a pattern and a language.

### Example 1

Here a simple example that will run patternrepair on the first PHP pattern without generating a new README file for that pattern.
`tpframework patternrepair -p 1 -l php --skip-readme`

### Example 2

Here an example for a patternrepair, that repairs all php patterns and generates a new readme for each pattern.
`tpframework patternrepair -a -l php  --measurement-results ./your_measurement_results --checkdiscoveryrules-results ./your_results.csv`
