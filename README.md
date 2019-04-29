# File Processing
## Introduction
This default process is to recursively find the targeted file with given input format, and do operation to the new output path with output format.

The class will do everything for you in behind with parallel computing power.
## Usage
### Codewise Operation
#### Usage 1 (argparse)
Then, inherit the class, and pass required parameters through `argparse` into the class.

The `template.py` (or `template_folder.py` for folder processing) file can be refered. Modify it with your function.
#### Usage 2 (api)
Build a dict with all required parameters below, and pass into the class.

If `output` or `out_format` is `None`, it is consider to be target folder operation, else the data is from `input` to `output`.
#### Required Parameters:
* `input`: input folder to do operation
* `output`: output folder to export something with the same file system structures
* `in_format`: format to search to do operation (for file processing)
* `out_format`: the export file format (for file processing)
* `cpu_number`: the number of cpu to process
#### Overwrite Function
Function `do`:
Consider parameters `in_path` and `out_path` are just one file data flow (or `in_folder` and `out_folder` are just one folder of data flow), from the source to the target.
#### Do operation
To get everything run just call the class with `()`.

