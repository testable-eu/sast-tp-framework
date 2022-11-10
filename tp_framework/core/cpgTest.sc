@main def main(name : String): Unit = {
    try {
        importCpg(name)
        delete;
    } catch {
        case _: Throwable => println("Error in CPG generation")
    }
}
