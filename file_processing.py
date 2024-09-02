import concurrent.futures
import functools
import glob
import operator
import os
import pathlib
import re
import shutil
import signal
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from copy import copy
from inspect import signature

import numpy as np
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
        self.fp_cpu = self._set_parser_value(ops, 'cpu_number', 1)
        self.fp_multi_what = self._set_parser_value(ops, 'multi_what', 'mp')
        self.fp_paths = []

        # initialize parameter
        self._initialize_parameters()
        self._initialize_paths()

    def __call__(self):
        """ parallel processing on files in file system """

        self.before()
        # do once
        if self._do_once_status:
            args = self._do_once()
            self._run_callback(args)
            return

        if self._file_iterator_mode:
            self._process_imp_imt()
        else:
            self._process_mp_mt()

        # clean output folder
        self._clean_output_folder()

    def __len__(self):
        self._update_paths_len()
        return len(self.fp_paths)

    def __getitem__(self, item):
        return self.fp_paths[item]

    def __or__(self, other_fp_obj):
        return self._set_operators(other_fp_obj, operator.or_)

    def __xor__(self, other_fp_obj):
        return self._set_operators(other_fp_obj, operator.xor)

    def __and__(self, other_fp_obj):
        return self._set_operators(other_fp_obj, operator.and_)

    def __sub__(self, other_fp_obj):
        return self._set_operators(other_fp_obj, operator.sub)

    def _initialize_parameters(self):
        # input controls
        assert self.fp_input is not None and self.fp_in_format is not None and len(self.fp_in_format) > 0
        if not os.path.exists(self.fp_input):
            raise FileNotFoundError(f'ERROR: input `{self.fp_input}` not found!')
        # fix input/output
        self.fp_input = self._fix_path(self.fp_input)
        self.fp_output = self._fix_path(self.fp_output)
        # single mode: True: 1, False: 2 data flow
        self._single_args_mode = self.fp_output is None
        if not self._single_args_mode and self.fp_out_format is None:
            self.fp_out_format = ''
        # pattern identifier
        self._re_pattern_identifier = '\\'
        self._is_re_pattern = self.fp_in_format.startswith(self._re_pattern_identifier)
        self._glob_pattern_identifier = '^'
        self._is_glob_pattern = self.fp_in_format.startswith(self._glob_pattern_identifier)
        self._skip_pattern_identifier = '!'
        self._is_skip_pattern = self.fp_in_format.startswith(self._skip_pattern_identifier)
        # empty folder counter
        self._empty_file_counter = 0
        self._total_file_number = None
        self._stop_each_file_cleaning_ratio = 0.1
        # callback number of inputs
        self._callback_input_length = len(signature(self.callback).parameters)
        self._callback_do_input_length = len(signature(self.do).parameters)
        # initialize other parameters
        self._do_once_status = False
        # file iterator mode, this mode do not separate search and process file, but do together
        self._file_iterator_mode = self.fp_multi_what[0] == 'i'

    def _initialize_paths(self):
        if os.path.isfile(self.fp_input):
            # if not meet input format requirement: consider it as paths text file
            if not self._check_input_file_path(self.fp_input):
                self.fp_input, self.fp_paths = self._read_fs()
                # fix parameters
                self._file_iterator_mode = False
                self.fp_multi_what = self.fp_multi_what.replace('i', '')
            # else: single process
            else:
                self._do_once_status = True
                return
        elif os.path.isdir(self.fp_input):
            if self._file_iterator_mode:
                # if `multi_what` is iterator mode, do not search files
                return
            else:
                self.fp_paths = self._find_fs()
        else:
            raise ValueError('ERROR: input not given, `input` as a file/directory is required!')
        self._update_paths_len()

    def _set_operators(self, other_fp_obj, func):
        if self._file_iterator_mode:
            raise ValueError('ERROR: iterator mode cannot use operator.')
        new_obj = copy(self)
        self._check_format(other_fp_obj)
        new_obj.fp_input, new_obj.fp_paths = self._tidy_fs(
            list(
                func(set(self.fp_paths), set(other_fp_obj.fp_paths))
            )
        )
        return new_obj

    def _update_paths_len(self):
        self._total_file_number = len(self.fp_paths)
        if not self._total_file_number:
            raise FileNotFoundError('ERROR: no file has been found!')

    def _check_format(self, obj):
        """ format should match """
        assert self.fp_in_format == obj.fp_in_format
        assert self.fp_out_format == obj.fp_out_format

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
        max_cpu = os.cpu_count()
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

    @staticmethod
    def _glob_files(base_folder, pattern):
        return pathlib.Path(base_folder).glob(pattern)

    @staticmethod
    def _remove_empty_folder(target_folder):
        """ if target folder is empty, then remove it """
        for root, dirs, files in os.walk(target_folder, topdown=False):
            for name in dirs:
                dir_path = os.path.join(root, name)
                if not os.listdir(str(dir_path)):
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

    def _do_multi_mapping(self, in_path):
        """ prepare function for multiple mapping """
        if not self._single_args_mode:
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
        if not self._single_args_mode:
            in_path, out_folder = args
            out_name = os.path.split(in_path)[1]
            # truncated the format and add a new one
            if self._is_re_pattern or self._is_glob_pattern or self._is_skip_pattern:
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
        # only use one `path`
        else:
            path = args[0]
            self.do(path)
            return path

    def _find_fs(self):
        """ find files from glob function """
        # find all patterns from regular expression
        if self._is_re_pattern:
            # if contains `pattern_identifier`, it is considered to be regular expression restrictions
            pattern = self.fp_in_format[len(self._re_pattern_identifier):]
            fs = self._glob_files(self.fp_input, '**/*')
            fs = [str(x) for x in fs if os.path.isfile(x) and re.search(pattern, os.path.split(x)[-1]) is not None]
        elif self._is_glob_pattern:
            pattern = self.fp_in_format[len(self._glob_pattern_identifier):]
            fs = self._glob_files(self.fp_input, '**/' + pattern)
            fs = [str(x) for x in fs if os.path.isfile(x)]
        elif self._is_skip_pattern:
            fs = self._glob_files(self.fp_input, '**/*')
            fs = [str(x) for x in fs]
        else:
            fs = self._glob_files(self.fp_input, '**/*.' + self.fp_in_format)
            fs = [str(x) for x in fs if os.path.isfile(x)]
        return fs

    def _find_fs_iterator(self):
        if self._is_re_pattern:
            pattern = self.fp_in_format[len(self._re_pattern_identifier):]
            for x in glob.iglob(os.path.join(f'{self.fp_input}', '**/*'), recursive=True):
                if os.path.isfile(x) and re.search(pattern, os.path.split(x)[-1]) is not None:
                    yield x
        elif self._is_glob_pattern:
            pattern = self.fp_in_format[len(self._glob_pattern_identifier):]
            for x in glob.iglob(os.path.join(f'{self.fp_input}', '**/' + pattern), recursive=True):
                if os.path.isfile(x):
                    yield x
        elif self._is_skip_pattern:
            for x in glob.iglob(os.path.join(f'{self.fp_input}', '**/*'), recursive=True):
                yield x
        else:
            for x in glob.iglob(os.path.join(f'{self.fp_input}', '**/*.' + self.fp_in_format), recursive=True):
                if os.path.isfile(x):
                    yield x

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
        """ check file that match the input format, and its existence """
        if self._is_re_pattern:
            pattern = self.fp_in_format[len(self._re_pattern_identifier):]
            condition = re.search(pattern, os.path.split(in_path)[-1]) is not None
            condition = condition and os.path.exists(in_path)
        else:
            condition = in_path.endswith('.' + self.fp_in_format)
            condition = condition and os.path.exists(in_path)
        return condition

    def _clean_output_folder(self):
        if not self._single_args_mode and (
                self._empty_file_counter / self._total_file_number >= self._stop_each_file_cleaning_ratio):
            self._remove_empty_folder(self.fp_output)

    def _tidy_fs(self, lines):
        """ check file status and find common root path """
        fs = []
        if len(lines) == 0:
            return None, fs
        common_path = lines[0]
        for line in lines:
            path = line.strip()
            if self._is_skip_pattern or self._check_input_file_path(path):
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
        try:
            lines = np.loadtxt(self.fp_input, dtype=str, comments=None, ndmin=1).tolist()
        except Exception:
            raise ValueError(f'ERROR: input file cannot be read!')
        common_path, fs = self._tidy_fs(lines)
        return common_path, fs

    def _run_callback(self, args):
        # custom callback function
        if self._callback_input_length == 0:
            self.callback()
        elif self._callback_input_length == 1:
            self.callback(args)
        else:
            self.callback(*args)

    def _callback_clean_paths(self, args):
        # clean file path during callback
        if not self._file_iterator_mode and not self._single_args_mode:
            in_path, out_path = args
            if not os.path.exists(out_path):
                self._empty_file_counter += 1
            if self._empty_file_counter / self._total_file_number < self._stop_each_file_cleaning_ratio:
                self._simplify_path(self.fp_output, out_path)

    def _process_mp_mt(self):
        def _callback_function(args):
            # update p_bar
            p_bar.update()
            self._run_callback(args)
            self._callback_clean_paths(args)

        self._update_paths_len()
        with tqdm(total=len(self.fp_paths), dynamic_ncols=True) as p_bar:
            if self.fp_cpu != 1:
                if self.fp_multi_what == 'mp':
                    executor_class = ProcessPoolExecutor
                elif self.fp_multi_what == 'mt':
                    executor_class = ThreadPoolExecutor
                else:
                    raise ValueError('ERROR: multi-what should be: multi-threading `mt`, or multi-processing `mp`!')
                with executor_class(max_workers=self._cpu_count(self.fp_cpu)) as executor:
                    for f in self.fp_paths:
                        future = executor.submit(self._do_multi_mapping, f)
                        future.add_done_callback(fn=lambda func: _callback_function(func.result()))
            else:
                for f in self.fp_paths:
                    result = self._do_multi_mapping(f)
                    _callback_function(result)

    def _process_imp_imt(self):
        def _callback_function(args):
            self._run_callback(args)
            self._callback_clean_paths(args)

        if self.fp_cpu != 1:
            if self.fp_multi_what == 'imp':
                executor_class = ProcessPoolExecutor
            elif self.fp_multi_what == 'imt':
                executor_class = ThreadPoolExecutor
            else:
                raise ValueError('ERROR: multi-what iterator mode should be:'
                                 'multi-threading `imt`, or multi-processing `imp`!')
            with executor_class(max_workers=self._cpu_count(self.fp_cpu)) as executor:
                futures = []
                for filename in self._find_fs_iterator():
                    # add counter if iterator mode
                    self._total_file_number += 1
                    future = executor.submit(self._do_multi_mapping, filename)
                    future.add_done_callback(fn=lambda func: _callback_function(func.result()))
                    futures.append(future)
                concurrent.futures.wait(futures)
        else:
            for f in self.fp_paths:
                result = self._do_multi_mapping(f)
                _callback_function(result)

    def _do_once(self):
        """
        process once if:
        --> input format == `in_format`
        --> output format == `out_format` (optional)
        """
        attributes = [self.fp_input]
        if not self._single_args_mode:
            if self.fp_output.endswith(self.fp_out_format):
                os.makedirs(os.path.dirname(self.fp_output), exist_ok=True)
                attributes.append(self.fp_output)
            else:
                raise AttributeError('ERROR: output format should match at single process!')
        self.do(*attributes)
        return attributes

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

    def before(self):
        """
        do something just before multiprocessing
        """
        pass
