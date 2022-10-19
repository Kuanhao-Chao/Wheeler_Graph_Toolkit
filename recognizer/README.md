## Installation

If the Z3 submodule has not been downloaded yet, do so with the command below.
```
git submodule update --init --recursive
```

Then, type `make z3` to compile Z3 and create static library and include files.
```
make z3
```
Root password will be requested to perform a sudo command (`sudo make install` in the `./z3`) to create the static library and include files in `./z3`.

Finally, enter `make` to compile the recognizer code.
```
make
```
An executable `recognizer` will be generated in the current directory and also copied to `../bin`.
