@main def main(name : String): Unit = {
    importCpg(name)
    val x3 = (name, "3_global_array_iall", cpg.call(".*FETCH_W.*|.*FETCH_R.*|.*FETCH_RW.*").argument.code("GLOBALS").repeat(_.astParent)(_.until(_.filter(x => x.lineNumber.getOrElse(-1) != -1))).location.toJson);
    println(x3)
    delete;
} 