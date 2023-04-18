# File Processing

## Introduction

This default process is to recursively find the targeted file with given input format, and do operation to the new output path with output format.

The class will process files with parallel computing power (multiple-core CPU).

## Usage

The file `template.py` can be referred. Modify it with your function.

### Usage 1 (`argparse`)

Then, inherit the class, and pass required parameters through `argparse` into the class.

### Usage 2 (`dict`)

Build a `dict` with few required parameters below, and pass into the class.

If `output` or `out_format` is `None`, it is consider to be target file `input` operation, else the data is from `input` to `output`.

### Parameters

#### Required

* Inputs:
  
  * `input`: 
    
    * a folder to do operation;
    * a file to process once (with same input format);
    * a text file which stores paths instead of finding file paths (with different input format);
  
  * `in_format`: format to search to do operation (for file processing); 
    
    * if starts with `\`, the file name will follow a `Regular Expression` restriction;
    
    * if starts with `^`, the search will follow `glob` restriction;
      
      #### Optional

* Outputs (for `io` data flow):
  
  * `output` (for `io`):
    * output folder to export something with the same file system structures;
    * a file to process once (with same output format);
  * `out_format`: the export file format (for file processing);

* `cpu_number`: the number of CPU to process;

* `logger_level`: defines the level of logger to print (`debug`, `info`, `warn`, `error`, `fatal`);
  
  * if `None`: no log file generated; 
  * `self.logger` is logger parameter to use; 
  * WARNING: it is easy to break when `cpu > 1`;

### Overwrite Function

#### Function `do`:

Consider parameters `in_path` and `out_path` are just one file data flow (or `in_folder` and `out_folder` are just one folder of data flow), from the source to the target.

#### Function `callback` (optional):

Callback will do operation after each process done.

Input:

* `None`;
* `1` argument: combined input;
* arguments same as function `do`;

#### Function `before` (Optional):

Do something just before multiprocessing.

### Files list operation

To perform operations on different file lists.

For example: initialize several objects `fp1`, `fp2`..., then:

* If using `fp1 + fp2` is to concatenate files list together;

* If using `fp1 - fp2` is to subtracting file list `fp2` from `fp1`;

### Do operation

To get everything run just call the class with `()`.
