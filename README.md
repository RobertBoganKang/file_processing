# File Processing

## Introduction

This default process recursively finds the target file for a given input format and batches it into the output folder with the original file structure in the new output format.

This class is designed to process files using parallel computing power (multi-core CPUs).

## How to use

The file `template.py` can be referenced. Make changes to it with your functions.

### Mehthod 1 (`argparse`)

Then, inherit the class and pass the required arguments into it in the form of `argparse`.

### Mehthod 2 (`dict`)

Create a `dict` with the following few necessary parameters and pass it to the class.

If `output` or out_format is `None`, it is considered an `input` operation for the target file, otherwise the data will flow from `input` to `output`.

## Parameters

### Required

* Inputs:
  
  * `input`: 
    
    * a folder to do operation;
    * a file to process once (with same input format);
    * a text file storing the path, rather than looking for the file path (with a different input format);
  
  * `in_format`: format to search to do operation (for file processing); 
    
    * if starts with `\`, the file name will follow a `Regular Expression` restriction;
    * if starts with `^`, the search will follow `glob` restriction;
    * if starts with `!`, the program will skip all input check (file existence, file format check);

### Optional

* Outputs (for `io` data flow):
  
  * `output` (for `io`):
    * output folder to export something with the same file system structure;
    * to process a file once (with same output format);
  * `out_format`: the export file format (for file processing);

* `cpu_number`: the number of CPU to process;

* `multi_what`: defines the method of processing:
  
  * multi-processing with `mp`;
  
  * multi-threading with `mt`;
  
  * iterator multi-processing with `imp`;
  
  * iterator multi-threading with `imt`;

## Overwrite Function

### Required

* Function `do`: consider the parameters `in_path` and `out_path` as just a stream of files (or `in_folder` and `out_folder` as just a stream of folders), from source to target;

### Optional

* Function `before`: do something just before multiprocessing;

* Function `callback`: callback will do operation after each process done, with input:
  
  * `None`;
  * `1` argument: combined input;
  * arguments same as function `do`;

## Files list operation

To perform operations on different file lists.

For example: initialize several objects `fp1`, `fp2`..., then there are set operations (python style):

* Operations: or (`|`), and (`&`), subtraction (`-`), xor (`^`);

* Use it as a common set operations and can be used in combination;

## Do operation in parallel

To get all the runs, just call the class with `()`.
