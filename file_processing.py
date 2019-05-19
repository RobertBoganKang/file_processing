import glob
import multiprocessing
import os
import shutil


class CommonUtils(object):
    """common tools for classes"""

    @staticmethod
    def cpu_count(cpu_count):
        """
        get the cpu number
        :return: int; valid cpu number
        """
        max_cpu = multiprocessing.cpu_count()
        if cpu_count == 0 or cpu_count > max_cpu:
            cpu_count = max_cpu
        return cpu_count

    @staticmethod
    def remove_empty_folder(target_folder):
        """
        target folder may empty, then remove it
        :return: None
        """
        # find all patterns
        fs = glob.glob(os.path.join(target_folder, '**/*'), recursive=True)
        # select folders
        fs = [x for x in fs if os.path.isdir(x)]
        fs.sort()
        fs.reverse()
        # test folder
        for folder in fs:
            if len(os.listdir(folder)) == 0:
                print(folder)
                shutil.rmtree(folder)
        # test if the output folder is empty
        if os.path.exists(target_folder) and len(os.listdir(target_folder)) == 0:
            shutil.rmtree(target_folder)


class FolderProcessing(CommonUtils):
    """
    recursively find folder of processing
    """

    def __init__(self, ops):
        if isinstance(ops, dict):
            # input folder
            self.input = os.path.abspath(ops['input'])
            # output folder
            self.output = os.path.abspath(ops['output'])
            # cpu number
            self.cpu = ops['cpu_number']
        else:
            # input folder
            self.input = os.path.abspath(ops.input)
            # output folder
            self.output = [os.path.abspath(ops.output) if ops.output is not None else None][0]
            # cpu number
            self.cpu = ops.cpu_number

        # test mode: True: 1, False: 2 data flow
        self.single_mode = self.output is None

    #########################################
    # this section is default batch process #
    # set all above parameters in argparse  #
    #########################################

    def __call__(self):
        """
        parallel processing on folders in file system
        :return: None
        """
        # find all patterns
        fs = glob.glob(os.path.join(self.input, '**/*'), recursive=True)
        fs = [x for x in fs if os.path.isdir(x)]
        if self.cpu != 1:
            pool = multiprocessing.Pool(self.cpu_count(self.cpu))
            pool.map(self.do_multiple_helper, fs)
        else:
            for in_folder in fs:
                self.do_multiple_helper(in_folder)
        if self.single_mode:
            self.remove_empty_folder(self.input)
        else:
            self.remove_empty_folder(self.output)

    def do_multiple_helper(self, in_folder):
        """
        prepare function for multiprocessing mapping
        :param in_folder: str; folder path to process
        :return: None
        """
        if not self.single_mode:
            # prepare output path
            truncated_path = in_folder[len(self.input) + 1:]
            out_folder = os.path.join(self.output, truncated_path)
            # make directories
            os.makedirs(out_folder, exist_ok=True)
            # do operation
            self.do(in_folder, out_folder)
        else:
            self.do(in_folder)

    #######
    # end #
    #######

    def do(self, *args):
        """
        do function will be implemented on folders
        """
        pass


class FileProcessing(CommonUtils):
    """
    recursively find file of processing
    """

    def __init__(self, ops):
        if isinstance(ops, dict):
            # input folder
            self.input = os.path.abspath(ops['input'])
            # output folder
            self.output = [os.path.abspath(ops['output']) if ops['output'] is not None else None][0]
            # input format
            self.in_format = ops['in_format']
            # output format
            self.out_format = ops['out_format']
            # cpu number
            self.cpu = ops['cpu_number']
        else:
            # input folder
            self.input = os.path.abspath(ops.input)
            # output folder
            self.output = [os.path.abspath(ops.output) if ops.output is not None else None][0]
            # input format
            self.in_format = ops.in_format
            # output format
            self.out_format = ops.out_format
            # cpu number
            self.cpu = ops.cpu_number

        # test mode: True: 1, False: 2 data flow
        self.single_mode = self.output is None or self.out_format is None
        # pattern identifier
        self.pattern_identifier = '\\'
        # is pattern
        self.is_pattern = self.pattern_identifier in self.in_format

    #########################################
    # this section is default batch process #
    # set all above parameters in argparse  #
    #########################################

    def __call__(self):
        """
        parallel processing on files in file system
        :return: None
        """
        # find all patterns
        if self.is_pattern:
            # if contains `pattern_identifier`, it is considered to be patterns
            fs = glob.glob(os.path.join(self.input, '**/' + self.in_format.replace(self.pattern_identifier, '')),
                           recursive=True)
        else:
            fs = glob.glob(os.path.join(self.input, '**/*.' + self.in_format), recursive=True)
        fs = [x for x in fs if os.path.isfile(x)]
        if self.cpu != 1:
            pool = multiprocessing.Pool(self.cpu_count(self.cpu))
            pool.map(self.do_multiple_helper, fs)
        else:
            for in_folder in fs:
                self.do_multiple_helper(in_folder)
        if self.single_mode:
            self.remove_empty_folder(self.input)
        else:
            self.remove_empty_folder(self.output)

    def do_multiple_helper(self, in_path):
        """
        prepare function for multiprocessing mapping
        :param in_path: str; file path to process
        :return: None
        """
        if not self.single_mode:
            # prepare output path
            truncated_path = os.path.split(in_path)[0][len(self.input) + 1:]
            out_folder = os.path.join(self.output, truncated_path)
            # make directories
            os.makedirs(out_folder, exist_ok=True)
            # do operation
            self.do_single(in_path, out_folder)
        else:
            self.do_single(in_path)

    def do_single(self, *args):
        """
        single processing on
        :return: None
        """
        # in_path: str; input file path
        # out_folder: str; output folder
        if not self.single_mode:
            in_path, out_folder = args[0], args[1]
            out_name = os.path.split(in_path)[1]
            if not self.is_pattern:
                # if not pattern, truncated the format and add a new one
                out_name = out_name[:-len(self.in_format)]
                out_path = os.path.join(out_folder, out_name) + self.out_format
            else:
                out_path = os.path.join(out_folder, out_name)
            # the 'do' function is main function for batch process
            self.do(in_path, out_path)
        else:
            in_path = args[0]
            self.do(in_path)

    #######
    # end #
    #######

    def do(self, *args):
        """
        do function will be implemented on files
        """
        pass
