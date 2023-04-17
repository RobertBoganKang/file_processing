import functools
import logging
import multiprocessing as mp
import os
import pathlib
import re
import shutil
import signal
import time
from inspect import signature

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
        self.fp_input = self._set_parser_value(ops, 'input', None)
        self.fp_in_format = self._set_parser_value(ops, 'in_format', '\\')
        self.fp_output = self._set_parser_value(ops, 'output', None)
        self.fp_out_format = self._set_parser_value(ops, 'out_format', None)
        self.fp_cpu = self._set_parser_value(ops, 'cpu_number', 0)
        self.fp_logger_level = self._set_parser_value(ops, 'logger_level', None)
        self.fp_paths = []

        # initialize parameter
        self._initialize_parameters()
        self._initialize_paths()

    def __call__(self):
        """ parallel processing on files in file system """
        self._update_paths_len()

        def _callback_function(args):
            # update p_bar
            p_bar.update()
            # custom callback function
            if self._callback_input_length == 0:
                self.callback()
            elif self._callback_input_length == 1:
                self.callback(args)
            elif self._callback_input_length == self._callback_do_input_length:
                self.callback(*args)
            else:
                raise AttributeError(f'ERROR: number of inputs for callback not matched '
                                     f'({self._callback_input_length}!={self._callback_do_input_length})!')
            # clean file path if few situation happen
            if not self._single_mode:
                in_path, out_path = args
                if not os.path.exists(out_path):
                    self._empty_file_counter += 1
                if self._empty_file_counter / self._total_file_number < self._stop_each_file_cleaning_ratio:
                    self._simplify_path(self.fp_output, out_path)

        with tqdm(total=len(self.fp_paths), dynamic_ncols=True) as p_bar:
            if self.fp_cpu != 1:
                pool = mp.Pool(self._cpu_count(self.fp_cpu))

                for f in self.fp_paths:
                    pool.apply_async(self._do_multiple, args=(f,), callback=_callback_function)
                # set multiprocessing within `tqdm` for process bar update
                pool.close()
                pool.join()
            else:
                for f in self.fp_paths:
                    result = self._do_multiple(f)
                    _callback_function(result)

        # clean output folder
        if not self._single_mode and (
                self._empty_file_counter / self._total_file_number >= self._stop_each_file_cleaning_ratio):
            self._remove_empty_folder(self.fp_output)
        # remove empty logs
        if self.fp_logger_level is not None:
            self._remove_empty_file(self._logger_folder)
            self._remove_empty_folder(self._logger_folder)

    def __len__(self):
        return len(self.fp_paths)

    def __getitem__(self, item):
        return self.fp_paths[item]

    def __add__(self, other_fp_obj):
        # format should match
        assert self.fp_in_format == other_fp_obj.fp_in_format
        assert self.fp_out_format == other_fp_obj.fp_out_format
        self.fp_input, self.fp_paths = self._tidy_fs(list(set(self.fp_paths) | set(other_fp_obj.fp_paths)))
        return self

    def __sub__(self, other_fp_obj):
        # format should match
        assert self.fp_in_format == other_fp_obj.fp_in_format
        assert self.fp_out_format == other_fp_obj.fp_out_format
        self.fp_input, self.fp_paths = self._tidy_fs(list(set(self.fp_paths) - set(other_fp_obj.fp_paths)))
        return self

    def _initialize_parameters(self):
        # input controls
        assert self.fp_input is not None and self.fp_in_format is not None and len(self.fp_in_format) > 0
        if not os.path.exists(self.fp_input):
            raise FileNotFoundError(f'ERROR: input `{self.fp_input}` not found!')
        # fix input/output
        self.fp_input = self._fix_path(self.fp_input)
        self.fp_output = self._fix_path(self.fp_output)
        self.file_encoding = 'utf-8'
        # single mode: True: 1, False: 2 data flow
        self._single_mode = self.fp_output is None
        if not self._single_mode and self.fp_out_format is None:
            self.fp_out_format = ''
        # pattern identifier
        self._re_pattern_identifier = '\\'
        self._is_re_pattern = self.fp_in_format.startswith(self._re_pattern_identifier)
        self._glob_pattern_identifier = '^'
        self._is_glob_pattern = self.fp_in_format.startswith(self._glob_pattern_identifier)
        # empty folder counter
        self._empty_file_counter = 0
        self._total_file_number = None
        self._stop_each_file_cleaning_ratio = 0.1
        # logger (easy to break in multiprocessing)
        if self.fp_logger_level is not None:
            self._logger_folder = 'log'
            self._log_path = os.path.join(self._logger_folder,
                                          time.strftime(f'log_%Y%m%d%H%M%S', time.localtime(time.time())) + '.log')

            self.logger = self._get_logger()
        # callback number of inputs
        self._callback_input_length = len(signature(self.callback).parameters)
        self._callback_do_input_length = len(signature(self.do).parameters)

    def _initialize_paths(self):
        # main
        if os.path.isfile(self.fp_input):
            # if not meet input format requirement: consider it as paths text file
            if not self._check_input_file_path(self.fp_input):
                self.fp_input, self.fp_paths = self._read_fs()
            # else: single process
            else:
                self._do_once()
                return
        elif os.path.isdir(self.fp_input):
            self.fp_paths = self._find_fs()
        else:
            raise ValueError('ERROR: input not given, `input` as a file/directory is required!')
        self._update_paths_len()

    def _update_paths_len(self):
        # multiple process
        self._total_file_number = len(self.fp_paths)
        if not self._total_file_number:
            raise FileNotFoundError('ERROR: no file has been found!')

    @staticmethod
    def _fix_path(path):
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
    def _set_parser_value(ops, parser_name, default_value):
        """ set parser value to default if needed """
        if not isinstance(ops, dict):
            ops = ops.__dict__
        if parser_name not in ops or ops[parser_name] is None:
            return default_value
        else:
            return ops[parser_name]

    def _get_logger(self):
        """ get a logger """
        # makedir
        os.makedirs(self._logger_folder, exist_ok=True)

        # create a logger
        logger = mp.get_logger()
        if self.fp_logger_level.lower() == 'info':
            logger.setLevel(logging.INFO)
        elif self.fp_logger_level.lower() == 'warning':
            logger.setLevel(logging.WARNING)
        elif self.fp_logger_level.lower() == 'error':
            logger.setLevel(logging.ERROR)
        elif self.fp_logger_level.lower() == 'debug':
            logger.setLevel(logging.DEBUG)
        else:
            raise AttributeError('ERROR: `logger_level` parameter ERROR.')
        # create handler
        fh = logging.FileHandler(self._log_path, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        # define handler format
        formatter = logging.Formatter("%(asctime)s|%(levelname)s|%(filename)s[%(lineno)d]|%(message)s")
        fh.setFormatter(formatter)
        # add logger into handler
        logger.addHandler(fh)
        return logger

    @staticmethod
    def _glob_files(base_folder, pattern):
        fs = []
        for file in pathlib.Path(base_folder).glob(pattern):
            fs.append(str(file))
        return fs

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
        if os.path.isdir(target_folder) and not os.listdir(target_folder):
            shutil.rmtree(target_folder)

    def _remove_empty_file(self, target_file_or_folder):
        """ if target file is empty, then remove it (or find within folder) """

        def rm_0_file(path):
            if os.path.isfile(path) and os.path.getsize(path) == 0:
                os.remove(path)

        if os.path.isfile(target_file_or_folder):
            rm_0_file(target_file_or_folder)
        elif os.path.isdir(target_file_or_folder):
            fs = self._glob_files(target_file_or_folder, '**/*')
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
                # noinspection PyBroadException
                try:
                    if os.path.exists(folder) and not os.listdir(folder):
                        shutil.rmtree(folder)
                    else:
                        break
                except Exception:
                    break

    def _do_multiple(self, in_path):
        """ prepare function for multiprocessing mapping """
        if not self._single_mode:
            # prepare output path
            truncated_path = os.path.dirname(in_path)[len(self.fp_input) + 1:]
            out_folder = os.path.join(self.fp_output, truncated_path)
            # make directories
            os.makedirs(out_folder, exist_ok=True)
            # do operation
            out_path = self._do_single(in_path, out_folder)
            return in_path, out_path
        else:
            self._do_single(in_path)
            return in_path

    def _do_single(self, *args):
        """ single process """
        # in_path: str; input file path
        # out_folder: str; output folder
        if not self._single_mode:
            in_path, out_folder = args
            out_name = os.path.split(in_path)[1]
            # truncated the format and add a new one
            if self._is_re_pattern or self._is_glob_pattern:
                out_name = os.path.splitext(out_name)[0]
            else:
                out_name = out_name[:-len(self.fp_in_format) - 1]
            if self.fp_out_format != '':
                out_name += '.'
            out_name += self.fp_out_format
            out_path = os.path.join(out_folder, out_name)
            # the 'do' function is main function for batch process
            self.do(in_path, out_path)
            return out_path
        # only use `in_path`
        else:
            in_path = args[0]
            self.do(in_path)
            return in_path

    def _find_fs(self):
        """ find files from glob function """
        # find all patterns from regular expression
        if self._is_re_pattern:
            # if contains `pattern_identifier`, it is considered to be regular expression restrictions
            pattern = self.fp_in_format[len(self._re_pattern_identifier):]
            fs = self._glob_files(self.fp_input, '**/*')
            fs = [x for x in fs if os.path.isfile(x) and re.search(pattern, os.path.split(x)[-1]) is not None]
        elif self._is_glob_pattern:
            pattern = self.fp_in_format[len(self._glob_pattern_identifier):]
            fs = self._glob_files(self.fp_input, '**/' + pattern)
            fs = [x for x in fs if os.path.isfile(x)]
        else:
            fs = self._glob_files(self.fp_input, '**/' + '**/*.' + self.fp_in_format)
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

    def _check_input_file_path(self, in_path):
        """ check file that match the input format """
        if self._is_re_pattern:
            pattern = self.fp_in_format[len(self._re_pattern_identifier):]
            condition = re.search(pattern, os.path.split(in_path)[-1]) is not None
        else:
            condition = in_path.endswith('.' + self.fp_in_format)
        return condition

    def _tidy_fs(self, lines):
        fs = []
        common_path = lines[0]
        for line in lines:
            path = os.path.abspath(line.strip())
            condition = self._check_input_file_path(path)
            if os.path.isfile(path) and condition:
                fs.append(path)
                common_path = self._get_common_path(path, common_path)
        # tidy path
        common_path = os.path.dirname(common_path)
        return common_path, fs

    def _read_fs(self):
        """
        read paths from text file: one line with one path
        else: only one input file
        """
        with open(self.fp_input, 'r', encoding=self.file_encoding) as f:
            lines = f.readlines()
        common_path, fs = self._tidy_fs(lines)
        return common_path, fs

    def _do_once(self):
        """
        process once if:
        --> input format == `in_format`
        --> output format == `out_format` (optional)
        """
        attributes = [self.fp_input]
        if not self._single_mode:
            if self.fp_output.endswith(self.fp_out_format):
                attributes.append(self.fp_output)
            else:
                raise AttributeError('ERROR: output format should match at single process!')
        self.do(*attributes)

    def do(self, *args):
        """
        do function will be implemented on main files, please rewrite this method.
        --> refer the file `template.py`.
        """
        pass

    def callback(self, *args):
        """
        define custom callback function.
        """
        pass

    @staticmethod
    def fp_change_format(path, out_format):
        """ change format API """
        return os.path.splitext(path)[0] + '.' + out_format
