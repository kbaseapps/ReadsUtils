#BEGIN_HEADER
import time
import subprocess
import os
import re
import tempfile
import shutil
from DataFileUtil.DataFileUtilClient import DataFileUtil
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
    GIT_COMMIT_HASH = "13d49cff1c422d001284ff9d59e429befd8d399b"
    
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

    # TODO later - merge with the 1st line counter if possible
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

            m = re.compile('^' + header1)
            for line in infile:
                if lcount % 4 == 0:
                    if m.match(line):
                        hcount = hcount + 1
                lcount += 1
        return hcount == 2  # exactly 2 headers with same id = interleaved

    def xor(self, a, b):
        return bool(a) != bool(b)

    def _proc_upload_reads_params(self, ctx, params):
        fwdid = params.get('fwd_id')
        if not fwdid:
            raise ValueError('At least one reads file must be provided')
        wsid = params.get('wsid')
        wsname = params.get('wsname')
        if not self.xor(wsid, wsname):
            raise ValueError(
                'Exactly one of the workspace ID or name must be provided')
        dfu = DataFileUtil(self.callback_url, token=ctx['token'])
        if wsname:
            wsid = dfu.ws_name_to_id(wsname)
        del wsname
        objid = params.get('objid')
        name = params.get('name')
        if not self.xor(objid, name):
            raise ValueError(
                'Exactly one of the object ID or name must be provided')
        revid = params.get('rev_id')
        interleaved = 1 if params.get('interleaved') else 0
        kbtype = 'KBaseFile.SingleEndLibrary'
        single_end = True
        if interleaved or revid:
            kbtype = 'KBaseFile.PairedEndLibrary'
            single_end = False
        if revid:
            interleaved = 0
        seqtype = params.get('sequencing_tech')
        if not seqtype:
            raise ValueError('The sequencing technology must be provided')

        o = {'sequencing_tech': seqtype,
             'single_genome': 1 if params.get('single_genome') else 0,
             'strain': params.get('strain'),
             'source': params.get('source'),
             'read_count': params.get('read_count'),
             'read_size': params.get('read_size'),
             'gc_content': params.get('gc_content')
             }
        # TODO tests
        if not single_end:
            o.update({'insert_size_mean': params.get('insert_size_mean'),
                      'insert_size_std_dev': params.get('insert_size_std_dev'),
                      'interleaved': interleaved,
                      'read_orientation_outward': 1 if params.get(
                            'read_orientation_outward') else 0
                      })
        return o, wsid, name, objid, kbtype, single_end, fwdid, revid

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.scratch = config['scratch']
        self.callback_url = os.environ['SDK_CALLBACK_URL']
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

    def upload_reads(self, ctx, params):
        """
        Loads a set of reads to KBase data stores.
        :param params: instance of type "UploadReadsParams" (Input to the
           upload_reads function. Required parameters: fwd_id - the id of the
           shock node containing the reads data file: either single end
           reads, forward/left reads, or interleaved reads. sequencing_tech -
           the sequencing technology used to produce the reads. One of: wsid
           - the id of the workspace where the reads will be saved
           (preferred). wsname - the name of the workspace where the reads
           will be saved. One of: objid - the id of the workspace object to
           save over name - the name to which the workspace object will be
           saved Optional parameters: rev_id - the shock node id containing
           the reverse/right reads for paired end, non-interleaved reads.
           interleaved - specify that the fwd reads file is an interleaved
           paired end reads file as opposed to a single end reads file.
           Default true, ignored if rev is specified. single_genome - whether
           the reads are from a single genome or a metagenome. Default is
           single genome. read_orientation_outward - whether the read
           orientation is outward from the set of primers. Default is false
           and is ignored for single end reads. strain - information about
           the organism strain that was sequenced. source - information about
           the organism source. insert_size_mean - the mean size of the
           genetic fragments. Ignored for single end reads.
           insert_size_std_dev - the standard deviation of the size of the
           genetic fragments. Ignored for single end reads. read_count - the
           number of reads in the this dataset. read_size - the total size of
           the reads, in bases. gc_content - the GC content of the reads.) ->
           structure: parameter "fwd_id" of String, parameter "wsid" of Long,
           parameter "wsname" of String, parameter "objid" of Long, parameter
           "name" of String, parameter "rev_id" of String, parameter
           "interleaved" of type "boolean" (A boolean - 0 for false, 1 for
           true. @range (0, 1)), parameter "single_genome" of type "boolean"
           (A boolean - 0 for false, 1 for true. @range (0, 1)), parameter
           "read_orientation_outward" of type "boolean" (A boolean - 0 for
           false, 1 for true. @range (0, 1)), parameter "sequencing_tech" of
           String, parameter "strain" of type "StrainInfo" (Information about
           a strain. genetic_code - the genetic code of the strain. See
           http://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi?mode=c
           genus - the genus of the strain species - the species of the
           strain strain - the identifier for the strain source - information
           about the source of the strain organelle - the organelle of
           interest for the related data (e.g. mitochondria) ncbi_taxid - the
           NCBI taxonomy ID of the strain location - the location from which
           the strain was collected @optional genetic_code source ncbi_taxid
           organelle location) -> structure: parameter "genetic_code" of
           Long, parameter "genus" of String, parameter "species" of String,
           parameter "strain" of String, parameter "organelle" of String,
           parameter "source" of type "SourceInfo" (Information about the
           source of a piece of data. source - the name of the source (e.g.
           NCBI, JGI, Swiss-Prot) source_id - the ID of the data at the
           source project_id - the ID of a project encompassing the data at
           the source @optional source source_id project_id) -> structure:
           parameter "source" of String, parameter "source_id" of type
           "source_id" (An ID used for a piece of data at its source. @id
           external), parameter "project_id" of type "project_id" (An ID used
           for a project encompassing a piece of data at its source. @id
           external), parameter "ncbi_taxid" of Long, parameter "location" of
           type "Location" (Information about a location. lat - latitude of
           the site, recorded as a decimal number. North latitudes are
           positive values and south latitudes are negative numbers. lon -
           longitude of the site, recorded as a decimal number. West
           longitudes are positive values and east longitudes are negative
           numbers. elevation - elevation of the site, expressed in meters
           above sea level. Negative values are allowed. date - date of an
           event at this location (for example, sample collection), expressed
           in the format YYYY-MM-DDThh:mm:ss.SSSZ description - a free text
           description of the location and, if applicable, the associated
           event. @optional date description) -> structure: parameter "lat"
           of Double, parameter "lon" of Double, parameter "elevation" of
           Double, parameter "date" of String, parameter "description" of
           String, parameter "source" of type "SourceInfo" (Information about
           the source of a piece of data. source - the name of the source
           (e.g. NCBI, JGI, Swiss-Prot) source_id - the ID of the data at the
           source project_id - the ID of a project encompassing the data at
           the source @optional source source_id project_id) -> structure:
           parameter "source" of String, parameter "source_id" of type
           "source_id" (An ID used for a piece of data at its source. @id
           external), parameter "project_id" of type "project_id" (An ID used
           for a project encompassing a piece of data at its source. @id
           external), parameter "insert_size_mean" of Double, parameter
           "insert_size_std_dev" of Double, parameter "read_count" of Long,
           parameter "read_size" of Long, parameter "gc_content" of Double
        :returns: instance of type "UploadReadsOutput" (The output of the
           upload_reads function. obj_ref - a reference to the new Workspace
           object in the form X/Y/Z, where X is the workspace ID, Y is the
           object ID, and Z is the version.) -> structure: parameter
           "obj_ref" of String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN upload_reads
        o, wsid, name, objid, kbtype, single_end, fwdid, revid = (
            self._proc_upload_reads_params(ctx, params))
        fileinput = [{'shock_id': fwdid,
                      'file_path': self.scratch + '/fwd'}]
        if revid:
            fileinput.add({'shock_id': revid,
                           'file_path': self.scratch + '/rev'})
        for f in fileinput:
            f.update({'make_handle': 1, 'unpack': 'uncompress'})
        dfu = DataFileUtil(self.callback_url, token=ctx['token'])
        files = dfu.shock_to_file_mass(fileinput)
        for f, i in zip(files, fileinput):
            if not self.validateFASTQ(ctx, f['file_path']):
                raise ValueError('Invalid fasta file {} from Shock node {}'
                                 .format(f['file_path'], i['shock_id']))
        fwdr = dfu.own_shock_node({'shock_id': fwdid, 'make_handle': 1})
        revr = None
        if revid:
            revr = dfu.own_shock_node({'shock_id': fwdid, 'make_handle': 1})

        # TODO tests
        fwdfile = {'file': fwdr['handle'],
                   'encoding': 'ascii',
                   'size': fwdr['size'],
                   'type': 'fq'
                   }
        if single_end:
            o['lib'] = fwdfile
        else:
            o['lib1'] = fwdfile,
            if revr:
                o['lib2'] = {'file': revr['handle'],
                             'encoding': 'ascii',
                             'size': revr['size'],
                             'type': 'fq'
                             }

        so = {'type': kbtype,
              'data': o
              }
        if name:
            so['name'] = name
        else:
            so['objid'] = objid
        oi = dfu.save_objects({'id': wsid, 'objects': [so]})[0]

        returnVal = {'obj_ref': str(oi[6]) + '/' + str(oi[0]) + '/' +
                     str(oi[4])}
        #END upload_reads

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method upload_reads return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

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
