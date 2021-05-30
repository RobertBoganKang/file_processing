import argparse

# https://github.com/RobertBoganKang/file_processing
from file_processing import FileProcessing


class Template(FileProcessing):
    """
    xxx xxx xxx xxx
    """

    def __init__(self, ops):
        super().__init__(ops)
        self.xx = None
        # ...

    # in_path --> out_path; data flow
    def do(self, in_path, out_path):
        """
        overwrite the method
        """
        pass

    # target path operation
    # def do(self, target_path):
    #    """
    #    overwrite the method
    #    """
    #    pass

    def xxx(self):
        # xxx
        pass

    # ...


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='xxx xxx xxx')
    fp_group = parser.add_argument_group('file processing arguments')
    fp_group.add_argument('--input', '-i', help='the input folder', default='in', type=str)
    fp_group.add_argument('--input_path_list', '-l', type=str, help='the file for paths', default=None)
    fp_group.add_argument('--in_format', '-if', type=str, help='the input format', default='xxx')
    fp_group.add_argument('--output', '-o', help='the output folder', default=None, type=str)
    fp_group.add_argument('--out_format', '-of', type=str, help='the output format', default=None)
    fp_group.add_argument('--cpu_number', '-j', type=int, help='cpu number of processing', default=0)
    fp_group.add_argument('--logger_level', '-log', type=str,
                          help='define the logger level, if `None`: no log file generated', default=None)

    xx_group = parser.add_argument_group('xxx xxx xxx')
    # ...

    args = parser.parse_args()

    # or use dict
    # args = {
    #     'input': 'in',
    #     'output': 'out',
    #     'cpu_number': 0,
    #     'in_format': 'xxx',
    #     'out_format': None
    # }

    # do operation
    Template(args)()
    # ...
