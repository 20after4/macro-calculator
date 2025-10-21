#!/usr/bin/env bash

# Copy all micropython files in `firmware` to the attached microcontroller
# board using `mpremote`. Handles .mpy or .py files, rebuilding the mpy files
# when changes are made to the source. If no .mpy file exists then we just
# copy the .py source and let the microcontroller compile it.

# For each python file in the firmware directory,
for f in ./firmware/*.py; do
    dir=$(dirname "$f")
    filename=$(basename -- "$f")
    #extension="${filename##*.}"
    filename="${filename%.*}"
    if [ -f "$dir/$filename.mpy" ]; then
        # If there is a .mpy file present with the same basename, rebuild it
        # using `mpy-cross`` and copy the updated mpy file instead of the source.py
        echo "Compile $filename.mpy"
        mpy-cross "$f"
        echo "Copy $dir/$filename.mpy :$filename.mpy"
        mpremote cp "$dir/$filename.mpy" ":$filename.mpy"
    else
        # Otherwise, just copy the .py file.
        echo "Copy $f :$filename.py"
        mpremote cp "$dir/$filename.py" ":$filename.py"
    fi
done
