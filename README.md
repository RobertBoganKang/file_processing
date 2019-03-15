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
Then, inherit the class, and pass several parameters through `argparse` into the class.

The `template.py` file can be refered.
```python
import argparse

# https://github.com/RobertBoganKang/FileProcessing
from file_processing import FileProcessing


class Template(FileProcessing):
    """
    xxx xxx xxx xxx
    """

    def __init__(self, ops):
        super().__init__(ops)
        self.xx = None
        # ...

    # in_path --> out_path; data flow
    def do_body(self, in_path, out_path):
        """
        overwrite the method
        """
        pass

    # target path operation
    # def do_body(self, target_path):
    #    """
    #    overwrite the method
    #    """
    #    pass

    def xxx(self):
        # xxx
        pass

    # ...


if __name__ == '__main__':
    # prepare argument
    parser = argparse.ArgumentParser(description='xxx xxx xxx')
    parser.add_argument('--input', '-i', help='xxx', default='in', type=str)
    parser.add_argument('--output', '-o', help='xxx', default=None, type=str)
    parser.add_argument('--in_format', '-if', type=str, help='define the input format', default='xxx')
    parser.add_argument('--out_format', '-of', type=str, help='define the output format', default=None)
    parser.add_argument('--cpu_number', '-j', type=int, help='cpu number of processing', default=0)
    # ...
    args = parser.parse_args()

    # do operation
    t = Template(args)
    t.do_multiple()
    # ...

```
Modify the `template.py` with your function.

If `output` or `out_format` is `None`, it is consider to be target folder operation, else the data is from `input` to `output`.
#### Several Parameters:
* `input`: input folder to do operation
* `output`: output folder to export something with the same file system structures
* `in_format`: format to search to do operation
* `out_format`: the export file format
* `cpu_number`: the number of cpu to process
#### Overwrite Function
Function `do_body`:
Consider parameters `in_path` and `out_path` are just one file data flow, from the source to the target.
#### Do operation
Do operation just write `do_multiple` function.

