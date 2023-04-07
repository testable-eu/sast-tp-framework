# How to write discovery rules in Joern

Our framework supports discovery of testability patterns instances via Joern queries. In short, from the source code (or its compiled version) the Code Property Graph is created.
The discovery rule comprises the Joern query that traverses the CPG to discover pattern instances, if any.

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

**Important**: For a rule to be properly parseable by the framework, the output needs to include at least the following mandatory fields:

- `filename`
- `lineNumber`

Not all CPG nodes include these.
A query in the rule scala file should always end on
`.location.toJson`.
In general, test your queries in the joern interactive shell:

```sh
$ joern 
[...]
joern> importCode("./your_src_dir")
```

## Template Patterns

### 1. grep-like

a. **Search for Code Patterns**: Many of Joern's CPG nodes take regex as an argument to filter search results:
a. E.g., here we search for instantiations of a specific class. For this, we grep on the code of all the assignments in the code, i.e. defining a new variable like `a = new Object()`.

```scala
cpg.assignment.code(".*new WeakMap.*")
```

<details markdown=true>
<summary>Note regarding Regex</summary>

The string inside the quotes is parsed as regex, e.g., you search for multiple strings with something like ".*Thread.*(Callable|Runnable).*".  
To search for special characters such as `{`, you have to escape them with a double backslash `//`.

</details>

b. **Search for Conditions**: One of the most important filtering functionalities is the `where` clause. It takes a traversal as an input, i.e., another CPG query, and returns all nodes which are not empty.
Here we use it to search for a java-builtin method which consumes a non-static parameter:

```scala
cpg.call.methodFullName(".*java.util.stream.Stream.*").whereNot(_.argument(1).isLiteral)
```

<details markdown=true>
<summary>Query Decomposition</summary>

1. `call`: consider all function calls
2. `methodFullName`: get the full name of all functions being called.
3. `([REGEX])`: filter the names for a java-builtin function called "Stream" (not the wildcards `.*` in the beginning and end)
4. `whereNot`: only consider call nodes which
5. `_.argument(1)`: this looks at the first argument of the call, for method calls this is the object itself (e.g., `this`)
6. `isLiteral`: and finally we make sure that it is not a literal, e.g., not a static string or integer (`"s", 1337`) but a variable.

</details>

c. **Filter and Match on Lists**:
Sometimes we want need to compare and match lists of strings, e.g., to find usages of certain methods or variables.  

This example rule checks if there are any function invocations of a re-defined function declaration.
For this, we get a list of all methods containing a `1` and match it against all methods which are being called.
It leverages the fact that joern appends numerical numbers to the names of re-defined function declarations.

```scala
cpg.method.filter{
    n => cpg.method.name.toList.contains(n.name+"1")
}.callIn.location.toJson
```

### 2. AST Traversals  

a. **Check for Enclosing Control Block**: For any found node, we can walk the AST backwards by using `inAst`.
In this example we check whether an assignment is enclosed in an if block:

```scala
cpg.assignment.code(".*new Obj.*").inAst.isControlStructure.controlStructureType("IF")
```

b. **Look for target candidate and assure that we call some method on it**: Here we assert that the `forEach` method is being called on the found method invocation by traversing the AST:

```scala
cpg.call.where(_.methodFullName(".*java.util.stream.Stream.*")).whereNot(_.argument(1).isLiteral).astParent.code(".*forEach.*")
```

### 3. Dataflow Analysis  

We can also make use ob Joern's built-in dataflow analysis to look for more complex scenarios, such as variable tainting.
In the following we will find an XSS vulnerability with the following steps:

```text
1. Find a source by looking for field accesses to `.url` on some object.
2. Define the sink as a call to `.write` which is not a new assignment.
3. Find a connecting flow.
```

Corresponding Discovery Rule:

```scala
def source = cpg.call.methodFullName(".*fieldAccess.*").where(_.argument(2).isFieldIdentifier.canonicalName(".*url.*"))

def sink = cpg.call.code(".*\\.write\\(.*\\).*").filter(_.methodFullName != "<operator>.assignment")

sink.where(_.argument(2).reachableBy(source))
```

<details markdown=true>
<summary>Example Code</summary>

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

</details>

[Here](https://github.com/testable-eu/sast-testability-patterns/blob/131d6f6861b0cdc890778ad5dc98a83fa2486e57/JAVA/23_array/2_instance_23_array/2_instance_23_array.sc) you can find an example of how we use this technique to discover a testability pattern.

### 4. PHP

Since the CPG for PHP is based on PHP bytecode and it is still under developement it doesn't support the full CPG spec:

For example it doesn't support constructs like `cpg.assignment`.

```scala
joern> cpg.assignment.l 
res0: List[operatorextension.OpNodes.Assignment] = List()
```

But that functionality can be queried via calls:

```scala
joern> cpg.call("ASSIGN").l 
res1: List[Call] = List(
  Call(
    id -> 512409557603043114L,
    argumentIndex -> -1,
    argumentName -> None,
    code -> "ASSIGN CV($x) T2",
    columnNumber -> None,
    dispatchType -> "STATIC_DISPATCH",
    dynamicTypeHintFullName -> ArraySeq(),
    lineNumber -> Some(value = 1),
    methodFullName -> "<empty>",
    name -> "ASSIGN",
    order -> 2,
    signature -> "",
    typeFullName -> "<empty>"
  )
)
```

Check out the documentation including links to useful resources at https://github.com/mal-tee/php-cpg-doc .
