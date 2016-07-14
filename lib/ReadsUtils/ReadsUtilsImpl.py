#BEGIN_HEADER
import time
import subprocess
import os
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
    GIT_COMMIT_HASH = "65beb3e2261f8eb766ccf7c703a69c2eb1df882b"
    
    #BEGIN_CLASS_HEADER

    FASTA_JAR = '/opt/lib/FastaValidator-1.0.jar'
    FASTQ_EXE = 'fastQValidator'

    FASTA_EXT = ['.fa', '.fas', '.fasta', '.fna']
    FASTQ_EXT = ['.fq', '.fastq', '.fnq']

    def log(self, message, prefix_newline=False):
        print(('\n' if prefix_newline else '') +
              str(time.time()) + ': ' + message)

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
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
        # note the version in jars returns non-zero error codes and so must
        # have been altered from the source above
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
        are accepted.
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
        validated = 0
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
