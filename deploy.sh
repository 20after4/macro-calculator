#!/usr/bin/env bash

# Copy all micropython files to the attached microcontroller board
# using mpremote. For each python file in the firmware directory,
# If there is a .mpy file present with the same basename, rebuild it
# using mpy-cross and copy the mpy file.
# Otherwise, just copy the .py file.

for f in ./firmware/*.py; do
    dir=$(dirname $f)
    filename=$(basename -- $f)
    extension="${filename##*.}"
    filename="${filename%.*}"
    if [ -f $dir/$filename.mpy ]; then
        echo "Compile $filename.mpy"
        mpy-cross $f
        echo "Copy $dir/$filename.mpy :$filename.mpy"
        mpremote cp $dir/$filename.mpy :$filename.mpy
    else
        echo "Copy $f :$filename.py"
        mpremote cp $dir/$filename.py :$filename.py
    fi
done
