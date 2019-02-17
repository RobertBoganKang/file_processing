import argparse

from file_processing import FileProcessing


class C(FileProcessing):
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
    parser.add_argument("--in_format", "-if", type=str, help="define the input format", default="xxx")
    parser.add_argument("--out_format", "-of", type=str, help="define the output format", default="yyy")
    # ...
    args = parser.parse_args()

    # do operation
    c = C(args)
    c.do_multiple()
    # ...
