import argparse

# https://github.com/RobertBoganKang/FileProcessing
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
    def do_body(self, in_path, out_path):
        """
        overwrite the method
        """
        pass

    # target path operation
    # def do_body(self, target_path):
    #    """
    #    overwrite the method
    #    """
    #    pass

    def xxx(self):
        # xxx
        pass

    # ...


if __name__ == '__main__':
    # prepare argument
    parser = argparse.ArgumentParser(description='xxx xxx xxx')
    parser.add_argument('--input', '-i', help='xxx', default='in', type=str)
    parser.add_argument('--output', '-o', help='xxx', default=None, type=str)
    parser.add_argument('--cpu_number', '-j', type=int, help='cpu number of processing', default=0)
    parser.add_argument('--in_format', '-if', type=str, help='define the input format', default='xxx')
    parser.add_argument('--out_format', '-of', type=str, help='define the output format', default=None)
    # ...
    args = parser.parse_args()

    # or use api
    # args = {}
    # args['input'] = 'in'
    # args['output'] = 'out'
    # args['cpu_number'] = 0
    # args['in_format'] = 'xxx'
    # args['out_format'] = None

    # do operation
    t = Template(args)
    t.do_multiple()
    # ...
