#!/bin/bash

if [ "$#" -lt 2 ]
then
    echo "usage: `basename $0` output_dir id-dir1[id-dir2...]"
    exit
fi

OUT_DIR=$1
mkdir -p  $OUT_DIR

shift

for yr_dir in $*
do
    if [ ! -d "$yr_dir" ]
    then
        echo "$yr_dir" is not a directory
        exit
    fi
    files=""
    year=$(basename $yr_dir)
    echo "merging year $year's id files..."
    for file in `ls -1 $yr_dir | sort -n`
    do
        files+=$yr_dir/$file' '
    done
    echo $files | xargs cat > $OUT_DIR/$year
done
