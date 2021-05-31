import functools
import glob
import logging
import multiprocessing as mp
import os
import re
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
            self._input = self._set_parser_value(ops, 'input', None, is_dict=True)
            self._input_path_list = self._set_parser_value(ops, 'input_path_list', None, is_dict=True)
            self._in_format = self._set_parser_value(ops, 'in_format', '\\', is_dict=True)
            self._output = self._set_parser_value(ops, 'output', None, is_dict=True)
            self._out_format = self._set_parser_value(ops, 'out_format', None, is_dict=True)
            self._cpu = self._set_parser_value(ops, 'cpu_number', 0, is_dict=True)
            self._logger_level = self._set_parser_value(ops, 'logger_level', 'info', is_dict=True)
        else:
            self._input = self._set_parser_value(ops, 'input', None)
            self._input_path_list = self._set_parser_value(ops, 'input_path_list', None)
            self._in_format = self._set_parser_value(ops, 'in_format', '\\')
            self._output = self._set_parser_value(ops, 'output', None)
            self._out_format = self._set_parser_value(ops, 'out_format', None)
            self._cpu = self._set_parser_value(ops, 'cpu_number', 0)
            self._logger_level = self._set_parser_value(ops, 'logger_level', 'info')

        # input controls
        assert self._in_format is not None and len(self._in_format) > 0

        # fix input/output
        self._input = self.fix_path(self._input)
        self._input_path_list = self.fix_path(self._input_path_list)
        self._output = self.fix_path(self._output)
        # single mode: True: 1, False: 2 data flow
        self._single_mode = self._output is None or self._out_format is None
        # pattern identifier
        self._re_pattern_identifier = '\\'
        self._is_re_pattern = self._in_format.startswith(self._re_pattern_identifier)
        self._glob_pattern_identifier = '^'
        self._is_glob_pattern = self._in_format.startswith(self._glob_pattern_identifier)
        # empty folder counter
        self._empty_file_counter = 0
        self._total_file_number = None
        self._stop_each_file_cleaning_ratio = 0.1
        # logger
        self.logger = None
        self._logger_folder = 'log'
        self._log_path = os.path.join(self._logger_folder,
                                      time.strftime(f'log_%Y%m%d%H%M%S', time.localtime(time.time())) + '.log')
        self._get_logger()

    @staticmethod
    def fix_path(path):
        if path is None:
            return None
        else:
            return os.path.abspath(path)

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
        """ set parser value to default if needed """
        value = None
        if parser_name in ops:
            if is_dict:
                value = ops[parser_name]
            else:
                value = eval('ops.' + parser_name)
        if value is None:
            return default_value
        else:
            return value

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
            raise ValueError('ERROR: `logger_level` parameter ERROR.')
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
        """ if target folder is empty, then remove it """
        for root, dirs, files in os.walk(target_folder, topdown=False):
            for name in dirs:
                dir_path = os.path.join(root, name)
                if not os.listdir(dir_path):
                    path = os.path.join(root, name)
                    shutil.rmtree(path)
        # remove root
        if not os.listdir(target_folder):
            shutil.rmtree(target_folder)

    @staticmethod
    def _remove_empty_file(target_file_or_folder):
        """ if target file is empty, then remove it (or find within folder) """

        def rm_0_file(path):
            if os.path.isfile(path) and os.path.getsize(path) == 0:
                os.remove(path)

        if os.path.isfile(target_file_or_folder):
            rm_0_file(target_file_or_folder)
        elif os.path.isdir(target_file_or_folder):
            fs = glob.glob(os.path.join(target_file_or_folder, '**/*'), recursive=True)
            for f in fs:
                rm_0_file(f)

    @staticmethod
    def _simplify_path(base, leaf):
        """ remove empty folders recursively to base folder """
        if not os.path.exists(leaf):
            folder = leaf
            while True:
                folder = os.path.dirname(folder)
                if len(folder) < len(base):
                    break
                if os.path.exists(folder) and not os.listdir(folder):
                    shutil.rmtree(folder)

    def _do_multiple_helper(self, in_path):
        """ prepare function for multiprocessing mapping """
        if not self._single_mode:
            # prepare output path
            truncated_path = os.path.dirname(in_path)[len(self._input) + 1:]
            out_folder = os.path.join(self._output, truncated_path)
            # make directories
            os.makedirs(out_folder, exist_ok=True)
            # do operation
            out_path = self._do_single(in_path, out_folder)
            return out_path
        else:
            self._do_single(in_path)

    def _do_single(self, *args):
        """ single process """
        # in_path: str; input file path
        # out_folder: str; output folder
        if not self._single_mode:
            in_path, out_folder = args[0], args[1]
            out_name = os.path.split(in_path)[1]
            if self._is_re_pattern:
                out_path = os.path.join(out_folder, out_name)
            else:
                # if not pattern, truncated the format and add a new one
                out_name = out_name[:-len(self._in_format)]
                out_path = os.path.join(out_folder, out_name) + self._out_format
            # the 'do' function is main function for batch process
            self.do(in_path, out_path)
            return out_path
        # only use `in_path`
        else:
            in_path = args[0]
            self.do(in_path)

    def _find_fs(self):
        """ find files from glob function """
        # find all patterns from regular expression
        if self._is_re_pattern:
            # if contains `pattern_identifier`, it is considered to be regular expression restrictions
            pattern = self._in_format[len(self._re_pattern_identifier):]
            fs = glob.glob(os.path.join(self._input, '**/*'), recursive=True)
            fs = [x for x in fs if os.path.isfile(x) and re.search(pattern, os.path.split(x)[-1]) is not None]
        elif self._is_glob_pattern:
            pattern = self._in_format[len(self._glob_pattern_identifier):]
            fs = glob.glob(os.path.join(self._input, '**/' + pattern), recursive=True)
            fs = [x for x in fs if os.path.isfile(x)]
        else:
            fs = glob.glob(os.path.join(self._input, '**/*.' + self._in_format), recursive=True)
            fs = [x for x in fs if os.path.isfile(x)]
        return fs

    @staticmethod
    def _get_common_path(path_a, path_b):
        """ get common path from two given paths """
        i = 0
        while i < min(len(path_a), len(path_b)):
            if path_a[i] == path_b[i]:
                i += 1
            else:
                break
        return path_a[:i]

    def _read_fs(self):
        """ read paths from text file: one line with one path """
        if not os.path.exists(self._input_path_list):
            raise FileNotFoundError(f'ERROR: [{self._input_path_list}] not found!')
        fs = []
        with open(self._input_path_list, 'r') as f:
            lines = f.readlines()
            common_path = lines[0]
            for line in lines:
                path = os.path.abspath(line.strip())
                if self._is_re_pattern:
                    pattern = self._in_format[len(self._re_pattern_identifier):]
                    condition = re.search(pattern, os.path.split(path)[-1]) is not None
                else:
                    condition = path.endswith('.' + self._in_format)
                if os.path.isfile(path) and condition:
                    fs.append(path)
                    common_path = self._get_common_path(path, common_path)
        return common_path, fs

    @staticmethod
    def api_change_format(path, out_format):
        """ change format API """
        return os.path.splitext(path)[0] + '.' + out_format

    def do(self, *args):
        """ do function will be implemented on files, please rewrite this method """
        pass

    def __call__(self):
        """ parallel processing on files in file system """
        if self._input_path_list is not None:
            self._input, fs = self._read_fs()
        elif self._input is not None:
            fs = self._find_fs()
        else:
            raise ValueError('ERROR: input not given, `input` or `input_path_list` is required!')
        self._total_file_number = len(fs)
        if not self._total_file_number:
            raise FileNotFoundError('ERROR: no file has been found!')

        if self._cpu != 1:
            pool = mp.Pool(self._cpu_count(self._cpu))
            with tqdm(total=len(fs)) as p_bar:
                def _callback_function(file_path):
                    # clean file path if few situation happen
                    if not os.path.exists(file_path):
                        self._empty_file_counter += 1
                    if not self._single_mode and (
                            self._empty_file_counter / self._total_file_number < self._stop_each_file_cleaning_ratio):
                        self._simplify_path(self._output, file_path)
                    # update p_bar
                    p_bar.update()

                for f in fs:
                    pool.apply_async(self._do_multiple_helper, args=(f,), callback=_callback_function)
                # set multiprocessing within `tqdm` for process bar update
                pool.close()
                pool.join()
        else:
            for f in fs:
                self._do_multiple_helper(f)

        # clean output folder
        if not self._single_mode and (
                self._empty_file_counter / self._total_file_number >= self._stop_each_file_cleaning_ratio):
            self._remove_empty_folder(self._output)
        # remove empty logs
        self._remove_empty_file(self._logger_folder)
        self._remove_empty_folder(self._logger_folder)
