#BEGIN_HEADER
import time
import subprocess
import os
import tempfile
import shutil
from DataFileUtil.DataFileUtilClient import DataFileUtil
from numbers import Number
import six


### copied from old kb_read_library_to_file
import os
import re
import json
import requests
import time
from pprint import pformat, pprint
from biokbase.workspace.client import Workspace as workspaceService  # @UnresolvedImport @IgnorePep8
from biokbase.workspace.client import ServerError as WorkspaceException  # @UnresolvedImport @IgnorePep8
import errno
import shutil
import gzip
import uuid


class ShockError(Exception):
    pass


class InvalidFileError(Exception):
    pass

### end copied from old kb_read_library_to_file


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
    GIT_URL = "git@github.com:msneddon/ReadsUtils"
    GIT_COMMIT_HASH = "6f7468b6bc2efdda27d18466f406386b3c6652e2"
    
    #BEGIN_CLASS_HEADER

    FASTA_JAR = '/opt/lib/FastaValidator-1.0.jar'
    FASTQ_EXE = 'fastQValidator'

    FASTA_EXT = ['.fa', '.fas', '.fasta', '.fna']
    FASTQ_EXT = ['.fq', '.fastq', '.fnq']

    def log(self, message, prefix_newline=False):
        print(('\n' if prefix_newline else '') +
              str(time.time()) + ': ' + message)

    def xor(self, a, b):
        return bool(a) != bool(b)

    def _add_field(self, obj, params, field):
        f = params.get(field)
        if f:
            obj[field] = f

    def _check_pos(self, num, name):
        if num is not None:
            if not isinstance(num, Number):
                raise ValueError(name + ' must be a number')
            if num <= 0:
                raise ValueError(name + ' must be > 0')

    def _proc_upload_reads_params(self, ctx, params):
        fwdid = params.get('fwd_id')
        if not fwdid:
            raise ValueError('No reads file provided')
        wsid = params.get('wsid')
        wsname = params.get('wsname')
        if not self.xor(wsid, wsname):
            raise ValueError(
                'Exactly one of the workspace ID or name must be provided')
        dfu = DataFileUtil(self.callback_url, token=ctx['token'])
        if wsname:
            self.log('Translating workspace name to id')
            if not isinstance(wsname, six.string_types):
                raise ValueError('wsname must be a string')
            wsid = dfu.ws_name_to_id(wsname)
            self.log('translation done')
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

        sg = 1
        if 'single_genome' in params and not params['single_genome']:
            sg = 0
        o = {'sequencing_tech': seqtype,
             'single_genome': sg,
             # 'read_count': params.get('read_count'),
             # 'read_size': params.get('read_size'),
             # 'gc_content': params.get('gc_content')
             }
        self._add_field(o, params, 'strain')
        self._add_field(o, params, 'source')
        ism = params.get('insert_size_mean')
        self._check_pos(ism, 'insert_size_mean')
        issd = params.get('insert_size_std_dev')
        self._check_pos(issd, 'insert_size_std_dev')
        if not single_end:
            o.update({'insert_size_mean': ism,
                      'insert_size_std_dev': issd,
                      'interleaved': interleaved,
                      'read_orientation_outward': 1 if params.get(
                            'read_orientation_outward') else 0
                      })
        return o, wsid, name, objid, kbtype, single_end, fwdid, revid

    def validateFASTA(self, ctx, params):
        """
        Validate a FASTA file. The file extensions .fa, .fas, .fna. and .fasta
        are accepted.
        :param file_path: instance of String
        :returns: instance of type "boolean" (A boolean - 0 for false, 1 for
           true. @range (0, 1))
        """
        # ctx is the context object
        # return variables are: validated
        # OLD BEGIN validateFASTA
        del ctx
        file_path = params.get('file_path')
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
        # Better yet, move this to a Java SDK module, don't make a system
        # call and expose useful options.
        retcode = subprocess.call(
            ['java', '-classpath', self.FASTA_JAR, 'FVTester', file_path])
        self.log('Validation return code: ' + str(retcode))
        validated = 1 if retcode == 0 else 0
        self.log('Validation ' + ('succeeded' if validated else 'failed'))
        out = {'valid': validated}
        # OLD END validateFASTA

        # At some point might do deeper type checking...
        if not isinstance(out, dict):
            raise ValueError('Method validateFASTA return value ' +
                             'out is not type dict as required.')
        # return the results
        return [out]


    ############# begin copied from kb_read_library_to_fileImpl
    #############   note: duplicate functions were removed
    #############
    #############

    # Class variables and functions can be defined in this block
    SINGLE_END_TYPE = 'SingleEndLibrary'
    PAIRED_END_TYPE = 'PairedEndLibrary'
    # one of these should be deprecated
    KBASE_FILE = 'KBaseFile'
    KBASE_ASSEMBLY = 'KBaseAssembly'
    MODULE_NAMES = [KBASE_FILE, KBASE_ASSEMBLY]
    TYPE_NAMES = [SINGLE_END_TYPE, PAIRED_END_TYPE]

    PARAM_IN_WS = 'workspace_name'
    PARAM_IN_LIB = 'read_libraries'
    PARAM_IN_GZIP = 'gzip'
    PARAM_IN_INTERLEAVED = 'interleaved'

    GZIP = '.gz'

    TRUE = 'true'
    FALSE = 'false'

    URL_WS = 'workspace-url'
    URL_SHOCK = 'shock-url'

    SUPPORTED_FILES = ['.fq',
                       '.fastq',
                       # '.bam',
                       # '.fa',
                       # '.fasta',
                       '.fq' + GZIP,
                       '.fastq' + GZIP,
                       # '.bam.gz',
                       # '.fa.gz',
                       # '.fasta.gz'
                       ]

    SHOCK_TEMP = 'shock_tmp'

    #def log(self, message, prefix_newline=False):
    #    print(('\n' if prefix_newline else '') +
    #          str(time.time()) + ': ' + message)

    def file_extension_ok(self, filename):
        for okext in self.SUPPORTED_FILES:
            if filename.lower().endswith(okext):
                if okext.endswith(self.GZIP):
                    return okext, True
                return okext, False
        return None, None

    def check_shock_response(self, response):
        if not response.ok:
            try:
                err = json.loads(response.content)['error'][0]
            except:
                # this means shock is down or not responding.
                self.log("Couldn't parse response error content from Shock: " +
                         response.content)
                response.raise_for_status()
            raise ShockError(str(err))

    def shock_download(self, token, handle, file_type=None):
        # Could keep a record of files downloaded to prevent duplicate
        # downloads if 2 ws objects point to the same shock node, but that
        # seems rare enough that it's not worth the extra code complexity and
        # maintenance burden
        self.log('Downloading from shock via handle:\n' + pformat(handle))

        headers = {'Authorization': 'OAuth ' + token}
        node_url = handle['url'] + '/node/' + handle['id']
        r = requests.get(node_url, headers=headers)
        self.check_shock_response(r)

        node_fn = r.json()['data']['file']['name']

        handle_fn = handle['file_name'] if 'file_name' in handle else None

        if file_type:
            file_type = ('' if file_type.startswith('.') else '.') + file_type
        fileok = None
        for txt, fn in zip(['file type', 'handle filename', 'shock filename'],
                           [file_type, handle_fn, node_fn]):
            if fn:
                fileok, gzipped = self.file_extension_ok(fn)
                if fileok:
                    self.log(('Found acceptable file extension in {}: {}. ' +
                             'File {} gzipped.').format(
                        txt, fn, 'is' if gzipped else 'is not'))
                break
            else:
                self.log('File extension cannot be determined from {}: {}'
                         .format(txt, fn))
        if not fileok:
            raise InvalidFileError(
                ('A valid file extension could not be determined for the ' +
                 'reads file. In order of precedence:\n' +
                 'File type is: {}\n' +
                 'Handle file name is: {}\n' +
                 'Shock file name is: {}\n' +
                 'Acceptable extensions: {}').format(
                    file_type, handle_fn, node_fn,
                    ' '.join(self.SUPPORTED_FILES)))

        file_path = os.path.join(self.shock_temp, handle['id'] +
                                 (self.GZIP if gzipped else ''))
        with open(file_path, 'w') as fhandle:
            self.log('downloading reads file: ' + str(file_path))
            r = requests.get(node_url + '?download', stream=True,
                             headers=headers)
            self.check_shock_response(r)
            for chunk in r.iter_content(1024):
                if not chunk:
                    break
                fhandle.write(chunk)
        return file_path, gzipped

    def make_ref(self, object_info):
        return str(object_info[6]) + '/' + str(object_info[0]) + \
            '/' + str(object_info[4])

    def check_reads(self, reads):
        info = reads['info']
        obj_ref = self.make_ref(info)
        obj_name = info[1]

        # Might need to do version checking here.
        module_name, type_name = info[2].split('-')[0].split('.')
        if (module_name not in self.MODULE_NAMES or
                type_name not in self.TYPE_NAMES):
            types = []
            for mod in self.MODULE_NAMES:
                for type_ in self.TYPE_NAMES:
                    types.append(mod + '.' + type_)
            raise ValueError(('Invalid type for object {} ({}). Supported ' +
                              'types: {}').format(obj_ref, obj_name,
                                                  ' '.join(types)))
        return (type_name == self.SINGLE_END_TYPE,
                module_name == self.KBASE_FILE)

    def copy_field(self, source, field, target):
        target[field] = source.get(field)

    # this assumes that the FASTQ file is properly formatted, which it should
    # be if it's in KBase. Credit:
    # https://www.biostars.org/p/19446/#117160
    def deinterleave(self, filepath, fwdpath, revpath):
        self.log('Deinterleaving file {} to files {} and {}'.format(
            filepath, fwdpath, revpath))
        with open(filepath, 'r') as s:
            with open(fwdpath, 'w') as f, open(revpath, 'w') as r:
                for i, line in enumerate(s):
                    if i % 8 < 4:
                        f.write(line)
                    else:
                        r.write(line)

    # this assumes that the FASTQ files are properly formatted and matched,
    # which they should be if they're in KBase. Credit:
    # https://sourceforge.net/p/denovoassembler/ray-testsuite/ci/master/tree/scripts/interleave-fastq.py
    def interleave(self, fwdpath, revpath, targetpath):
        self.log('Interleaving files {} and {} to {}'.format(
            fwdpath, revpath, targetpath))
        with open(targetpath, 'w') as t:
            with open(fwdpath, 'r') as f, open(revpath, 'r') as r:
                while True:
                    line = f.readline()
                    # since FASTQ cannot contain blank lines
                    if not line or not line.strip():
                        break
                    t.write(line.strip() + '\n')

                    for _ in xrange(3):
                        t.write(f.readline().strip() + '\n')

                    for _ in xrange(4):
                        t.write(r.readline().strip() + '\n')

    def set_up_reads_return(self, single, kbasefile, reads):
        data = reads['data']
        info = reads['info']

        ret = {}
        ret['ref'] = self.make_ref(info)

        sg = 'single_genome'
        if kbasefile:
            if sg not in data or data[sg]:
                ret[sg] = self.TRUE
            else:
                ret[sg] = self.FALSE
        else:
            ret[sg] = None

        roo = 'read_orientation_outward'
        if single:
            ret[roo] = None
        elif roo in data:
            ret[roo] = self.TRUE if data[roo] else self.FALSE
        else:
            ret[roo] = self.FALSE if kbasefile else None

        # these fields are only possible in KBaseFile/Assy paired end, but the
        # logic is still fine for single end, will just force a null
        self.copy_field(data, 'insert_size_mean', ret)
        self.copy_field(data, 'insert_size_std_dev', ret)
        # these fields are in KBaseFile single end and paired end only
        self.copy_field(data, 'source', ret)
        self.copy_field(data, 'strain', ret)
        self.copy_field(data, 'sequencing_tech', ret)
        self.copy_field(data, 'read_count', ret)
        self.copy_field(data, 'read_size', ret)
        self.copy_field(data, 'gc_content', ret)

        return ret

    def bool_outgoing(self, boolean):
        return self.TRUE if boolean else self.FALSE

    def get_file_prefix(self):
        return os.path.join(self.scratch, str(uuid.uuid4()))

    def get_shock_data_and_handle_errors(
            self, source_obj_ref, source_obj_name, token, handle, file_type):
        try:
            return self.shock_download(token, handle, file_type)
        except (ShockError, InvalidFileError) as e:
            msg = ('Error downloading reads for object {} ({}) from ' +
                   'Shock node {}: ').format(
                   source_obj_ref, source_obj_name, handle['id'])
            e.args = (msg + e.args[0],) + e.args[1:]
            # py 3 exceptions have no message field
            if hasattr(e, 'message'):  # changing args doesn't change message
                e.message = msg + e.message
            raise

    # there's got to be better way to do this than these processing methods.
    # make some input classes for starters to fix these gross method sigs

    def process_interleaved(self, source_obj_ref, source_obj_name, token,
                            handle, gzip, interleave, file_type=None):

        shockfile, isgz = self.get_shock_data_and_handle_errors(
            source_obj_ref, source_obj_name, token, handle, file_type)

        ret = {}
        if interleave is not False:  # e.g. True or None
            ret['inter'], ret['inter_gz'] = self.handle_gzip(
                shockfile, gzip, isgz, self.get_file_prefix() + '.inter.fastq')
        else:
            if isgz:
                # we expect the job runner to clean up for us
                shockfile = self.gunzip(shockfile)
            fwdpath = os.path.join(self.scratch, self.get_file_prefix() +
                                   '.fwd.fastq')
            revpath = os.path.join(self.scratch, self.get_file_prefix() +
                                   '.rev.fastq')
            self.deinterleave(shockfile, fwdpath, revpath)
            if gzip:
                fwdpath = self.gzip(fwdpath)
                revpath = self.gzip(revpath)
            gzip = self.bool_outgoing(gzip)
            ret['fwd'] = fwdpath
            ret['fwd_gz'] = gzip
            ret['rev'] = revpath
            ret['rev_gz'] = gzip
        return ret

    def process_paired(self, source_obj_ref, source_obj_name, token,
                       fwdhandle, revhandle, gzip, interleave,
                       fwd_file_type=None, rev_file_type=None):

        fwdshock, fwdisgz = self.get_shock_data_and_handle_errors(
            source_obj_ref, source_obj_name, token, fwdhandle, fwd_file_type)
        revshock, revisgz = self.get_shock_data_and_handle_errors(
            source_obj_ref, source_obj_name, token, revhandle, rev_file_type)

        ret = {}
        if interleave:
            # we expect the job runner to clean up for us
            if fwdisgz:
                fwdshock = self.gunzip(fwdshock)
            if revisgz:
                revshock = self.gunzip(revshock)
            intpath = os.path.join(self.scratch, self.get_file_prefix() +
                                   '.inter.fastq')
            self.interleave(fwdshock, revshock, intpath)
            if gzip:
                intpath = self.gzip(intpath)
            ret['inter'] = intpath
            ret['inter_gz'] = self.bool_outgoing(gzip)
        else:
            ret['fwd'], ret['fwd_gz'] = self.handle_gzip(
                fwdshock, gzip, fwdisgz, self.get_file_prefix() + '.fwd.fastq')

            ret['rev'], ret['rev_gz'] = self.handle_gzip(
                revshock, gzip, revisgz, self.get_file_prefix() + '.rev.fastq')
        return ret

    def process_single_end(self, source_obj_ref, source_obj_name, token,
                           handle, gzip, file_type=None):

        shockfile, isgz = self.get_shock_data_and_handle_errors(
            source_obj_ref, source_obj_name, token, handle, file_type)
        f, iszip = self.handle_gzip(shockfile, gzip, isgz,
                                    self.get_file_prefix() + '.sing.fastq')
        return {'sing': f, 'sing_gz': iszip}

    # there's almost certainly a better way to do this
    def handle_gzip(self, oldfile, shouldzip, iszip, prefix):
        zipped = False
        if shouldzip:
            prefix += self.GZIP
            zipped = True
            if iszip:
                self.mv(oldfile, os.path.join(self.scratch, prefix))
            else:
                self.gzip(oldfile, os.path.join(self.scratch, prefix))
        elif shouldzip is None:
            if iszip:
                prefix += self.GZIP
                zipped = True
            self.mv(oldfile, os.path.join(self.scratch, prefix))
        else:
            if iszip:
                self.gunzip(oldfile, os.path.join(self.scratch, prefix))
            else:
                self.mv(oldfile, os.path.join(self.scratch, prefix))
        return prefix, self.bool_outgoing(zipped)

    def mv(self, oldfile, newfile):
        self.log('Moving {} to {}'.format(oldfile, newfile))
        shutil.move(oldfile, newfile)

    def gzip(self, oldfile, newfile=None):
        if oldfile.lower().endswith(self.GZIP):
            raise ValueError('File {} is already gzipped'.format(oldfile))
        if not newfile:
            newfile = oldfile + self.GZIP
        self.log('gzipping {} to {}'.format(oldfile, newfile))
        with open(oldfile, 'rb') as s, gzip.open(newfile, 'wb') as t:
            shutil.copyfileobj(s, t)
        return newfile

    def gunzip(self, oldfile, newfile=None):
        if not oldfile.lower().endswith(self.GZIP):
            raise ValueError('File {} is not gzipped'.format(oldfile))
        if not newfile:
            newfile = oldfile[: -len(self.GZIP)]
        self.log('gunzipping {} to {}'.format(oldfile, newfile))
        with gzip.open(oldfile, 'rb') as s, open(newfile, 'wb') as t:
            shutil.copyfileobj(s, t)
        return newfile

    def process_reads(self, reads, gzip, interleave, token):
        data = reads['data']
        info = reads['info']
        # Object Info Contents
        # 0 - obj_id objid
        # 1 - obj_name name
        # 2 - type_string type
        # 3 - timestamp save_date
        # 4 - int version
        # 5 - username saved_by
        # 6 - ws_id wsid
        # 7 - ws_name workspace
        # 8 - string chsum
        # 9 - int size
        # 10 - usermeta meta

        single, kbasefile = self.check_reads(reads)
        ret = self.set_up_reads_return(single, kbasefile, reads)
        obj_name = info[1]
        ref = ret['ref']
        self.log('Type: ' + info[2])

        # lib1 = KBaseFile, handle_1 = KBaseAssembly
        if kbasefile:
            if single:
                reads = data['lib']['file']
                type_ = data['lib']['type']
                ret['files'] = self.process_single_end(
                    ref, obj_name, token, reads, gzip, type_)
            else:
                fwd_reads = data['lib1']['file']
                fwd_type = data['lib1']['type']
                if 'lib2' in data:  # not interleaved
                    rev_reads = data['lib2']['file']
                    rev_type = data['lib2']['type']
                    ret['files'] = self.process_paired(
                        ref, obj_name, token, fwd_reads, rev_reads, gzip,
                        interleave, fwd_type, rev_type)
                else:
                    ret['files'] = self.process_interleaved(
                        ref, obj_name, token, fwd_reads, gzip, interleave,
                        fwd_type)
        else:  # KBaseAssembly
            if single:
                ret['files'] = self.process_single_end(
                    ref, obj_name, token, data['handle'], gzip)
            else:
                if 'handle_2' in data:  # not interleaved
                    ret['files'] = self.process_paired(
                        ref, obj_name, token, data['handle_1'],
                        data['handle_2'], gzip, interleave)
                else:
                    ret['files'] = self.process_interleaved(
                        ref, obj_name, token, data['handle_1'], gzip,
                        interleave)

        return ret

    def process_ternary(self, params, boolname):
        if boolname not in params or params[boolname] is None:
            params[boolname] = None
        elif params[boolname] == 'true':
            params[boolname] = True
        elif params[boolname] == 'false':
            params[boolname] = False
        else:
            raise ValueError(('Illegal value for ternary parameter {}: {}. ' +
                              'Allowed values are "true", "false", and null.')
                             .format(boolname, params[boolname]))

    def process_params(self, params):
        if self.PARAM_IN_LIB not in params:
            raise ValueError(self.PARAM_IN_LIB + ' parameter is required')
        reads = params[self.PARAM_IN_LIB]
        if type(reads) != list:
            raise ValueError(self.PARAM_IN_LIB + ' must be a list')
        if not reads:
            raise ValueError('At least one reads library must be provided')
        reads = list(set(reads))
        for read_name in reads:
            if not read_name:
                raise ValueError('Invalid workspace object name ' + read_name)
        params[self.PARAM_IN_LIB] = reads

        self.process_ternary(params, self.PARAM_IN_GZIP)
        self.process_ternary(params, self.PARAM_IN_INTERLEAVED)

    def mkdir_p(self, path):
        try:
            os.makedirs(path)
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise
    ############# end copied from kb_read_library_to_fileImpl
    #############
    #############
    #############

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.scratch = config['scratch']
        self.callback_url = os.environ['SDK_CALLBACK_URL']

        ## added from kb_read_library_to_file_impl
        self.workspaceURL = config[self.URL_WS]
        self.shockURL = config[self.URL_SHOCK]
        self.scratch = os.path.abspath(config['scratch'])
        self.mkdir_p(self.scratch)
        self.shock_temp = os.path.join(self.scratch, self.SHOCK_TEMP)
        self.mkdir_p(self.shock_temp)
        ## end from kb_read_library_to_file_impl

        #END_CONSTRUCTOR
        pass
    

    def validateFASTQ(self, ctx, params):
        """
        Validate a FASTQ file. The file extensions .fq, .fnq, and .fastq
        are accepted. Note that prior to validation the file will be altered in
        place to remove blank lines if any exist.
        :param params: instance of list of type "ValidateFASTQParams" (Input
           to the validateFASTQ function. Required parameters: file_path -
           the path to the file to validate. Optional parameters: interleaved
           - whether the file is interleaved or not. Setting this to true
           disables sequence ID checks.) -> structure: parameter "file_path"
           of String, parameter "interleaved" of type "boolean" (A boolean -
           0 for false, 1 for true. @range (0, 1))
        :returns: instance of list of type "ValidateFASTQOutput" (The output
           of the validateFASTQ function. validated - whether the file
           validated successfully or not.) -> structure: parameter
           "validated" of type "boolean" (A boolean - 0 for false, 1 for
           true. @range (0, 1))
        """
        # ctx is the context object
        # return variables are: out
        #BEGIN validateFASTQ
        del ctx
        # TODO try and parse the validator output and return errors
        out = []
        for p in params:
            file_path = p.get('file_path')
            if not file_path or not os.path.isfile(file_path):
                raise ValueError('No such file: ' + str(file_path))
            if os.path.splitext(file_path)[1] not in self.FASTQ_EXT:
                raise ValueError('File {} is not a FASTQ file'
                                 .format(file_path))
            self.log('Validating FASTQ file ' + file_path)
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
                err = ('Invalid FASTQ file, expected multiple of 4 lines, ' +
                       'got ' + str(c))
                self.log(err)
                validated = 0
            else:
                self.log(str(c) + ' lines in file')

            if validated:
                arguments = [self.FASTQ_EXE, '--file', file_path,
                             '--maxErrors', '10']
                if p.get('interleaved'):
                    arguments.append('--disableSeqIDCheck')
                retcode = subprocess.call(arguments)
                self.log('Validation return code: ' + str(retcode))
                validated = 1 if retcode == 0 else 0
                self.log('Validation ' +
                         ('succeeded' if validated else 'failed'))
            out.append({'validated': validated})
        #END validateFASTQ

        # At some point might do deeper type checking...
        if not isinstance(out, list):
            raise ValueError('Method validateFASTQ return value ' +
                             'out is not type list as required.')
        # return the results
        return [out]

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
           single_genome - whether the reads are from a single genome or a
           metagenome. Default is single genome. strain - information about
           the organism strain that was sequenced. source - information about
           the organism source. interleaved - specify that the fwd reads file
           is an interleaved paired end reads file as opposed to a single end
           reads file. Default true, ignored if rev_id is specified.
           read_orientation_outward - whether the read orientation is outward
           from the set of primers. Default is false and is ignored for
           single end reads. insert_size_mean - the mean size of the genetic
           fragments. Ignored for single end reads. insert_size_std_dev - the
           standard deviation of the size of the genetic fragments. Ignored
           for single end reads.) -> structure: parameter "fwd_id" of String,
           parameter "wsid" of Long, parameter "wsname" of String, parameter
           "objid" of Long, parameter "name" of String, parameter "rev_id" of
           String, parameter "sequencing_tech" of String, parameter
           "single_genome" of type "boolean" (A boolean - 0 for false, 1 for
           true. @range (0, 1)), parameter "strain" of type "StrainInfo"
           (Information about a strain. genetic_code - the genetic code of
           the strain. See
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
           external), parameter "interleaved" of type "boolean" (A boolean -
           0 for false, 1 for true. @range (0, 1)), parameter
           "read_orientation_outward" of type "boolean" (A boolean - 0 for
           false, 1 for true. @range (0, 1)), parameter "insert_size_mean" of
           Double, parameter "insert_size_std_dev" of Double
        :returns: instance of type "UploadReadsOutput" (The output of the
           upload_reads function. obj_ref - a reference to the new Workspace
           object in the form X/Y/Z, where X is the workspace ID, Y is the
           object ID, and Z is the version.) -> structure: parameter
           "obj_ref" of String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN upload_reads
        self.log('Starting upload reads, parsing args')
        o, wsid, name, objid, kbtype, single_end, fwdid, revid = (
            self._proc_upload_reads_params(ctx, params))
        interleaved = 1 if (not single_end and not revid) else 0
        fileinput = [{'shock_id': fwdid,
                      'file_path': self.scratch + '/fwd/',
                      'unpack': 'uncompress'}]
        if revid:
            fileinput.append({'shock_id': revid,
                              'file_path': self.scratch + '/rev/',
                              'unpack': 'uncompress'})
        dfu = DataFileUtil(self.callback_url, token=ctx['token'])
        self.log('downloading reads files from Shock')
        files = dfu.shock_to_file_mass(fileinput)
        self.log('download complete, validating files')
        for f, i in zip(files, fileinput):
            if not self.validateFASTQ(
                    ctx, [{'file_path': f['file_path'],
                           'interleaved': interleaved
                           }])[0][0]['validated']:
                raise ValueError('Invalid fasta file {} from Shock node {}'
                                 .format(f['file_path'], i['shock_id']))
        self.log('file validation complete')
        self.log('coercing forward reads node to my control, muhahahaha!')
        fwdr = dfu.own_shock_node({'shock_id': fwdid, 'make_handle': 1})
        self.log('coercing complete, my evil schemes know no bounds')
        revr = None
        if revid:
            self.log('coercing reverse reads node to my control, muhahahaha!')
            revr = dfu.own_shock_node({'shock_id': revid, 'make_handle': 1})
            self.log('coercing complete. Will I stop at nothing?')

        # TODO calculate gc content, read size, read_count (find a program)
        fwdfile = {'file': fwdr['handle'],
                   'encoding': 'ascii',
                   'size': files[0]['size'],
                   'type': 'fq'
                   }
        if single_end:
            o['lib'] = fwdfile
        else:
            o['lib1'] = fwdfile
            if revr:
                o['lib2'] = {'file': revr['handle'],
                             'encoding': 'ascii',
                             'size': files[1]['size'],
                             'type': 'fq'
                             }

        so = {'type': kbtype,
              'data': o
              }
        if name:
            so['name'] = name
        else:
            so['objid'] = objid
        self.log('saving workspace object')
        oi = dfu.save_objects({'id': wsid, 'objects': [so]})[0]
        self.log('save complete')

        returnVal = {'obj_ref': str(oi[6]) + '/' + str(oi[0]) + '/' +
                     str(oi[4])}
        #END upload_reads

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method upload_reads return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def convert_read_library_to_file(self, ctx, params):
        """
        Convert read libraries to files
        :param params: instance of type "ConvertReadLibraryParams" (Input
           parameters for converting libraries to files. list<read_lib>
           read_libraries - the names of the workspace read library objects
           to convert. tern gzip - if true, gzip any unzipped files. If
           false, gunzip any zipped files. If null or missing, leave files as
           is unless unzipping is required for interleaving or
           deinterleaving, in which case the files will be left unzipped.
           tern interleaved - if true, provide the files in interleaved
           format if they are not already. If false, provide forward and
           reverse reads files. If null or missing, leave files as is.) ->
           structure: parameter "read_libraries" of list of type "read_lib"
           (A reference to a read library stored in the workspace service,
           whether of the KBaseAssembly or KBaseFile type. Usage of absolute
           references (e.g. 256/3/6) is strongly encouraged to avoid race
           conditions, although any valid reference is allowed.), parameter
           "gzip" of type "tern" (A ternary. Allowed values are 'false',
           'true', or null. Any other value is invalid.), parameter
           "interleaved" of type "tern" (A ternary. Allowed values are
           'false', 'true', or null. Any other value is invalid.)
        :returns: instance of type "ConvertReadLibraryOutput" (The output of
           the convert method. mapping<read_lib, ConvertedReadLibrary> files
           - a mapping of the read library workspace references to
           information about the converted data for each library.) ->
           structure: parameter "files" of mapping from type "read_lib" (A
           reference to a read library stored in the workspace service,
           whether of the KBaseAssembly or KBaseFile type. Usage of absolute
           references (e.g. 256/3/6) is strongly encouraged to avoid race
           conditions, although any valid reference is allowed.) to type
           "ConvertedReadLibrary" (Information about each set of reads.
           ReadsFiles files - the reads files. string ref - the absolute
           workspace reference of the reads file, e.g
           workspace_id/object_id/version. tern single_genome - whether the
           reads are from a single genome or a metagenome. null if unknown.
           tern read_orientation_outward - whether the read orientation is
           outward from the set of primers. null if unknown or single ended
           reads. string sequencing_tech - the sequencing technology used to
           produce the reads. null if unknown. KBaseCommon.StrainInfo strain
           - information about the organism strain that was sequenced. null
           if unavailable. KBaseCommon.SourceInfo source - information about
           the organism source. null if unavailable. float insert_size_mean -
           the mean size of the genetic fragments. null if unavailable or
           single end reads. float insert_size_std_dev - the standard
           deviation of the size of the genetic fragments. null if
           unavailable or single end reads. int read_count - the number of
           reads in the this dataset. null if unavailable. int read_size -
           the total size of the reads, in bases. null if unavailable. float
           gc_content - the GC content of the reads. null if unavailable.) ->
           structure: parameter "files" of type "ReadsFiles" (Reads file
           locations and gzip status. Only the relevant fields will be
           present in the structure. string fwd - the path to the forward /
           left reads. string rev - the path to the reverse / right reads.
           string inter - the path to the interleaved reads. string sing -
           the path to the single end reads. bool fwd_gz - whether the
           forward / left reads are gzipped. bool rev_gz - whether the
           reverse / right reads are gzipped. bool inter_gz - whether the
           interleaved reads are gzipped. bool sing_gz - whether the single
           reads are gzipped.) -> structure: parameter "fwd" of String,
           parameter "rev" of String, parameter "inter" of String, parameter
           "sing" of String, parameter "fwd_gz" of type "sbool" (A boolean.
           Allowed values are 'false' or 'true'. Any other value is
           invalid.), parameter "rev_gz" of type "sbool" (A boolean. Allowed
           values are 'false' or 'true'. Any other value is invalid.),
           parameter "inter_gz" of type "sbool" (A boolean. Allowed values
           are 'false' or 'true'. Any other value is invalid.), parameter
           "sing_gz" of type "sbool" (A boolean. Allowed values are 'false'
           or 'true'. Any other value is invalid.), parameter "ref" of
           String, parameter "single_genome" of type "tern" (A ternary.
           Allowed values are 'false', 'true', or null. Any other value is
           invalid.), parameter "read_orientation_outward" of type "tern" (A
           ternary. Allowed values are 'false', 'true', or null. Any other
           value is invalid.), parameter "sequencing_tech" of String,
           parameter "strain" of type "StrainInfo" (Information about a
           strain. genetic_code - the genetic code of the strain. See
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
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN convert_read_library_to_file


        self.log('Running convert_read_library_to_file with params:\n' +
                 pformat(params))

        token = ctx['token']

        self.process_params(params)
#         self.log('\n' + pformat(params))

        # Get the reads library
        ws = workspaceService(self.workspaceURL, token=token)
        ws_reads_ids = []
        for read_name in params[self.PARAM_IN_LIB]:
            ws_reads_ids.append({'ref': read_name})
        try:
            reads = ws.get_objects(ws_reads_ids)
        except WorkspaceException as e:
            self.log('Logging stacktrace from workspace exception:\n' + e.data)
            raise

        output = {}
        for read_name, read in zip(params[self.PARAM_IN_LIB], reads):
            self.log('=== processing read library ' + read_name + '===\n',
                     prefix_newline=True)
            output[read_name] = self.process_reads(
                read, params[self.PARAM_IN_GZIP],
                params[self.PARAM_IN_INTERLEAVED], token)
        output = {'files': output}

        #END convert_read_library_to_file

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method convert_read_library_to_file return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def export_reads(self, ctx, params):
        """
        Using the convert_read_library_to_file function, this prepares a standard
        KBase download package, zips it, and uploads to shock.
        :param params: instance of type "ExportParams" -> structure:
           parameter "input_ref" of String
        :returns: instance of type "ExportOutput" -> structure: parameter
           "shock_id" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN export_reads
        print('running export_reads')
        pprint(params)

        # for some reason, in tests this doesn't happen, or something cleans out the shock
        # temp directory.  So make sure the temp space exists.
        self.shock_temp = os.path.join(self.scratch, self.SHOCK_TEMP)
        self.mkdir_p(self.shock_temp)

         # validate parameters
        if 'input_ref' not in params:
            raise ValueError('Cannot export reads- no input_ref field defined.')

        # get WS metadata to get ws_name and obj_name
        ws = workspaceService(url=self.workspaceURL)
        info = ws.get_object_info_new({'objects':[{'ref': params['input_ref'] }],'includeMetadata':0, 'ignoreErrors':0})[0]

        # export to a file, don't set any conversion parameters
        read_libraries = [ params['input_ref'] ]
        read_lib_info = self.convert_read_library_to_file(ctx, { 
                              'read_libraries': read_libraries
                            })[0]['files']
        pprint(read_lib_info)

        # create the output directory and move the file there
        export_package_dir = os.path.join(self.scratch, info[1])
        os.makedirs(export_package_dir)
        for r in read_lib_info:
            lib = read_lib_info[r]

            if 'fwd' in lib['files'] and lib['files']['fwd'] is not None and lib['files']['fwd'] is not '':
                f_name = lib['files']['fwd']
                print('packaging fwd reads file: '+f_name)
                shutil.move(f_name, os.path.join(export_package_dir, os.path.basename(f_name)))

            if 'rev' in lib['files'] and lib['files']['rev'] is not None and lib['files']['rev'] is not '':
                print('packaging rev reads file: '+f_name)
                f_name = lib['files']['rev']
                shutil.move(f_name, os.path.join(export_package_dir, os.path.basename(f_name)))

            if 'inter' in lib['files'] and lib['files']['inter'] is not None and lib['files']['inter'] is not '':
                print('packaging interleaved reads file: '+f_name)
                f_name = lib['files']['inter']
                shutil.move(f_name, os.path.join(export_package_dir, os.path.basename(f_name)))

            if 'sing' in lib['files'] and lib['files']['sing'] is not None and lib['files']['sing'] is not '':
                print('packaging single end reads file: '+f_name)
                f_name = lib['files']['sing']
                shutil.move(f_name, os.path.join(export_package_dir, os.path.basename(f_name)))   

        # package it up and be done
        dfUtil = DataFileUtil(self.callback_url)
        package_details = dfUtil.package_for_download({
                                    'file_path': export_package_dir,
                                    'ws_refs': [ params['input_ref'] ]
                                })

        output = { 'shock_id': package_details['shock_id'] }


        #END export_reads

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method export_reads return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

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
