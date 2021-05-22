import functools
import glob
import multiprocessing as mp
import os
import shutil
import signal

from tqdm import tqdm


def timeout(seconds):
    """
    https://cloud.tencent.com/developer/article/1043966
    :param seconds: int; time seconds
    :return: wrapper function
    """
    seconds = int(seconds)

    def decorated(func):

        # noinspection PyUnusedLocal
        def _handle_timeout(signum, frame):
            print('<timeout error>')
            raise TimeoutError()

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            # noinspection PyBroadException
            try:
                func(*args, **kwargs)
            except Exception:
                signal.alarm(0)

        return functools.wraps(func)(wrapper)

    return decorated


class FileProcessing(object):
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
        # in format is other pattern: `?` is no format, `??` is all format
        self.is_no_format = '?' in self.in_format
        self.is_all_format = self.in_format == '??'
        # if out format pattern follow the same as input
        self.is_same_out_format = self.in_format == '?'
        # empty folder counter
        self.empty_file_counter = 0
        self.total_file_number = None
        self.stop_cleaning_ratio = 0.2

    @staticmethod
    def cpu_count(cpu):
        """
        get the cpu number
        :return: int; valid cpu number
        """
        max_cpu = mp.cpu_count()
        if 0 < cpu <= max_cpu:
            return cpu
        elif cpu == 0 or cpu > max_cpu:
            return max_cpu
        elif 1 - max_cpu < cpu < 0:
            return max_cpu + cpu
        else:
            return 1

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
                if not self.is_all_format:
                    fs = [x for x in fs if '.' not in x]
                # reset input format to empty
                self.in_format = ''
            else:
                fs = glob.glob(os.path.join(self.input, '**/*.' + self.in_format), recursive=True)
        fs = [x for x in fs if os.path.isfile(x)]
        self.total_file_number = len(fs)

        if self.cpu != 1:
            pool = mp.Pool(self.cpu_count(self.cpu))
            with tqdm(total=len(fs)) as p_bar:
                def _callback_function(file_path):
                    # clean file path if few situation happen
                    self.empty_file_counter += 1
                    if not self.single_mode and (
                            self.empty_file_counter / self.total_file_number < self.stop_cleaning_ratio):
                        self.simplify_path(self.input, file_path)
                    # update pbar
                    p_bar.update()

                for f in fs:
                    pool.apply_async(self.do_multiple_helper, args=(f,),
                                     callback=_callback_function)
            pool.close()
            pool.join()
        else:
            for in_folder in fs:
                self.do_multiple_helper(in_folder)

        # clean output folder
        if not self.single_mode and (self.empty_file_counter / self.total_file_number >= self.stop_cleaning_ratio):
            self.remove_empty_folder(self.output)

    @staticmethod
    def simplify_path(base, leaf):
        if not os.path.exists(leaf):
            folder = leaf
            while True:
                folder = os.path.dirname(folder)
                if len(os.listdir(folder)) == 0:
                    print('remove', folder)
                    shutil.rmtree(folder)
                elif folder == base:
                    break

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
        return in_path

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
            if self.is_pattern or self.is_same_out_format:
                out_path = os.path.join(out_folder, out_name)
            else:
                # if not pattern, truncated the format and add a new one
                if len(self.in_format) > 0:
                    out_name = out_name[:-len(self.in_format)]
                else:
                    out_name += '.'
                out_path = os.path.join(out_folder, out_name) + self.out_format
            # the 'do' function is main function for batch process
            self.do(in_path, out_path)
        else:
            in_path = args[0]
            self.do(in_path)

    def do(self, *args):
        """
        do function will be implemented on files
        """
        pass
