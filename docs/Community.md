# A Community around Testability Patterns for SAST

Our SAST testability patterns and related framework target the following main groups:

- Web developers
  - discover our testability patterns in development project so to get awareness of the code areas that are not analysed by the SAST tools used
  - with that awareness, a developer can estimate the risk of SAST incomplete analysis in her project
  - this can trigger remediation actions such as
    - refactoring the code problematic for SAST
    - performing more intensive code review for the code areas missed by SAST
    - interacting with the central security team to get feedback and remediation guidelines

- Security central teams
  - the central security team can discover our testability patterns in all the projects implemented in their organization so to get awareness of the SAST challenges e.g., which testability patterns are more prevalent and more impactful
  - the decision about which SAST tools to buy can be made by also considering which SAST tool performs better on the most prevalent testability patterns
  - remediation strategies can be devised for those prevalent testability patterns
    - code refactoring practices can be introduced and disseminated to developers
    - SAST tool improvements can emerge from discussions between the security central team and the SAST tools' customer services
  - create new testability patterns emerging from the usage of SAST tools in their organization

- SAST tool developers
  - measure SAST testability patterns against their own tool to know which ones are not supported
  - contribute to create new testability patterns that their tool is supporting while others may not
  - discover patterns in open source projects to be aware of the most prevalent ones
  - improve the SAST tool to remediate some of these not-yet-supported prevalent patterns

- Web Security Researchers (SAST area)
  - create new testability patterns emerging from their research
  - devise discovery and/or remediation strategies for some testability patterns

The overall goal is to make web applications more testable for SAST tools.
