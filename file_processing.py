import functools
import logging
import multiprocessing as mp
import os
import pathlib
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
        self.input = self._set_parser_value(ops, 'input', None)
        self.in_format = self._set_parser_value(ops, 'in_format', '\\')
        self.output = self._set_parser_value(ops, 'output', None)
        self.out_format = self._set_parser_value(ops, 'out_format', None)
        self.cpu = self._set_parser_value(ops, 'cpu_number', 0)
        self.logger_level = self._set_parser_value(ops, 'logger_level', None)

    def _initialize_parameters(self):
        # input controls
        assert self.input is not None and self.in_format is not None and len(self.in_format) > 0
        if not os.path.exists(self.input):
            raise FileNotFoundError(f'ERROR: input `{self.input}` not found!')
        # fix input/output
        self.input = self._fix_path(self.input)
        self.output = self._fix_path(self.output)
        self.file_encoding = 'utf-8'
        # single mode: True: 1, False: 2 data flow
        self._single_mode = self.output is None
        if not self._single_mode and self.out_format is None:
            self.out_format = ''
        # pattern identifier
        self._re_pattern_identifier = '\\'
        self._is_re_pattern = self.in_format.startswith(self._re_pattern_identifier)
        self._glob_pattern_identifier = '^'
        self._is_glob_pattern = self.in_format.startswith(self._glob_pattern_identifier)
        # empty folder counter
        self._empty_file_counter = 0
        self._total_file_number = None
        self._stop_each_file_cleaning_ratio = 0.1
        # logger (easy to break in multiprocessing)
        if self.logger_level is not None:
            self._logger_folder = 'log'
            self._log_path = os.path.join(self._logger_folder,
                                          time.strftime(f'log_%Y%m%d%H%M%S', time.localtime(time.time())) + '.log')

            self.logger = self._get_logger()

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
        value = None
        if parser_name in ops:
            if isinstance(ops, dict):
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
        logger = mp.get_logger()
        if self.logger_level.lower() == 'info':
            logger.setLevel(logging.INFO)
        elif self.logger_level.lower() == 'warning':
            logger.setLevel(logging.WARNING)
        elif self.logger_level.lower() == 'error':
            logger.setLevel(logging.ERROR)
        elif self.logger_level.lower() == 'debug':
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
            truncated_path = os.path.dirname(in_path)[len(self.input) + 1:]
            out_folder = os.path.join(self.output, truncated_path)
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
            in_path, out_folder = args
            out_name = os.path.split(in_path)[1]
            # truncated the format and add a new one
            if self._is_re_pattern or self._is_glob_pattern:
                out_name = os.path.splitext(out_name)[0]
                if self.out_format != '':
                    out_name += '.'
            else:
                out_name = out_name[:-len(self.in_format)]
            out_name += self.out_format
            out_path = os.path.join(out_folder, out_name)
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
            pattern = self.in_format[len(self._re_pattern_identifier):]
            fs = self._glob_files(self.input, '**/*')
            fs = [x for x in fs if os.path.isfile(x) and re.search(pattern, os.path.split(x)[-1]) is not None]
        elif self._is_glob_pattern:
            pattern = self.in_format[len(self._glob_pattern_identifier):]
            fs = self._glob_files(self.input, '**/' + pattern)
            fs = [x for x in fs if os.path.isfile(x)]
        else:
            fs = self._glob_files(self.input, '**/' + '**/*.' + self.in_format)
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
            pattern = self.in_format[len(self._re_pattern_identifier):]
            condition = re.search(pattern, os.path.split(in_path)[-1]) is not None
        else:
            condition = in_path.endswith('.' + self.in_format)
        return condition

    def _read_fs(self):
        """
        read paths from text file: one line with one path
        else: only one input file
        """
        fs = []
        with open(self.input, 'r', encoding=self.file_encoding) as f:
            lines = f.readlines()
            common_path = lines[0]
            for line in lines:
                path = os.path.abspath(line.strip())
                condition = self._check_input_file_path(path)
                if os.path.isfile(path) and condition:
                    fs.append(path)
                    common_path = self._get_common_path(path, common_path)
        return common_path, fs

    def _do_once(self):
        """
        process once if:
        --> input format == `in_format`
        --> output format == `out_format` (optional)
        """
        attributes = [self.input]
        if not self._single_mode:
            if self.output.endswith(self.out_format):
                attributes.append(self.output)
            else:
                raise AttributeError('ERROR: output format should match at single process!')
        self.do(*attributes)

    def do(self, *args):
        """
        do function will be implemented on main files, please rewrite this method.
        --> refer the file `template.py`.
        """
        pass

    def __call__(self):
        """ parallel processing on files in file system """
        # initialize parameter
        self._initialize_parameters()
        # main
        if os.path.isfile(self.input):
            # if not meet input format requirement: consider it as paths text file
            condition = self._check_input_file_path(self.input)
            if not condition:
                self.input, fs = self._read_fs()
            # else: single process
            else:
                self._do_once()
                return
        elif os.path.isdir(self.input):
            fs = self._find_fs()
        else:
            raise ValueError('ERROR: input not given, `input` as a file/directory is required!')
        # multiple process
        self._total_file_number = len(fs)
        if not self._total_file_number:
            raise FileNotFoundError('ERROR: no file has been found!')

        def _callback_function(out_path):
            # update p_bar
            p_bar.update()
            # clean file path if few situation happen
            if not self._single_mode:
                if not os.path.exists(out_path):
                    self._empty_file_counter += 1
                if not self._single_mode and (
                        self._empty_file_counter / self._total_file_number < self._stop_each_file_cleaning_ratio):
                    self._simplify_path(self.output, out_path)

        with tqdm(total=len(fs), dynamic_ncols=True) as p_bar:
            if self.cpu != 1:
                pool = mp.Pool(self._cpu_count(self.cpu))

                for f in fs:
                    pool.apply_async(self._do_multiple, args=(f,), callback=_callback_function)
                # set multiprocessing within `tqdm` for process bar update
                pool.close()
                pool.join()
            else:
                for f in fs:
                    result = self._do_multiple(f)
                    _callback_function(result)

        # clean output folder
        if not self._single_mode and (
                self._empty_file_counter / self._total_file_number >= self._stop_each_file_cleaning_ratio):
            self._remove_empty_folder(self.output)
        # remove empty logs
        if self.logger_level is not None:
            self._remove_empty_file(self._logger_folder)
            self._remove_empty_folder(self._logger_folder)

    @staticmethod
    def api_change_format(path, out_format):
        """ change format API """
        return os.path.splitext(path)[0] + '.' + out_format
