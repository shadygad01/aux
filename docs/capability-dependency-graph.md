# Capability Dependency Graph

```mermaid
flowchart LR
    C["Collection 40"] --> N["Normalization 40"]
    N --> E["Evidence 60"]
    E --> K["Knowledge 60"]
    E --> R["Reasoning 40"]
    K --> R
    R --> MS["Market Story subprofile 20"]
    MS --> D["Decision 40"]
    D --> MT["Market Thesis subprofile 20"]
    MT --> P["Publishing 20"]
    P --> DP["Decision Presentation subprofile 0"]
    D --> L["Learning 60"]
    L --> RS["Research 40"]
    RS --> K
    M["Monitoring 20"] --> G["Governance subprofile 20"]
    G -. gates .-> C
    G -. gates .-> N
    G -. gates .-> E
    G -. gates .-> K
    G -. gates .-> R
    G -. gates .-> D
    G -. gates .-> L
    G -. gates .-> RS
    G -. gates .-> P
```

A capability cannot be promoted above a required upstream dependency unless it proves a fail-closed
isolation contract. Cyclic learning (`Decision -> Learning -> Research -> Knowledge`) is
non-production and cannot mutate the live decision path.
