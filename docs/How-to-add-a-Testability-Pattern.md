# How to add a Testability Pattern

## Prerequisites
- [Testability patterns overview](./Testability-Patterns.md)
- [Testability patterns structure/schema](./Testability-patterns-structure.md)

## Steps
A pattern can be added to a SAST catalog either manually or via the tp-framework. The second option is recommended. 

In both the cases the pattern needs first to be created (as explained in the Testability pattern overview, see [here](./Testability-patterns-structure.md)). The output of this creation will be a self-contained _pattern folder structure_ like the following (cf. [Testability patterns structure/schema](./Testability-patterns-structure.md)):
```
00_pattern_name
|-- 00_pattern_name.json
|-- README.md
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

__Important__: the pattern folder shall be _self-contained_ as files and folders outside it will be neglected! For instance, dependencies should not point outside the pattern folder.

### Add via the framework
_TODO_

### Add manually
_TODO_