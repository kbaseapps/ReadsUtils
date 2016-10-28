# -*- coding: utf-8 -*-
#BEGIN_HEADER
import time
import subprocess
import os
import tempfile
import shutil
from pprint import pformat
from DataFileUtil.DataFileUtilClient import DataFileUtil
from DataFileUtil.baseclient import ServerError as DFUError
from kb_ea_utils.kb_ea_utilsClient import kb_ea_utils
from Workspace.WorkspaceClient import Workspace
from Workspace.baseclient import ServerError as WorkspaceError
from numbers import Number
import six
import uuid
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
    VERSION = "0.1.1"
    GIT_URL = "https://github.com/mrcreosote/ReadsUtils"
    GIT_COMMIT_HASH = "43386a99be668244c08048afbe190fdbde3245f6"

    #BEGIN_CLASS_HEADER

    TRUE = 'true'
    FALSE = 'false'

    FASTA_JAR = '/opt/lib/FastaValidator-1.0.jar'
    FASTQ_EXE = 'fastQValidator'

    FASTA_EXT = ['.fa', '.fas', '.fasta', '.fna']
    FASTQ_EXT = ['.fq', '.fastq', '.fnq']

    COMPRESS_EXT = ['.gz', '.gzip', '.bz', '.bzip', '.bz2', '.bzip2']

    PARAM_IN_LIB = 'read_libraries'
    PARAM_IN_INTERLEAVED = 'interleaved'

    SINGLE_END_TYPE = 'SingleEndLibrary'
    PAIRED_END_TYPE = 'PairedEndLibrary'
    # one of these should be deprecated
    KBASE_FILE = 'KBaseFile'
    KBASE_ASSEMBLY = 'KBaseAssembly'
    MODULE_NAMES = [KBASE_FILE, KBASE_ASSEMBLY]
    TYPE_NAMES = [SINGLE_END_TYPE, PAIRED_END_TYPE]

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

    def _proc_upload_reads_params(self, params):
        fwdid = params.get('fwd_id')
        fwdfile = params.get('fwd_file')
        if not self.xor(fwdid, fwdfile):
            raise ValueError('Exactly one of a file or shock id containing ' +
                             'a forwards reads file must be specified')
        shock = True if fwdid else False
        fwdid = fwdid if shock else os.path.abspath(
            os.path.expanduser(fwdfile))
        wsid = params.get('wsid')
        wsname = params.get('wsname')
        if not self.xor(wsid, wsname):
            raise ValueError(
                'Exactly one of the workspace ID or name must be provided')
        dfu = DataFileUtil(self.callback_url)
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
        revfile = params.get('rev_file')
        if revid and revfile:
            raise ValueError('Specified both a local file and a shock node ' +
                             'for the reverse reads file')
        if shock and revfile:
            raise ValueError('Cannot specify a local reverse reads file ' +
                             'with a forward reads file in shock')
        if not shock and revid:
            raise ValueError('Cannot specify a reverse reads file in shock ' +
                             'with a local forward reads file')
        if not shock and revfile:
            revid = os.path.abspath(os.path.expanduser(revfile))
        interleaved = 1 if params.get('interleaved') else 0
        kbtype = 'KBaseFile.SingleEndLibrary'
        single_end = True
        if interleaved or revid:
            kbtype = 'KBaseFile.PairedEndLibrary'
            single_end = False
        if revid:
            interleaved = 1
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
            read_orientation_out = 1 if params.get('read_orientation_outward') else 0
            o.update({'insert_size_mean': ism,
                      'insert_size_std_dev': issd,
                      'interleaved': interleaved,
                      'read_orientation_outward': read_orientation_out
                      })
        return o, wsid, name, objid, kbtype, single_end, fwdid, revid, shock

    def process_files_for_upload(self, fwdfile, revfile, interleaved):
        params = [{'file_path': fwdfile,
                   'make_handle': 1,
                   'pack': 'gzip'}]
        if revfile:
            params.append({'file_path': revfile,
                           'make_handle': 1,
                           'pack': 'gzip'})
        self.log('validating files')
        for f in params:
            valid = self.validateFASTQ({}, [{'file_path': f['file_path'],
                                       'interleaved': interleaved}])
            if not valid[0][0]['validated']:
                raise ValueError('Invalid fasta file ' + f['file_path'])
        self.log('validation complete, uploading files to shock')
        dfu = DataFileUtil(self.callback_url)
        files = dfu.file_to_shock_mass(params)
        if revfile:
            return (files[0]['handle'], files[1]['handle'],
                    files[0]['size'], files[1]['size'])
        return files[0]['handle'], None, files[0]['size'], None

    def process_ternary(self, params, boolname):
        if params.get(boolname) is None:
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
                raise ValueError('Invalid workspace object name: ' +
                                 str(read_name))
        params[self.PARAM_IN_LIB] = reads

        self.process_ternary(params, self.PARAM_IN_INTERLEAVED)

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

    def _get_ext(self, fn, extensions):
        for e in extensions:
            if fn.endswith(e):
                return e
        return None

    def _filename_ok(self, fn):
        if not fn:
            return False
        fn = fn.lower()
        if (self._get_ext(fn, self.FASTQ_EXT)):
            return True
        compress_ext = self._get_ext(fn, self.COMPRESS_EXT)
        if not compress_ext:
            return False
        fn = fn[0: -len(compress_ext)]
        if (self._get_ext(fn, self.FASTQ_EXT)):
            return True
        return False

    def _download_reads_from_shock(self, ref, obj_name, handle, file_type):
        params = {'shock_id': handle['id'],
                  'unpack': 'uncompress',
                  'file_path': os.path.join(self.scratch, handle['id'])
                  }
        # TODO LATER may want to do dl en masse, but that means if there's
        # TODO a bad file it won't be caught until everythings dl'd @IgnorePep8
        # TODO LATER add method to DFU to get shock attribs and check filename prior to
        # TODO download LATER at least check handle filename & file type are
        # TODO ok before download @IgnorePep8
        dfu = DataFileUtil(self.callback_url)
        ret = dfu.shock_to_file(params)
        fn = ret['node_file_name']
        if file_type and not file_type.startswith('.'):
            file_type = '.' + file_type
        ok = False
        for f, n in zip([fn, handle['file_name'], file_type],
                        ['Shock file name',
                         'Handle file name from reads Workspace object',
                         'File type from reads Workspace object']):
            if f:
                if not self._filename_ok(f):
                    raise ValueError(
                        ('{} is illegal: {}. Expected FASTQ file. Reads ' +
                         'object {} ({}). Shock node {}')
                        .format(n, f, obj_name, ref, handle['id']))
                ok = True
        # TODO this is untested. You have to try pretty hard to upload a file
        # TODO without a name to Shock.
        if not ok:
            raise ValueError(
                'Unable to determine file type from Shock or Workspace ' +
                'data. Reads object {} ({}). Shock node {}'
                .format(obj_name, ref, handle['id']))
        if not fn:
            self.log('No filename available from Shock')
        else:
            self.log('Filename from Shock: ' + fn)
        return ret['file_path'], fn

    def mv(self, oldfile, newfile):
        self.log('Moving {} to {}'.format(oldfile, newfile))
        shutil.move(oldfile, newfile)

    def process_single_end(self, ref, obj_name, handle, file_type=None):
        path, name = self._download_reads_from_shock(
            ref, obj_name, handle, file_type)
        np = path + '.single.fastq'
        self.mv(path, np)
        return {'fwd': np,
                'fwd_name': name,
                'rev': None,
                'rev_name': None,
                'otype': 'single',
                'type': 'single'}

    def get_file_prefix(self):
        return os.path.join(self.scratch, str(uuid.uuid4()))

    # should probably make an InterleaveProcessor class to avoid these
    # insane method sigs

    def _read_fq_record(self, source_obj_ref, source_obj_name,
                        shock_filename, shock_node, f):
        r = ''
        for i in xrange(4):
            l = f.readline()
            while (l == '\n'):  # skip blank lines
                l = f.readline()
            if not l:  # EOF
                if i != 0:
                    error_message_bindings = [shock_node, shock_filename]
                    error_message = 'Reading FASTQ record failed - non-blank lines are ' \
                                    'not a multiple of four. '
                    if source_obj_ref is not None and source_obj_name is not None:
                        error_message += 'Workspace reads object {} ({}), '
                        error_message_bindings.insert(0, source_obj_ref)
                        error_message_bindings.insert(0, source_obj_name)
                    error_message += 'Shock node {}, Shock filename {}'
                    raise ValueError(error_message.format(*error_message_bindings))
                else:
                    return ''
            r = r + l
        return r

    # this assumes that the FASTQ files are properly formatted and matched,
    # which they should be if they're in KBase.
    def interleave(self, source_obj_ref, source_obj_name, fwd_shock_filename,
                   fwd_shock_node, rev_shock_filename, rev_shock_node,
                   fwdpath, revpath, targetpath):
        self.log('Interleaving files {} and {} to {}'.format(
            fwdpath, revpath, targetpath))
        with open(targetpath, 'w') as t:
            with open(fwdpath, 'r') as f, open(revpath, 'r') as r:
                while True:
                    frec = self._read_fq_record(
                        source_obj_ref, source_obj_name,
                        fwd_shock_filename, fwd_shock_node, f)
                    rrec = self._read_fq_record(
                        source_obj_ref, source_obj_name,
                        rev_shock_filename, rev_shock_node, r)
                    if (not frec and rrec) or (frec and not rrec):
                        error_message_bindings = [fwd_shock_node, fwd_shock_filename,
                                                  rev_shock_node, rev_shock_filename]
                        error_message = 'Interleave failed - reads files do not have '\
                                        'an equal number of records. '
                        if source_obj_name is not None and source_obj_ref is not None:
                            error_message += 'Workspace reads object {} ({}), '
                            error_message_bindings.insert(0, source_obj_ref)
                            error_message_bindings.insert(0, source_obj_name)
                        error_message += 'forward Shock node {}, filename {}, ' \
                                         'reverse Shock node {}, filename {}'
                        raise ValueError(error_message.format(*error_message_bindings))
                    if not frec:  # not rrec is implied at this point
                        break
                    t.write(frec)
                    t.write(rrec)

    # this assumes that the FASTQ file is properly formatted, which it should
    # be if it's in KBase. Credit:
    # https://www.biostars.org/p/19446/#117160
    def deinterleave(self, source_obj_ref, source_obj_name, shock_filename,
                     shock_node, filepath, fwdpath, revpath):
        self.log('Deinterleaving file {} to files {} and {}'.format(
            filepath, fwdpath, revpath))
        with open(filepath, 'r') as s:
            with open(fwdpath, 'w') as f, open(revpath, 'w') as r:
                count = 0
                for line in s:
                    if not line.strip():
                        continue
                    if count % 8 < 4:
                        f.write(line)
                    else:
                        r.write(line)
                    count += 1
        if count % 8 != 0:
            raise ValueError('Deinterleave failed - line count ' +
                             'is not divisible by 8. Workspace reads object ' +
                             '{} ({}), Shock node {}, Shock filename {}.'
                             .format(source_obj_name, source_obj_ref,
                                     shock_node, shock_filename))

    # there's got to be better way to do this than these processing methods.
    # make some input classes for starters to fix these gross method sigs

    def process_interleaved(self, source_obj_ref, source_obj_name,
                            handle, interleave, file_type=None):

        path, name = self._download_reads_from_shock(
            source_obj_ref, source_obj_name, handle, file_type)

        ret = {}
        if interleave is not False:  # e.g. True or None
            np = path + '.inter.fastq'
            self.mv(path, np)
            ret = {'fwd': np,
                   'fwd_name': name,
                   'rev': None,
                   'rev_name': None,
                   'otype': 'interleaved',
                   'type': 'interleaved'}
        else:
            fwdpath = os.path.join(self.scratch, self.get_file_prefix() +
                                   '.fwd.fastq')
            revpath = os.path.join(self.scratch, self.get_file_prefix() +
                                   '.rev.fastq')
            self.deinterleave(source_obj_ref, source_obj_name, name,
                              handle['id'], path, fwdpath, revpath)
            ret = {'fwd': fwdpath,
                   'fwd_name': name,
                   'rev': revpath,
                   'rev_name': None,
                   'otype': 'interleaved',
                   'type': 'paired'
                   }
        return ret

    def process_paired(self, source_obj_ref, source_obj_name,
                       fwdhandle, revhandle, interleave,
                       fwd_file_type=None, rev_file_type=None):

        fwdpath, fwdname = self._download_reads_from_shock(
            source_obj_ref, source_obj_name, fwdhandle, fwd_file_type)
        revpath, revname = self._download_reads_from_shock(
            source_obj_ref, source_obj_name, revhandle, rev_file_type)

        ret = {}
        if interleave:
            # we expect the job runner to clean up for us
            intpath = os.path.join(self.scratch, self.get_file_prefix() +
                                   '.inter.fastq')
            self.interleave(source_obj_ref, source_obj_name, fwdname, fwdhandle['id'],
                            revname, revhandle['id'], fwdpath, revpath, intpath)
            ret = {'fwd': intpath,
                   'fwd_name': fwdname,
                   'rev': None,
                   'rev_name': revname,
                   'otype': 'paired',
                   'type': 'interleaved'
                   }
        else:
            nf = fwdpath + '.fwd.fastq'
            nr = revpath + '.rev.fastq'
            self.mv(fwdpath, nf)
            self.mv(revpath, nr)
            ret = {'fwd': nf,
                   'fwd_name': fwdname,
                   'rev': nr,
                   'rev_name': revname,
                   'otype': 'paired',
                   'type': 'paired'
                   }
        return ret

    def process_reads(self, reads, interleave):
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
                sreads = data['lib']['file']
                type_ = data['lib']['type']
                ret['files'] = self.process_single_end(
                    ref, obj_name, sreads, type_)
            else:
                fwd_reads = data['lib1']['file']
                fwd_type = data['lib1']['type']
                if 'lib2' in data:  # not interleaved
                    rev_reads = data['lib2']['file']
                    rev_type = data['lib2']['type']
                    ret['files'] = self.process_paired(
                        ref, obj_name, fwd_reads, rev_reads,
                        interleave, fwd_type, rev_type)
                else:
                    ret['files'] = self.process_interleaved(
                        ref, obj_name, fwd_reads, interleave, fwd_type)
        else:  # KBaseAssembly
            if single:
                ret['files'] = self.process_single_end(
                    ref, obj_name, data['handle'])
            else:
                if 'handle_2' in data:  # not interleaved
                    ret['files'] = self.process_paired(
                        ref, obj_name, data['handle_1'],
                        data['handle_2'], interleave)
                else:
                    ret['files'] = self.process_interleaved(
                        ref, obj_name, data['handle_1'], interleave)

        return ret

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
        # see https://github.com/jwaldman/FastaValidator/blob/master/src/demo/FVTester.java
        # note the version in jars returns non-zero error codes:
        # https://github.com/srividya22/FastaValidator/commit/67e2d860f1869b9a76033e71fb2aaff910b7c2e3
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

    def calculate_fq_stats(self, reads_object, file_path):
        eautils = kb_ea_utils(self.callback_url)
        ea_report = eautils.get_ea_utils_stats({'read_library_path': file_path})
