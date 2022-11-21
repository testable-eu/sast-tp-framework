# How to write discovery rules in Joern

Our framework supports discovery of testability patterns instances via Joern queries. In short, 
from the source code (or its compiled version) the Code Property Graph is created. The discovery 
rule comprises the Joern query that traverses the CPG to discover pattern instances, if any.

Let us consider the following discovery rule:
```scala
@main def main(name : String): Unit = {
    importCpg(name)
    val x86 = (name, "80_callback_functions_D3", cpg.call.code(".*INIT_USER_CALL.*call_user_func.*").reachableBy(cpg.call.code(".*CONCAT.*string.*")).location.toJson);
    println(x86)
    delete;
} 
```

Here are the main steps:
- the rule first imports the CPG (automatically generated via the framework) 
- the query is then executed and its outcomes collected in a result variable (`x86` in this case) together with other info
- the value of that result variable is printed
- space is properly cleaned-up

All the above steps are the same in all the rules. Let us dig into the result variable and the Joern query.

The result variable is a triple (1)
- `name` of the CPG used
- identifier of the Scala rule (2)
- Joern query that will be run to discover the pattern instance

> (1) the framework will parse the output of that Scala rule according to the above triple format.
> 
> (2) sometime the same discovery rule is used for more than one instance in a patterns. Using the same identifier there allows to run the rule only once and to group the results properly. Basically, for those instances using the same discovery rule, the framework will not be able to say which of the instances was discovered, but one of them was.    

The Joern query is the core part of the entire Scala rule. It can range from a very simple query searching for a specific syntax construct to something more complex requiring some backward reachability analysis in the CPG.

_TO_BE_CONTINUED_