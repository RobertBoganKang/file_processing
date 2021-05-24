import functools
import glob
import logging
import multiprocessing as mp
import os
import shutil
import signal
import time

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
            self._input = os.path.abspath(ops['input'])
            # output folder
            self._output = self._set_parser_value(ops, 'output', None, is_dict=True)
            # input format
            self._in_format = self._set_parser_value(ops, 'in_format', '??', is_dict=True)
            # output format
            self._out_format = self._set_parser_value(ops, 'out_format', None, is_dict=True)
            # cpu number
            self._cpu = self._set_parser_value(ops, 'cpu_number', 0, is_dict=True)
            # logger level
            self._logger_level = self._set_parser_value(ops, 'logger_level', 'info', is_dict=True)
        else:
            # input folder
            self._input = os.path.abspath(ops._input)
            # output folder
            self._output = self._set_parser_value(ops, 'output', None)
            # input format
            self._in_format = self._set_parser_value(ops, 'in_format', '??')
            # output format
            self._out_format = self._set_parser_value(ops, 'out_format', None)
            # cpu number
            self._cpu = self._set_parser_value(ops, 'cpu_number', 0)
            # logger level
            self._logger_level = self._set_parser_value(ops, 'logger_level', 'info')

        # fix output
        self._output = [os.path.abspath(self._output) if self._output is not None else None][0]
        # test mode: True: 1, False: 2 data flow
        self._single_mode = self._output is None or self._out_format is None
        # pattern identifier
        self._pattern_identifier = '\\'
        # is pattern
        self._is_pattern = self._pattern_identifier in self._in_format
        # in format is other pattern: `?` is no format, `??` is all format
        self._is_no_format = '?' in self._in_format
        self._is_all_format = self._in_format == '??'
        # if out format pattern follow the same as input
        self._is_same_out_format = self._in_format == '?'
        # empty folder counter
        self._empty_file_counter = 0
        self._total_file_number = None
        self._stop_cleaning_ratio = 0.2
        # logger
        self.logger = None
        self._logger_folder = 'log'
        self._log_path = os.path.join(self._logger_folder,
                                      time.strftime(f'log_%Y%m%d%H%M%S', time.localtime(time.time())) + '.log')
        self._get_logger()

    @staticmethod
    def _cpu_count(cpu):
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
    def _set_parser_value(ops, parser_name, default_value, is_dict=False):
        if parser_name in ops:
            if is_dict:
                return ops[parser_name]
            else:
                return eval('ops.' + parser_name)
        else:
            return default_value

    def _get_logger(self):
        """ get a logger """
        # makedir
        os.makedirs(self._logger_folder, exist_ok=True)

        # create a logger
        self.logger = logging.getLogger()
        if self._logger_level.lower() == 'info':
            self.logger.setLevel(logging.INFO)
        elif self._logger_level.lower() == 'warning':
            self.logger.setLevel(logging.WARNING)
        elif self._logger_level.lower() == 'error':
            self.logger.setLevel(logging.ERROR)
        elif self._logger_level.lower() == 'debug':
            self.logger.setLevel(logging.DEBUG)
        else:
            raise ValueError('config.yml: logger.logger_level parameter ERROR.')
        # create handler
        fh = logging.FileHandler(self._log_path, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        # define handler format
        formatter = logging.Formatter("%(asctime)s|%(levelname)s|%(filename)s[%(lineno)d]|%(message)s")
        fh.setFormatter(formatter)
        # add logger into handler
        self.logger.addHandler(fh)

    @staticmethod
    def _remove_empty_folder(target_folder):
        """
        target folder may empty, then remove it
        :return: None
        """
        for root, dirs, files in os.walk(target_folder, topdown=False):
            for name in dirs:
                dir_path = os.path.join(root, name)
                if not os.listdir(dir_path):
                    path = os.path.join(root, name)
                    shutil.rmtree(path)

    @staticmethod
    def _remove_empty_file(target_file):
        if os.path.exists(target_file) and os.path.getsize(target_file) == 0:
            os.remove(target_file)

    @staticmethod
    def _simplify_path(base, leaf):
        """ remove empty folders recursively to base folder"""
        if not os.path.exists(leaf):
            folder = leaf
            while True:
                folder = os.path.dirname(folder)
                if not os.listdir(folder):
                    shutil.rmtree(folder)
                elif folder == base:
                    break

    def _do_multiple_helper(self, in_path):
        """
        prepare function for multiprocessing mapping
        :param in_path: str; file path to process
        :return: None
        """
        if not self._single_mode:
            # prepare output path
            truncated_path = os.path.split(in_path)[0][len(self._input) + 1:]
            out_folder = os.path.join(self._output, truncated_path)
            # make directories
            os.makedirs(out_folder, exist_ok=True)
            # do operation
            self._do_single(in_path, out_folder)
        else:
            self._do_single(in_path)
        return in_path

    def _do_single(self, *args):
        """
        single processing on
        :return: None
        """
        # in_path: str; input file path
        # out_folder: str; output folder
        if not self._single_mode:
            in_path, out_folder = args[0], args[1]
            out_name = os.path.split(in_path)[1]
            if self._is_pattern or self._is_same_out_format:
                out_path = os.path.join(out_folder, out_name)
            else:
                # if not pattern, truncated the format and add a new one
                if len(self._in_format) > 0:
                    out_name = out_name[:-len(self._in_format)]
                else:
                    out_name += '.'
                out_path = os.path.join(out_folder, out_name) + self._out_format
            # the 'do' function is main function for batch process
            self.do(in_path, out_path)
        else:
            in_path = args[0]
            self.do(in_path)

    def do(self, *args):
        """
        do function will be implemented on files, please rewrite this method
        """
        pass

    def __call__(self):
        """
        parallel processing on files in file system
        :return: None
        """
        # find all patterns
        if self._is_pattern:
            # if contains `pattern_identifier`, it is considered to be patterns
            fs = glob.glob(os.path.join(self._input, '**/' + self._in_format.replace(self._pattern_identifier, '')),
                           recursive=True)
        else:
            if self._is_no_format:
                fs = glob.glob(os.path.join(self._input, '**/*' + self._in_format), recursive=True)
                if not self._is_all_format:
                    fs = [x for x in fs if '.' not in x]
                # reset input format to empty
                self._in_format = ''
            else:
                fs = glob.glob(os.path.join(self._input, '**/*.' + self._in_format), recursive=True)
        fs = [x for x in fs if os.path.isfile(x)]
        self._total_file_number = len(fs)

        if self._cpu != 1:
            pool = mp.Pool(self._cpu_count(self._cpu))
            with tqdm(total=len(fs)) as p_bar:
                def _callback_function(file_path):
                    # clean file path if few situation happen
                    self._empty_file_counter += 1
                    if not self._single_mode and (
                            self._empty_file_counter / self._total_file_number < self._stop_cleaning_ratio):
                        self._simplify_path(self._input, file_path)
                    # update pbar
                    p_bar.update()

                for f in fs:
                    pool.apply_async(self._do_multiple_helper, args=(f,),
                                     callback=_callback_function)
                # set multiprocessing within `tqdm` for process bar update
                pool.close()
                pool.join()
        else:
            for in_folder in fs:
                self._do_multiple_helper(in_folder)

        # clean output folder
        if not self._single_mode and (self._empty_file_counter / self._total_file_number >= self._stop_cleaning_ratio):
            self._remove_empty_folder(self._output)
        # remove empty log
        self._remove_empty_file(self._log_path)
        self._remove_empty_folder(self._logger_folder)
