import glob
import multiprocessing
import os


class FileProcessing(object):
    def __init__(self, ops):
        # output folder
        self.output = os.path.abspath(ops.output)
        # input folder
        self.input = os.path.abspath(ops.input)
        # input format
        self.in_format = ops.in_format
        # output format
        self.out_format = ops.out_format

    ##########################################
    # this section is default batch process  #
    # set above with self.input, self.output #
    ##########################################
    def do_multiple(self):
        # find all patterns
        fs = glob.glob(os.path.join(self.input, '**/*.' + self.in_format), recursive=True)
        pool = multiprocessing.Pool(multiprocessing.cpu_count())
        pool.map(self.do_multiple_helper, fs)

    def do_multiple_helper(self, in_path):
        # prepare output path
        truncated_path = os.path.split(in_path)[0][len(self.input) + 1:]
        out_folder = os.path.join(self.output, truncated_path)
        if not os.path.exists(out_folder):
            print('[{}] has been created successfully ~'.format(out_folder))
        os.makedirs(out_folder, exist_ok=True)
        # do operation
        self.do_single(in_path, out_folder)

    def do_single(self, in_path, out_folder):
        out_name = os.path.split(in_path)[1][:-len(self.in_format)]
        out_path = os.path.join(out_folder, out_name) + self.out_format
        # the 'do_body' function is main function for batch process
        self.do_body(in_path, out_path)

    #######
    # end #
    #######

    def do_body(self, in_path, out_path):
        """
        do function will be implemented
        """
        pass
