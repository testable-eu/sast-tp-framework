# Catalogs of SAST Testability Patterns
The Testability Pattern framework operate over catalogs of testability patterns for SAST. 

These catalogs need to follow a precise file system structure:
- each catalog is captured as a subfolder of the `.\testability_patterns` folder, e.g., `.\testability_patterns\PHP` 
- each pattern in a catalog is captured as a sub-folder of the catalog folder, e.g., `.\testability_patterns\PHP\1_static_variables`
- each pattern is required to follow the guidelines described [here](./Testability-patterns-structure.md)

We recommend adding patterns to a catalog via the `add` operation of the framework. This will fill-in automatically some necessary metadata and will ensure your pattern is well-written and properly added. However, patterns can also be added manually by adding a new pattern folder to the catalog and by manually providing all the necessary metadata and artifact for that pattern. 
