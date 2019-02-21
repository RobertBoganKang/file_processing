import glob
import multiprocessing
import os
import shutil


class FileProcessing(object):
    """
    recursively find file of processing
    """

    def __init__(self, ops):
        # output folder
        self.output = os.path.abspath(ops.output)
        # input folder
        self.input = os.path.abspath(ops.input)
        # input format
        self.in_format = ops.in_format
        # output format
        self.out_format = ops.out_format
        # cpu number
        self.cpu = ops.cpu_number

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

    def remove_empty_folder(self):
        """
        output folder may empty, then remove it
        :return: None
        """
        # find all patterns
        fs = glob.glob(os.path.join(self.output, '**/*'), recursive=True)
        # select folders
        fs = [x for x in fs if os.path.isdir(x)]
        # test folder
        for folder in fs:
            if len(os.listdir(folder)) == 0:
                shutil.rmtree(folder)
        # test if the output folder is empty
        if len(os.listdir(self.output)) == 0:
            shutil.rmtree(self.output)

    def do_multiple(self):
        """
        parallel processing on files in file system
        :return: None
        """
        # find all patterns
        fs = glob.glob(os.path.join(self.input, '**/*.' + self.in_format), recursive=True)
        pool = multiprocessing.Pool(self.cpu_count())
        pool.map(self.do_multiple_helper, fs)
        self.remove_empty_folder()

    def do_multiple_helper(self, in_path):
        """
        prepare function for multiprocessing mapping
        :param in_path: str; file path to process
        :return: None
        """
        # prepare output path
        truncated_path = os.path.split(in_path)[0][len(self.input) + 1:]
        out_folder = os.path.join(self.output, truncated_path)
        # if not os.path.exists(out_folder):
        #     print('[{}] has been created successfully ~'.format(out_folder))
        os.makedirs(out_folder, exist_ok=True)
        # do operation
        self.do_single(in_path, out_folder)

    def do_single(self, in_path, out_folder):
        """
        single processing on
        :param in_path: str; input file path
        :param out_folder: str; output folder
        :return: None
        """
        out_name = os.path.split(in_path)[1][:-len(self.in_format)]
        out_path = os.path.join(out_folder, out_name) + self.out_format
        # the 'do_body' function is main function for batch process
        self.do_body(in_path, out_path)

    #######
    # end #
    #######

    def do_body(self, in_path, out_path):
        """
        do function will be implemented
        """
        pass
