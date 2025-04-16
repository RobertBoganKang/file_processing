import argparse
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
try:
    # https://github.com/RobertBoganKang/file_processing
    from file_processing import FileProcessing
except Exception:
    raise ImportError('ERROR: cannot import!')


class Template(FileProcessing):
    """
    xxx xxx xxx xxx
    """

    def __init__(self, ops):
        super().__init__(ops)

    # in_path --> out_path; data flow
    def do(self, in_path, out_path):
        """
        implement this method for main operation
        """
        pass

    # target path operation
    # def do(self, target_path):
    #    """
    #    implement this method
    #    """
    #    pass

    def callback(self, in_path, out_path):
        """
        (optional) implement this method for callback operation
        input:
            * None;
            * 1 argument: combined input;
            * arguments same as function `do`;
        """
        pass

    def before(self):
        """
        (optional) do something just before multiprocessing
        """
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='xxx xxx xxx')
    fp_group = parser.add_argument_group('file processing arguments')
    fp_group.add_argument('--input', '-i', type=str, help='the input folder/file, or a text file for paths',
                          required=True)
    fp_group.add_argument('--in_format', '-if', type=str, help='the input format', default='xxx')
    fp_group.add_argument('--output', '-o', type=str, help='the output folder/file')
    fp_group.add_argument('--out_format', '-of', type=str, help='the output format', default='yyy')
    fp_group.add_argument('--cpu_number', '-j', type=int, help='cpu number of processing', default=0)
    fp_group.add_argument('--multi_what', '-x', type=str,
                          help='4 mode supported:'
                               'a. multi-threading: `mt`,'
                               'b. multi-processing: `mp` (default),'
                               'c. iterator multi-threading: `imt`,'
                               'd. iterator multi-processing: `imp`',
                          default=None)
    fp_group.add_argument('--logger_level', '-log', type=str,
                          help='define the logger level, if `None`: no log file generated', default='info')

    xx_group = parser.add_argument_group('xxx xxx arguments')

    args = parser.parse_args()

    # or use dict
    # args = {
    #     'input': 'in',
    #     'in_format': 'xxx',
    #     'output': 'out',
    #     'out_format': 'yyy',
    #     'cpu_number': 0,
    #     'multi_what': 'mp'
    # }

    # do operation
    Template(args)()
