# File Processing
## Introduction
This default process is to recursively find the targeted file with given input format, and do operation to the new output path with output format.

The class will do everything for you in behind with parallel computing power (multiple-core CPU).
## Usage
### Code-wise Operation
#### Usage 1 (`argparse`)
Then, inherit the class, and pass required parameters through `argparse` into the class.

The file `template.py` can be referred. Modify it with your function.
#### Usage 2 (`dict`)
Build a `dict` with all required parameters below, and pass into the class.

If `output` or `out_format` is `None`, it is consider to be target folder operation, else the data is from `input` to `output`.
#### Required Parameters:
* Inputs:
  * `input`: input folder to do operation; or `input_path_list`: use a text file which stores paths instead of finding file paths;
  * `in_format`: format to search to do operation (for file processing); 
    * if starts with `\\` letter, the file name will follow a Regular Expression;
#### Optional Parameters:

* Outputs (for `io` data flow):
  * `output`: output folder to export something with the same file system structures (for `io`);
  * `out_format`: the export file format (for file processing); `?` is the same pattern as input (for `io`);
* `cpu_number`: the number of CPU to process;
* `logger_level`: defines the level of logger to print, `self.logger` is logger parameter to use; if `None`: no log file generated;

#### Overwrite Function
Function `do`:
Consider parameters `in_path` and `out_path` are just one file data flow (or `in_folder` and `out_folder` are just one folder of data flow), from the source to the target.

#### Do operation
To get everything run just call the class with `()`.