#        print "Full Report : {}".format(ea_report)

        report_lines = ea_report.splitlines()
        report_to_object_mappings = {'reads': 'read_count',
                                     'total bases': 'total_bases',
                                     'len mean': 'read_length_mean',
                                     'len stdev': 'read_length_stdev',
                                     'phred': 'phred_type',
                                     'dups': 'number_of_duplicates',
                                     'qual min': 'qual_min',
                                     'qual max': 'qual_max',
                                     'qual mean': 'qual_mean',
                                     'qual stdev': 'qual_stdev'}
        integer_fields = ['read_count', 'total_bases', 'number_of_duplicates']
        for line in report_lines:
            line_elements = line.split()
            line_value = line_elements.pop()
            line_key = " ".join(line_elements)
            line_key = line_key.strip()
            if line_key in report_to_object_mappings:
                #print ":{}: = :{}:".format(report_to_object_mappings[line_key],line_value)
                value_to_use = None
                if line_key == 'phred':
                    value_to_use = line_value.strip()
                elif report_to_object_mappings[line_key] in integer_fields:
                    value_to_use = int(line_value.strip())
                else:
                    value_to_use = float(line_value.strip())
                reads_object[report_to_object_mappings[line_key]] = value_to_use
            elif line_key.startswith("%") and not line_key.startswith("%dup"):
                if 'base_percentages' not in reads_object:
                    reads_object['base_percentages'] = dict()
                dict_key = line_key.strip("%")
                reads_object['base_percentages'][dict_key] = float(line_value.strip())
        #populate the GC content (as a value betwwen 0 and 1)
        if 'base_percentages' in reads_object:
            gc_content = 0
            if "G" in reads_object['base_percentages']:
                gc_content += reads_object['base_percentages']["G"]
            if "C" in reads_object['base_percentages']:
                gc_content += reads_object['base_percentages']["C"]
            reads_object["gc_content"] = gc_content / 100
        #set number of dups if no dups, but read_count
        if 'read_count' in reads_object and 'number_of_duplicates' not in reads_object:
            reads_object["number_of_duplicates"] = 0
        return reads_object

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.scratch = config['scratch']
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.ws_url = config['workspace-url']
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
           upload_reads function. If local files are specified for upload,
           they must be uncompressed. Files will be gzipped prior to upload.
           Note that if a reverse read file is specified, it must be a local
           file if the forward reads file is a local file, or a shock id if
           not. Required parameters: fwd_id - the id of the shock node
           containing the reads data file: either single end reads,
           forward/left reads, or interleaved reads. - OR - fwd_file - a
           local path to the reads data file: either single end reads,
           forward/left reads, or interleaved reads. sequencing_tech - the
           sequencing technology used to produce the reads. One of: wsid -
           the id of the workspace where the reads will be saved (preferred).
           wsname - the name of the workspace where the reads will be saved.
           One of: objid - the id of the workspace object to save over name -
           the name to which the workspace object will be saved Optional
           parameters: rev_id - the shock node id containing the
           reverse/right reads for paired end, non-interleaved reads. - OR -
           rev_file - a local path to the reads data file containing the
           reverse/right reads for paired end, non-interleaved reads, note the
           reverse file will get interleaved with the forward file.
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
           parameter "fwd_file" of String, parameter "wsid" of Long,
           parameter "wsname" of String, parameter "objid" of Long, parameter
           "name" of String, parameter "rev_id" of String, parameter
           "rev_file" of String, parameter "sequencing_tech" of String,
           parameter "single_genome" of type "boolean" (A boolean - 0 for
           false, 1 for true. @range (0, 1)), parameter "strain" of type
           "StrainInfo" (Information about a strain. genetic_code - the
           genetic code of the strain. See
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
        o, wsid, name, objid, kbtype, single_end, fwdid, revid, shock = (
            self._proc_upload_reads_params(params))
        #IF from shock fwdid and revid are shock nodes, if not shock they are file paths
        dfu = DataFileUtil(self.callback_url)
        fwdpath = None
        revpath = None
        if shock:
            #Grab files from Shock
            fileinput = [{'shock_id': fwdid,
                          'file_path': self.scratch + '/fwd/',
                          'unpack': 'uncompress'}]
            if revid:
                fileinput.append({'shock_id': revid,
                                  'file_path': self.scratch + '/rev/',
                                  'unpack': 'uncompress'})
            self.log('downloading reads file(s) from Shock')
            files = dfu.shock_to_file_mass(fileinput)
            shock = False
            fwdpath = files[0]["file_path"]
            fwdname = files[0]["node_file_name"]
            if revid:
                revpath = files[1]["file_path"]
                revname = files[1]["node_file_name"]
        else:
            #Not shock
            fwdpath = fwdid
            revpath = revid
            fwdname = None
            revname = None
        shock = False
        if revid:
            #now interleave the files
            intpath = os.path.join(self.scratch, self.get_file_prefix() + '.inter.fastq')
            self.interleave(None, None, fwdname, fwdpath,
                            revname, revpath, fwdpath, revpath, intpath)
            fwdpath = intpath
            revid = None
            revpath = None

        interleaved = 1 if (not single_end and not revid) else 0

        fhandle, rhandle, fsize, rsize = \
            self.process_files_for_upload(fwdpath, revpath, interleaved)

        #calculate the stats for fwd_file.
        o = self.calculate_fq_stats(o, fwdpath)

        fwdfile = {'file': fhandle,
                   'encoding': 'ascii',
                   'size': fsize,
                   'type': 'fq'
                   }
        if single_end:
            o['lib'] = fwdfile
        else:
            o['lib1'] = fwdfile
            if rhandle:
                o['lib2'] = {'file': rhandle,
                             'encoding': 'ascii',
                             'size': rsize,
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

    def download_reads(self, ctx, params):
        """
        Download read libraries. Reads compressed with gzip or bzip are
        automatically uncompressed.
        :param params: instance of type "DownloadReadsParams" (Input
           parameters for downloading reads objects. list<read_lib>
           read_libraries - the the workspace read library objects to
           download. tern interleaved - if true, provide the files in
           interleaved format if they are not already. If false, provide
           forward and reverse reads files. If null or missing, leave files
           as is.) -> structure: parameter "read_libraries" of list of type
           "read_lib" (A reference to a read library stored in the workspace
           service, whether of the KBaseAssembly or KBaseFile type. Usage of
           absolute references (e.g. 256/3/6) is strongly encouraged to avoid
           race conditions, although any valid reference is allowed.),
           parameter "interleaved" of type "tern" (A ternary. Allowed values
           are 'false', 'true', or null. Any other value is invalid.)
        :returns: instance of type "DownloadReadsOutput" (The output of the
           download method. mapping<read_lib, DownloadedReadLibrary> files -
           a mapping of the read library workspace references to information
           about the converted data for each library.) -> structure:
           parameter "files" of mapping from type "read_lib" (A reference to
           a read library stored in the workspace service, whether of the
           KBaseAssembly or KBaseFile type. Usage of absolute references
           (e.g. 256/3/6) is strongly encouraged to avoid race conditions,
           although any valid reference is allowed.) to type
           "DownloadedReadLibrary" (Information about each set of reads.
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
           information. Note that the file names provided are those *prior
           to* interleaving or deinterleaving the reads. string fwd - the
           path to the forward / left reads. string fwd_name - the name of
           the forwards reads file from Shock, or if not available, from the
           Shock handle. string rev - the path to the reverse / right reads.
           null if the reads are single end or interleaved. string rev_name -
           the name of the reverse reads file from Shock, or if not
           available, from the Shock handle. null if the reads are single end
           or interleaved. string otype - the original type of the reads. One
           of 'single', 'paired', or 'interleaved'. string type - one of
           'single', 'paired', or 'interleaved'.) -> structure: parameter
           "fwd" of String, parameter "fwd_name" of String, parameter "rev"
           of String, parameter "rev_name" of String, parameter "otype" of
           String, parameter "type" of String, parameter "ref" of String,
           parameter "single_genome" of type "tern" (A ternary. Allowed
           values are 'false', 'true', or null. Any other value is invalid.),
           parameter "read_orientation_outward" of type "tern" (A ternary.
           Allowed values are 'false', 'true', or null. Any other value is
           invalid.), parameter "sequencing_tech" of String, parameter
           "strain" of type "StrainInfo" (Information about a strain.
           genetic_code - the genetic code of the strain. See
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
        #BEGIN download_reads
        ''' potential improvements:
            Add continue_on_failure mode that reports errors for each failed
                conversion rather than failing completely.
            Parallelize - probably not worth it, this is all IO bound. Try if
                there's nothing better to do. If so, each process/thread needs
                its own shock_tmp folder.
            Add user specified failure conditions - e.g. fail if is/is not
                metagenome, outwards reads, etc.
        '''
        del ctx
        self.log('Running download_reads with params:\n' +
                 pformat(params))

        self.process_params(params)
#         self.log('\n' + pformat(params))

        dfu = DataFileUtil(self.callback_url)
        # Get the reads library
        ws_reads_ids = params[self.PARAM_IN_LIB]
        try:
            reads = dfu.get_objects({'object_refs': ws_reads_ids})['data']
        except DFUError as e:
            self.log('Logging stacktrace from workspace exception:\n' + e.data)
            raise

        output = {}
        for read_name, read in zip(ws_reads_ids, reads):
            self.log('=== processing read library ' + read_name + '===\n',
                     prefix_newline=True)
            output[read_name] = self.process_reads(
                read, params[self.PARAM_IN_INTERLEAVED])
        output = {'files': output}
        #END download_reads

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method download_reads return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def export_reads(self, ctx, params):
        """
        KBase downloader function. Packages a set of reads into a zip file and
        stores the zip in shock.
        :param params: instance of type "ExportParams" (Standard KBase
           downloader input.) -> structure: parameter "input_ref" of String
        :returns: instance of type "ExportOutput" (Standard KBase downloader
           output.) -> structure: parameter "shock_id" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN export_reads

        inref = params.get('input_ref')
        if not inref:
            raise ValueError('No input_ref specified')

        # get WS metadata to get obj_name
        ws = Workspace(self.ws_url)
        try:
            info = ws.get_object_info_new({'objects': [{'ref': inref}]})[0]
        except WorkspaceError as wse:
            self.log('Logging workspace exception')
            self.log(str(wse))
            raise

        files = self.download_reads(
            ctx, {self.PARAM_IN_LIB: [inref]})[0]['files'][inref]['files']

        # create the output directory and move the file there
        tempdir = tempfile.mkdtemp(dir=self.scratch)
        export_dir = os.path.join(tempdir, info[1])
        os.makedirs(export_dir)
        fwd = files['fwd']
        shutil.move(fwd, os.path.join(export_dir, os.path.basename(fwd)))
        rev = files.get('rev')
        if rev:
            shutil.move(rev, os.path.join(export_dir, os.path.basename(rev)))

        # package and load to shock
        dfu = DataFileUtil(self.callback_url)
        ret = dfu.package_for_download({'file_path': export_dir,
                                        'ws_refs': [inref]
                                        })

        output = {'shock_id': ret['shock_id']}

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
