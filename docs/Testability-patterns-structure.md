# Testability patterns for SAST: structure

## Prerequisites
- [Testability patterns](./Testability-Patterns.md)

## Structure: file system and json
For the purpose of the framework a Pattern is contained into a folder denominated with the following naming convention (`00` should be replaced with specific numbers for both the pattern and its instances, e.g., `80_callback_functions` and `1_instance_80_callback_functions`):

```bash
00_pattern_name
```

The Pattern Instance naming convention:

```bash
00_instance_00_pattern_name
```

The pattern folder structure:

```
00_pattern_name
|-- 00_pattern_name.json
|-- README.md
|-- pattern_instances_documentation.md (optional, detail the experiments done for each instance)
|-- 1_instance_00_pattern_name
|   |-- 1_instance_00_pattern_name.json
|   |-- pattern_src_code // (file or dir)
|   |-- pattern_discovery_rule.sc // (Scala query, or a python script can be provided sometime)
|   |-- lib/dep folders // (optional)
|   |-- other_files // (optional)
|
|-- 2_instance_00_pattern_name
|-- 3_instance_00_pattern_name
|-- ...
```

The pattern `json` metadata:

```json
{
    "name": "string",
    "description": "string | path/to/file",
    "family": "string",
    "tags": ["list", "of", "strings"],
    "instances": [
        "paths/to/instance1.json",
        "paths/to/instance2.json",
        "paths/to/instance3.json"
    ]
}
```

The instance `json` metadata:

```json
{
    "description": "string | path/to/file",
    "code": {
        "path": "path/to/src_code",
        "injection_skeleton_broken": "boolean"
    },
    "discovery": {
        "rule": "path/to/discovery_rule",
        "method": "joern | python | ...",
        "rule_accuracy": "FP | FN | FPFN | Perfect",
        "notes": "string | path/to/file"
    },
    "remediation": {
        "transformation": "TBD",
        "modeling_rule": "TBD"
        "notes": "string | path/to/file"
    },
    "compile": {
        "dependencies": "path/to/dependencies",
        "binary": "path/to/binary",
        "instruction": "string"
    },
    "expectation": {
        "type": "string",
        "sink_file": "path/to/file",
        "sink_line": "number",
        "source_file": "path/to/file",
        "source_line": "number",
        "expectation": "boolean"
    },
    "properties": {
        "category": "S0 | D1 | D2 | D3 | D4",
        "feature_vs_internal_api": "FEATURE | INTERNAL_API",
        "input_sanitizer": "boolean",
        "source_and_sink": "boolean",
        "negative_test_case": "boolean"
    }
}
```

## Mandatory fields for each framework operation

_TO BE DONE: write here which json fields are required so that the framework can implement an operation e.g., measurement_