import argparse

from file_processing import FileProcessing


class Template(FileProcessing):
    """
    xxx xxx xxx xxx
    """

    def __init__(self, ops):
        super().__init__(ops)
        self.xx = None
        # ...

    def do_body(self, in_path, out_path):
        """
        overwrite the method
        """
        pass

    def xxx(self):
        # xxx
        pass

    # ...


if __name__ == '__main__':
    # prepare argument
    parser = argparse.ArgumentParser(description='xxx xxx xxx')
    parser.add_argument('--input', '-i', help='xxx', default='in', type=str)
    parser.add_argument('--output', '-o', help='xxx', default='out', type=str)
    parser.add_argument('--in_format', '-if', type=str, help='define the input format', default='xxx')
    parser.add_argument('--out_format', '-of', type=str, help='define the output format', default='yyy')
    parser.add_argument('--cpu_number', '-j', type=int, help='cpu number of processing', default=0)
    # ...
    args = parser.parse_args()

    # do operation
    t = Template(args)
    t.do_multiple()
    # ...
