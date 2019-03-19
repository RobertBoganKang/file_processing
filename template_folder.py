import argparse

# https://github.com/RobertBoganKang/FileProcessing
from file_processing import FolderProcessing


class Template(FolderProcessing):
    """
    xxx xxx xxx xxx
    """

    def __init__(self, ops):
        super().__init__(ops)
        self.xx = None
        # ...

    # in_folder --> out_folder; data flow
    def do_body(self, in_folder, out_folder):
        """
        overwrite the method
        """
        pass

    # target path operation
    # def do_body(self, target_folder):
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
    # ...
    args = parser.parse_args()

    # or use api
    # args = {
    #     'input': 'in',
    #     'output': 'out',
    #     'cpu_number': 0
    # }

    # do operation
    t = Template(args)
    t.do_multiple()
    # ...
