#!/bin/bash
find $PATTERNSRC -name "*.java" > $TPFOUT/sources.txt
javac -classpath $PATTERNLIB/*.jar  @$TPFOUT/sources.txt