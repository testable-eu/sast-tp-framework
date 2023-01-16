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

> (1) the framework will parse the output of that Scala rule according to the above triple format (note that your query is expected to end with `.toJson` for correct parsing).
> 
> (2) sometime the same discovery rule is used for more than one instance in a patterns. Using the same identifier there allows to run the rule only once and to group the results properly. Basically, for those instances using the same discovery rule, the framework will not be able to say which of the instances was discovered, but one of them was.    

The Joern query is the core part of the entire Scala rule. It can range from a very simple query searching for a specific syntax construct to something more complex requiring some backward reachability analysis in the CPG.

## Template Patterns
1. Search for instantiation of a specific class (here, assigning a new object in Javascript):
```scala
cpg.assignment.code(".*new WeakMap.*")
```

2. Search for a java-builtin method which consumes a non-static parameter:
```scala
cpg.call.methodFullName(".*java.util.stream.Stream.*").whereNot(_.argument(1).isLiteral).location
```
Note: The string inside the quotes is parsed as regex, e.g., you search for multiple strings with something like ".*Thread.*(Callable|Runnable).*"  

3. Additionally assert that `forEach` is being called on the found method invocation by traversing the AST:
```scala
cpg.call.where(_.methodFullName(".*java.util.stream.Stream.*")).whereNot(_.argument(1).isLiteral).astParent.code(".*forEach.*")
``` 
 4. Search for classic reflexted XSS by tracing the dataflow:  
Example code:
```javascript
function makeResponse(code, message) { 
    res.writeHead(code, {"Content-Type" : "text/html"});

    res.write(message); 
    res.end();
}

const parsed = route.parse(req.url); 
const query = querystring.parse(parsed.query);

makeResponse(200, query);
``` 
Explanation: A Javascript backend (e.g., NodeJS) accesses the .url field of the Request object and returns parts of it in the response.

Discovery rule:
```scala
def source = cpg.call.methodFullName(".*fieldAccess.*").where(_.argument(2).isFieldIdentifier.canonicalName(".*url.*"))

def sink = cpg.call.code(".*\\.write\\(.*\\).*").filter(_.methodFullName != "<operator>.assignment")

sink.where(_.argument(2).reachableBy(source))
```
Explanation: Find a source by looking for field accesses to `.url` on some object.
Define the sink as a call to `.write` which is not a new assignment.
Find a connecting flow.