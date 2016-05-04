import sys
import re
import unittest

class pseudoTest(unittest.TestCase):
    def test_dummy(self):
        self.assertTrue(1)

def do_edit(filename, filter=None):
    with open(filename, "r") as f:
        lines = f.readlines()
    with open(filename, "w") as f:
        for line in lines:
            if filter is not None and not filter.match(line):
                f.write(line)

if __name__ == "__main__":
    # delete all lines containing the word "delete"
    filter = re.compile(r".*\bdelete\b")
    for name in sys.argv[1:]:
        do_edit(name, filter=filter)
