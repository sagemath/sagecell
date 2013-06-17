#! /usr/bin/env python

import sys

if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        text = f.read().replace("+ ++a", "+(++a)", 1)
        # JSMin minimizes this expression incorrectly
    with open(sys.argv[1], "w") as f:
        f.write(text)
