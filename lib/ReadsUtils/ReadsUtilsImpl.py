#BEGIN_HEADER
import time
import subprocess
import os
import re
import tempfile
import shutil
#END_HEADER


class ReadsUtils:
    '''
    Module Name:
    ReadsUtils

    Module Description:
    Utilities for handling reads files.
    '''

    ######## WARNING FOR GEVENT USERS #######
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    #########################################
    VERSION = "0.0.1"
    GIT_URL = "https://github.com/mrcreosote/ReadsUtils"
    GIT_COMMIT_HASH = "1fefc7be5acf19d9eff339948f58d73f06f8832b"
    
    #BEGIN_CLASS_HEADER

    FASTA_JAR = '/opt/lib/FastaValidator-1.0.jar'
    FASTQ_EXE = 'fastQValidator'

    FASTA_EXT = ['.fa', '.fas', '.fasta', '.fna']
    FASTQ_EXT = ['.fq', '.fastq', '.fnq']

    def log(self, message, prefix_newline=False):
        print(('\n' if prefix_newline else '') +
              str(time.time()) + ': ' + message)

    SEP_ILLUMINA = '/'
    SEP_CASAVA_1 = ':Y:'
    SEP_CASAVA_2 = ':N:'

    # TODO add tests & improve
    # TODO later - merge with the line counter / remover if possible
    def check_interleavedPE(self, filename):

        with open(filename, 'r') as infile:
            first_line = infile.readline().strip()
            hcount = 1
            lcount = 1

            if self.SEP_ILLUMINA in first_line:
                header1 = first_line.split(self.SEP_ILLUMINA)[0]
            elif (self.SEP_CASAVA_1 in first_line or
                  self.SEP_CASAVA_2 in first_line):
                header1 = re.split('[1,2]:[Y,N]:', first_line)[0]
            else:
                header1 = first_line

            for line in infile:
                lcount += 1
#                 if lcount % 4 == 0:
                if re.match(header1, line):  # compile this & anchor
                        hcount = hcount + 1

        return hcount == 2  # exactly 2 headers with same id = interleaved

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.scratch = config['scratch']
        #END_CONSTRUCTOR
        pass
    

    def validateFASTA(self, ctx, file_path):
        """
        Validate a FASTA file. The file extensions .fa, .fas, .fna. and .fasta
        are accepted.
        :param file_path: instance of String
        :returns: instance of type "boolean" (A boolean - 0 for false, 1 for
           true. @range (0, 1))
        """
        # ctx is the context object
        # return variables are: validated
        #BEGIN validateFASTA
        del ctx
        if not file_path or not os.path.isfile(file_path):
            raise ValueError('No such file: ' + str(file_path))
        if os.path.splitext(file_path)[1] not in self.FASTA_EXT:
            raise ValueError('File {} is not a FASTA file'.format(file_path))
        self.log('Validating FASTA file ' + file_path)
        # TODO per transform service notes, we need a better fasta validator
        # a good start would be not calling FVTester but writing our own
        # wrapper (Py4J?) that takes options for types etc.
        # see https://github.com/jwaldman/FastaValidator/blob/master/src/demo/FVTester.java @IgnorePep8
        # note the version in jars returns non-zero error codes:
        # https://github.com/srividya22/FastaValidator/commit/67e2d860f1869b9a76033e71fb2aaff910b7c2e3 @IgnorePep8
        retcode = subprocess.call(
            ['java', '-classpath', self.FASTA_JAR, 'FVTester', file_path])
        self.log('Validation return code: ' + str(retcode))
        validated = 1 if retcode == 0 else 0
        self.log('Validation ' + ('succeeded' if validated else 'failed'))
        #END validateFASTA

        # At some point might do deeper type checking...
        if not isinstance(validated, int):
            raise ValueError('Method validateFASTA return value ' +
                             'validated is not type int as required.')
        # return the results
        return [validated]

    def validateFASTQ(self, ctx, file_path):
        """
        Validate a FASTQ file. The file extensions .fq, .fnq, and .fastq
        are accepted. Note that prior to validation the file will be altered in
        place to remove blank lines if any exist.
        :param file_path: instance of String
        :returns: instance of type "boolean" (A boolean - 0 for false, 1 for
           true. @range (0, 1))
        """
        # ctx is the context object
        # return variables are: validated
        #BEGIN validateFASTQ
        del ctx
        if not file_path or not os.path.isfile(file_path):
            raise ValueError('No such file: ' + str(file_path))
        if os.path.splitext(file_path)[1] not in self.FASTQ_EXT:
            raise ValueError('File {} is not a FASTQ file'.format(file_path))
        self.log('Validating FASTA file ' + file_path)
        self.log('Checking line count')
        c = 0
        blank = False
        # open assumes ascii, which is ok for reads
        with open(file_path) as f:  # run & count until we hit a blank line
            for l in f:
                if not l.strip():
                    blank = True
                    break
                c += 1
        if blank:
            c = 0
            self.log('Removing blank lines')
            with open(file_path) as s, tempfile.NamedTemporaryFile(
                    mode='w', dir=self.scratch) as t:
                for l in s:
                    l = l.strip()
                    if l:
                        t.write(l + '\n')
                        c += 1
                s.close()
                t.flush()
                shutil.copy2(t.name, file_path)
        validated = 1
        if c % 4 != 0:
            err = ('Invalid FASTQ file, expected multiple of 4 lines, got ' +
                   str(c))
            self.log(err)
            validated = 0
        else:
            self.log(str(c) + ' lines in file')

        if validated:
            arguments = [self.FASTQ_EXE, '--file', file_path,
                         '--maxErrors', '10']
            if self.check_interleavedPE(file_path):
                arguments.append('--disableSeqIDCheck')
            retcode = subprocess.call(arguments)
            self.log('Validation return code: ' + str(retcode))
            validated = 1 if retcode == 0 else 0
            self.log('Validation ' + ('succeeded' if validated else 'failed'))
        #END validateFASTQ

        # At some point might do deeper type checking...
        if not isinstance(validated, int):
            raise ValueError('Method validateFASTQ return value ' +
                             'validated is not type int as required.')
        # return the results
        return [validated]

    def status(self, ctx):
        #BEGIN_STATUS
        del ctx
        returnVal = {'state': 'OK',
                     'message': '',
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
