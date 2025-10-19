keymap.py contains a list with all of the key metadata.

The layout of the keys list is arranged according to the physical key matrix
starting at the bottom row with F17 through ENTER.   Positions that are not
connected to a key switch are filled with the value None so that the matrix
remains rectangular.   There are 6 rows with 5 columns.  There are however,
only 4 keys in each matrix column. Coercing the data structure to match the
physical wiring of the key matrix allows for more efficient key scanning.
Specifically, it allows us to deduce the keycode from simply multipling
row * column  to get the index into the keys list so that key metadata can
be accessed with a quick lookup, without scanning the array and without the
memory overhead of using a hash table.
