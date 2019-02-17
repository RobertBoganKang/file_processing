# File Processing
## Introduction
This default process is to recursively find the targeted file with given input format, and do operation to the new output path with output format.

The class will do everything for you in behind with parallel computing power.
## Usage
### Import Function
Import function first with:
```python
from file_processing import FileProcessing
```
### Codewise Operation
Then, inherit the class, and pass four parameters through `argparse` into the class:
```python
import argparse

from file_processing import FileProcessing


class C(FileProcessing):
    """
    xxx xxx xxx xxx
    """

    def __init__(self, ops):
        super().__init__(ops)
        self.xx = None
        ...

    def do_body(self, in_path, out_path):
        """
        overwrite the method
        """

    def xxx(self):
        # xxx
        pass

    # ...


if __name__ == '__main__':
    # prepare argument
    parser = argparse.ArgumentParser(description='xxx xxx xxx')
    parser.add_argument('--input', '-i', help='xxx', default='in', type=str)
    parser.add_argument('--output', '-o', help='xxx', default='out', type=str)
    parser.add_argument("--in_format", "-if", type=str, help="define the input format", default="xxx")
    parser.add_argument("--out_format", "-of", type=str, help="define the output format", default="yyy")
    # ...
    args = parser.parse_args()

    # do operation
    c = C(args)
    c.do_multiple()
    # ...
```
Modify the `template.py` with your function.
#### Four Parameters:
* `input`: input folder to do operation
* `output`: output folder to export something with the same file system structures
* `in_format`: format to search to do operation
* `out_format`: the export file format
#### Overwrite Function
Function `do_body`:
Consider parameters `in_path` and `out_path` are just one file data flow, from the source to the target.
#### Do operation
Do operation just write `do_multiple` function.

