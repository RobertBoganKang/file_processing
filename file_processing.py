import glob
import multiprocessing
import os
import shutil


class FileProcessing(object):
    """
    recursively find file of processing
    """

    def __init__(self, ops):
        # input folder
        self.input = os.path.abspath(ops.input)
        # output folder
        self.output = os.path.abspath(ops.output)
        # input format
        self.in_format = ops.in_format
        # output format
        self.out_format = ops.out_format
        # cpu number
        self.cpu = ops.cpu_number
        # test mode: True: 1, False: 2 data flow
        self.single_mode = self.output is None or self.out_format is None

    #########################################
    # this section is default batch process #
    # set all above parameters in argparse  #
    #########################################

    def cpu_count(self):
        """
        get the cpu number
        :return: int; valid cpu number
        """
        cpu_count = self.cpu
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
        # test folder
        for folder in fs:
            if len(os.listdir(folder)) == 0:
                shutil.rmtree(folder)
        # test if the output folder is empty
        if os.path.exists(target_folder) and len(os.listdir(target_folder)) == 0:
            shutil.rmtree(target_folder)

    def do_multiple(self):
        """
        parallel processing on files in file system
        :return: None
        """
        # find all patterns
        fs = glob.glob(os.path.join(self.input, '**/*.' + self.in_format), recursive=True)
        pool = multiprocessing.Pool(self.cpu_count())
        pool.map(self.do_multiple_helper, fs)
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
            out_name = os.path.split(in_path)[1][:-len(self.in_format)]
            out_path = os.path.join(out_folder, out_name) + self.out_format
            # the 'do_body' function is main function for batch process
            self.do_body(in_path, out_path)
        else:
            in_path = args[0]
            self.do_body(in_path)

    #######
    # end #
    #######

    def do_body(self, *args):
        """
        do function will be implemented
        """
        pass
