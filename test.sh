#!/bin/sh
status=0

python sort.py
status=$(echo "$? + $status" | bc)

diff -u cameras.csv cameras.sorted.csv
status=$(echo "$? + $status" | bc)

diff -u lenses.csv lenses.sorted.csv
status=$(echo "$? + $status" | bc)

if test $status -ne 0; then
    echo DATA ENTRIES ARE NOT SORTED
    exit 1
fi
exit 0
