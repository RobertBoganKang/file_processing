import glob
import multiprocessing
import os
import shutil
import time


class CommonUtils(object):
    """common tools for classes"""

    def __init__(self):
        # process indicator
        global _process_counter
        _process_counter = multiprocessing.Value('i', 0)
        self._process_starting_time = time.time()
        self.process_file = 'process.txt'
        self._process_total = None

    @staticmethod
    def time_conversion(second):
        return f'{int(second / 3600)}:{int(second / 60) % 60}:{int(second) % 60}'

    def process_update(self):
        _process_counter.value += 1
        ending_time = time.time()
        with open(self.process_file, 'w') as w:
            w.write('[process]-(' + str(round(_process_counter.value / self._process_total * 100, 5)) + '%)')
            time_consume = ending_time - self._process_starting_time
            velocity = time_consume / _process_counter.value
            time_remaining = (self._process_total - _process_counter.value) * velocity
            if velocity > 1:
                w.write('\t(' + str(round(velocity, 3)) + ')-[s/ea]')
            else:
                w.write('\t(' + str(round(1 / velocity, 3)) + ')-[ea/s]')
            w.write('\t[time]-(' + self.time_conversion(time_consume) + ')')
            w.write('\t[remain]-(' + self.time_conversion(time_remaining) + ')')
            w.write('\n')

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
                shutil.rmtree(folder)
        # test if the output folder is empty
        if os.path.exists(target_folder) and len(os.listdir(target_folder)) == 0:
            shutil.rmtree(target_folder)


class FolderProcessing(CommonUtils):
    """
    recursively find folder of processing
    """

    def __init__(self, ops):
        super().__init__()
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
        self.total = len(fs)
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

        # remove process indicator if done
        if os.path.exists(self.process_file):
            os.remove(self.process_file)

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

        # update process indicator
        self.process_update()

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
        super().__init__()
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
        # no format patter
        self.is_no_format = self.in_format == '?'

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
            if self.is_no_format:
                fs = glob.glob(os.path.join(self.input, '**/*' + self.in_format), recursive=True)
                fs = [x for x in fs if '.' not in x]
                # reset input format to empty
                self.in_format = ''
            else:
                fs = glob.glob(os.path.join(self.input, '**/*.' + self.in_format), recursive=True)
        fs = [x for x in fs if os.path.isfile(x)]
        self.total = len(fs)
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

        # remove process indicator if done
        if os.path.exists(self.process_file):
            os.remove(self.process_file)

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
                if len(self.in_format) > 0:
                    out_name = out_name[:-len(self.in_format)]
                else:
                    out_name += '.'
                out_path = os.path.join(out_folder, out_name) + self.out_format
            else:
                out_path = os.path.join(out_folder, out_name)
            # the 'do' function is main function for batch process
            self.do(in_path, out_path)
        else:
            in_path = args[0]
            self.do(in_path)

        # update process indicator
        self.process_update()

    #######
    # end #
    #######

    def do(self, *args):
        """
        do function will be implemented on files
        """
        pass
