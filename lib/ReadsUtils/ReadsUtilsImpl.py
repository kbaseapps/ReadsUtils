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
import urllib2
from contextlib import closing
import ftplib
import re
import gzip
from itertools import islice
#END_HEADER


class ReadsUtils:
    '''
    Module Name:
    ReadsUtils

    Module Description:
    Utilities for handling reads files.
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.3.4"
    GIT_URL = "git@github.com:Tianhao-Gu/ReadsUtils.git"
    GIT_COMMIT_HASH = "d96fa904641d8e5900be2bd3be62face57990887"

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

    # staging file prefix
    STAGING_FILE_PREFIX = '/data/bulk/'

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

        fwdsource, reads_source = (self._process_fwd_params(
            params.get('fwd_id'), params.get('fwd_file'), params.get('fwd_file_url'), 
            params.get('fwd_staging_file_name'), params.get('download_type')))

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

        revsource = self._process_rev_params(params.get('rev_id'), params.get('rev_file'), 
            params.get('rev_file_url'), params.get('rev_staging_file_name'), reads_source)

        interleaved = 0
        kbtype = 'KBaseFile.SingleEndLibrary'
        single_end = True
        if params.get('interleaved') or revsource:
            interleaved = 1
            kbtype = 'KBaseFile.PairedEndLibrary'
            single_end = False

        source_reads_ref = params.get('source_reads_ref')
        if source_reads_ref:
            o = self._propagate_reference_reads_info(params, dfu,
                                                     source_reads_ref,
                                                     interleaved, single_end)
        else:
            o = self._build_up_reads_data(params, single_end)
        return o, wsid, name, objid, kbtype, single_end, fwdsource, revsource, reads_source

    def _check_rev_params(self, revid, revfile, revurl, revstaging, reads_source):
        if sum(bool(e) for e in [revid, revfile, revurl, revstaging]) > 1:
            raise ValueError('Cannot specify more than one rev file source')

        if revid and reads_source != 'shock':
            raise ValueError(
                'Specified reverse reads file in shock path but missing ' +
                'forward reads file in shock')
        if revfile and reads_source != 'local':
            raise ValueError(
                'Specified local reverse file path but missing local forward file path')
        if revurl and reads_source != 'web':
            raise ValueError(
                'Specified reverse file URL but missing forward file URL')
        if revstaging and reads_source != 'staging':
            raise ValueError(
                'Specified reverse staging file but missing forward staging file')

    def _process_rev_params(self, revid, revfile, revurl, revstaging, reads_source):

        self._check_rev_params(revid, revfile, revurl, revstaging, reads_source)

        if revurl:
            revsource = revurl
        elif revstaging:
            revsource = revstaging
        elif revfile:
            revsource = os.path.abspath(os.path.expanduser(revfile))
        else:
            revsource = revid

        return revsource


    def _process_fwd_params(self, fwdid, fwdfile, fwdurl, fwdstaging, download_type):

        if sum(bool(e) for e in [fwdid, fwdfile, fwdurl, fwdstaging]) != 1:
            raise ValueError('Exactly one of a file, shock id, staging ' +
                             'file name or file url containing ' +
                             'a forwards reads file must be specified')
        if fwdurl:
            if not download_type:
                raise ValueError(
                    'Both download_type and fwd_file_url must be provided')
            reads_source = 'web'
            fwdsource = fwdurl
        elif fwdstaging:
            reads_source = 'staging'
            fwdsource = fwdstaging
        elif fwdid:
            reads_source = 'shock'
            fwdsource = fwdid
        else:
            reads_source = 'local'
            fwdsource = os.path.abspath(os.path.expanduser(fwdfile))

        return fwdsource, reads_source

    def _propagate_reference_reads_info(self, params, dfu, source_reads_ref,
                                        interleaved, single_end):
        # Means the uploaded reads is a result of an input reads object being filtered/trimmed
        # Make sure that no non file related parameters are set. If so throw
        # error.
        parameters_should_unfilled = ['insert_size_mean', 'insert_size_std_dev',
                                      'sequencing_tech', 'strain',
                                      'source', 'read_orientation_outward']
        if any(x in params for x in parameters_should_unfilled):
            self.log(("'source_reads_ref' was passed, making the following list of " +
                      "parameters {} erroneous to " +
                      "include").format(",".join(parameters_should_unfilled)))
            raise ValueError(("'source_reads_ref' was passed, making the following list of " +
                              "parameters : {} erroneous to " +
                              "include").format(", ".join(parameters_should_unfilled)))
        try:
            source_reads_object = dfu.get_objects({'object_refs':
                                                   [source_reads_ref]})['data'][0]
        except DFUError as e:
            self.log(('The supplied source_reads_ref {} was not able to be retrieved. ' +
                      'Logging stacktrace from workspace exception:' +
                      '\n{}').format(source_reads_ref, e.data))
            raise
        # Check that it is a reads object. If not throw an eror.
        single_input, kbasefile = self.check_reads(source_reads_object)
        if not single_input and not single_end:
            is_single_end = False
        elif single_input and not single_end:
            raise ValueError(("The input reference reads is single end, that should not " +
                              "give rise to a paired end object."))
        else:
            is_single_end = True
        return self._build_up_reads_data(source_reads_object['data'], is_single_end)

    def _build_up_reads_data(self, params, is_single_end):
        seqtype = params.get('sequencing_tech')
        if not seqtype:
            raise ValueError('The sequencing technology must be provided')
        sg = 1
        if 'single_genome' in params and not params['single_genome']:
            sg = 0
        o = {'sequencing_tech': seqtype,
             'single_genome': sg
             }
        self._add_field(o, params, 'strain')
        self._add_field(o, params, 'source')
        if not is_single_end:
            # is a paired end input and trying to upload a filtered/trimmed
            # paired end ReadsUtils. need to check for more fields.
            ism = params.get('insert_size_mean')
            self._check_pos(ism, 'insert_size_mean')
            issd = params.get('insert_size_std_dev')
            self._check_pos(issd, 'insert_size_std_dev')
            if params.get('read_orientation_outward'):
                read_orientation_out = 1
            else:
                read_orientation_out = 0
            o.update({'insert_size_mean': ism,
                      'insert_size_std_dev': issd,
                      'interleaved': 1,
                      'read_orientation_outward': read_orientation_out
                      })
        return o

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
        self.copy_field(data, 'total_bases', ret)
        self.copy_field(data, 'read_length_mean', ret)
        self.copy_field(data, 'read_length_stdev', ret)
        self.copy_field(data, 'phred_type', ret)
        self.copy_field(data, 'number_of_duplicates', ret)
        self.copy_field(data, 'qual_min', ret)
        self.copy_field(data, 'qual_max', ret)
        self.copy_field(data, 'qual_mean', ret)
        self.copy_field(data, 'qual_stdev', ret)
        self.copy_field(data, 'base_percentages', ret)

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
        # TODO LATER may want to do dl en masse, but that means if there's a bad file it won't be caught until everythings dl'd @IgnorePep8 # noqa
        # TODO LATER add method to DFU to get shock attribs and check filename prior to download @IgnorePep8 # noqa
        # TODO LATER at least check handle filename & file type are ok before
        # download
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
        # TODO this is untested. You have to try pretty hard to upload a file without a name to Shock. @IgnorePep8 # noqa
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
                        shock_filename, shock_node, f,
                        reads_source, filesource):
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

                    if reads_source == 'web':
                        error_message += 'File URL {}, '
                        error_message_bindings.insert(0, filesource)

                    if reads_source == 'staging':
                        error_message += 'Staging file name {}, '
                        error_message_bindings.insert(0, filesource)

                    error_message += 'Shock node {}, Shock filename {}'
                    raise ValueError(error_message.format(
                        *error_message_bindings))
                else:
                    return ''
            r = r + l
        return r

    # this assumes that the FASTQ files are properly formatted and matched,
    # which they should be if they're in KBase.
    # source_obj_ref and source_obj_name will be None if done from upload.
    # reads_source, fwdsource, revsource will be None if done from process_paired.
    def interleave(self, source_obj_ref, source_obj_name, fwd_shock_filename,
                   fwd_shock_node, rev_shock_filename, rev_shock_node,
                   fwdpath, revpath, targetpath, reads_source, fwdsource, revsource):
        self.log('Interleaving files {} and {} to {}'.format(
            fwdpath, revpath, targetpath))
        with open(targetpath, 'w') as t:
            with open(fwdpath, 'r') as f, open(revpath, 'r') as r:
                while True:
                    frec = self._read_fq_record(
                        source_obj_ref, source_obj_name,
                        fwd_shock_filename, fwd_shock_node, f, 
                        reads_source, fwdsource)
                    rrec = self._read_fq_record(
                        source_obj_ref, source_obj_name,
                        rev_shock_filename, rev_shock_node, r, 
                        reads_source, revsource)
                    error_message_bindings = list()
                    if (not frec and rrec) or (frec and not rrec):
                        error_message = 'Interleave failed - reads files do not have '\
                                        'an equal number of records. '
                        if source_obj_name is not None and source_obj_ref is not None:
                            error_message += 'Workspace reads object {} ({}). '
                            error_message_bindings.insert(0, source_obj_ref)
                            error_message_bindings.insert(0, source_obj_name)
                        if fwd_shock_node is not None and rev_shock_node is not None:
                            error_message += 'forward Shock node {}, filename {}, ' \
                                             'reverse Shock node {}, filename {}. '
                            error_message_bindings.extend([fwd_shock_node, fwd_shock_filename,
                                                           rev_shock_node, rev_shock_filename])
                        error_message += 'Forward Path {}, Reverse Path {}.'
                        error_message_bindings.extend([fwdpath, revpath])

                        if reads_source == 'web':
                            error_message += 'Forward File URL {}, Reverse File URL {}.'
                            error_message_bindings.extend([fwdsource, revsource])

                        if reads_source == 'staging':
                            error_message += 'Forward Staging file name {}, '
                            error_message += 'Reverse Staging file name {}.'
                            error_message_bindings.extend([fwdsource, revsource])
                        
                        raise ValueError(error_message.format(
                            *error_message_bindings))
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
                            revname, revhandle['id'], fwdpath, revpath, intpath, None, None, None)
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

    def get_fq_stats(self, reads_object, file_path):
        eautils = kb_ea_utils(self.callback_url)
        ea_stats_dict = eautils.calculate_fastq_stats(
            {'read_library_path': file_path})
        for key in ea_stats_dict:
            reads_object[key] = ea_stats_dict[key]
        return reads_object

    def _get_staging_file_path(self, token_user, staging_file_subdir_path):
        """
        _get_staging_file_path: return staging area file path

        directory pattern: /data/bulk/user_name/file_name

        """
        return self.STAGING_FILE_PREFIX + token_user + '/' + staging_file_subdir_path

    def _download_staging_file(self, token_user, staging_file_subdir_path):
        """
        _download_staging_file: download staging file to scratch

        return: file path of downloaded staging file

        """
        staging_file_name = staging_file_subdir_path.rpartition('/')[-1]
        staging_file_path = self._get_staging_file_path(
            token_user, staging_file_subdir_path)

        self.log('Start downloading staging file: %s' % staging_file_path)
        dstdir = os.path.join(self.scratch, 'tmp')
        if not os.path.exists(dstdir):
            os.makedirs(dstdir)
        shutil.copy2(staging_file_path, dstdir)
        copy_file_path = os.path.join(dstdir, staging_file_name)
        self.log('Copied staging file from %s to %s' %
                 (staging_file_path, copy_file_path))

        return copy_file_path

    def _download_web_file(self, file_url, download_type, rev_file=False):
        """
        _download_web_file: download reads source file from web

        file_url: file URL
        download_type: one of ['Direct Download', 'FTP', 'DropBox', 'Google Drive']
        rev_file: optional, default as False. Set to True if file_url is for rev_file

        return: file path of downloaded web file

        """

        # prepare local copy file path for copy
        self.log('Start downloading web file from: %s' % file_url)
        tmp_file_name = 'tmp_rev_fastq.fastq' if rev_file else 'tmp_fwd_fastq.fastq'
        dstdir = os.path.join(self.scratch, 'tmp')
        if not os.path.exists(dstdir):
            os.makedirs(dstdir)
        copy_file_path = os.path.join(dstdir, tmp_file_name)

        self._download_file(download_type, file_url, copy_file_path)
        self.log('Copied web file to %s' % copy_file_path)

        return copy_file_path

    def _download_file(self, download_type, file_url, copy_file_path):
        """
        _download_file: download execution distributor

        params:
        download_type: download type for web source file
        file_url: file URL
        copy_file_path: output file saving path

        """
        if download_type == 'Direct Download':
            self._download_direct_download_link(file_url, copy_file_path)
        elif download_type == 'DropBox':
            self._download_dropbox_link(file_url, copy_file_path)
        elif download_type == 'FTP':
            self._download_ftp_link(file_url, copy_file_path)
        elif download_type == 'Google Drive':
            self._download_google_drive_link(file_url, copy_file_path)
        else:
            raise ValueError('Invalid download type: %s' % download_type)

    def _download_direct_download_link(self, file_url, copy_file_path):
        """
        _download_direct_download_link: direct download link handler 

        params:
        file_url: direct download URL
        copy_file_path: output file saving path

        """

        self.log('Connecting and downloading web source: %s' % file_url)
        try:
            online_file = urllib2.urlopen(file_url)
        except urllib2.HTTPError as e:
            raise ValueError(
                "The server error\nURL: %s\nError code: %s" % (file_url, e.code))
        except urllib2.URLError as e:
            raise ValueError("Failed to reach URL: %s\nReason: %s" % (file_url, e.reason))
        else:
            with closing(online_file):
                with open(copy_file_path, 'wb') as output:
                    shutil.copyfileobj(online_file, output)
            # check first 5 lines of file content
            with open(copy_file_path) as copied_file:
                for line in islice(copied_file, 5):
                    if line.lower().find('html') != -1:
                        raise ValueError("Undownable File.\n" + 
                            "Please make sure file is publicly accessible\n" +
                            "File URL: %s" % file_url)

            self.log('Downloaded file to %s' % copy_file_path)

    def _download_dropbox_link(self, file_url, copy_file_path):
        """
        _download_dropbox_link: dropbox download link handler
                                file needs to be shared publicly 

        params:
        file_url: dropbox download link
        copy_file_path: output file saving path

        """
        # translate dropbox URL for direct download
        if "?" not in file_url:
            force_download_link = file_url + '?raw=1'
        else:
            force_download_link = file_url.partition('?')[0] + '?raw=1'

        self.log('Generating DropBox direct download link\n from: %s\n to: %s' % (
            file_url, force_download_link))
        self._download_direct_download_link(
            force_download_link, copy_file_path)

    def _download_ftp_link(self, file_url, copy_file_path):
        """
        _download_ftp_link: FTP download link handler
                            URL fomat: ftp://anonymous:email@ftp_link 
                                    or ftp://ftp_link
                            defualt user_name: 'anonymous'
                                    password: 'anonymous@domain.com'

                            Note: Currenlty we only support anonymous FTP due to securty reasons.

        params:
        file_url: FTP download link
        copy_file_path: output file saving path

        """
        self.log('Connecting FTP link: %s' % file_url)
        ftp_url_format = re.match(r'ftp://.*:.*@.*/.*', file_url)
        # process ftp credentials
        if ftp_url_format:
            self.ftp_user_name = re.search('ftp://(.+?):', file_url).group(1)
            if self.ftp_user_name.lower() != 'anonymous':
                raise ValueError("Currently we only support anonymous FTP")
            self.ftp_password = file_url.rpartition('@')[0].rpartition(':')[-1]
            self.ftp_domain = re.search(
                'ftp://.*:.*@(.+?)/', file_url).group(1)
            self.ftp_file_path = file_url.partition(
                'ftp://')[-1].partition('/')[-1].rpartition('/')[0]
            self.ftp_file_name = re.search(
                'ftp://.*:.*@.*/(.+$)', file_url).group(1)
        else:
            self.log('Setting anonymous FTP user_name and password')
            self.ftp_user_name = 'anonymous'
            self.ftp_password = 'anonymous@domain.com'
            self.ftp_domain = re.search('ftp://(.+?)/', file_url).group(1)
            self.ftp_file_path = file_url.partition(
                'ftp://')[-1].partition('/')[-1].rpartition('/')[0]
            self.ftp_file_name = re.search('ftp://.*/(.+$)', file_url).group(1)

        self._check_ftp_connection(self.ftp_user_name, self.ftp_password,
                                   self.ftp_domain, self.ftp_file_path, self.ftp_file_name)

        ftp_connection = ftplib.FTP(self.ftp_domain)
        ftp_connection.login(self.ftp_user_name, self.ftp_password)
        ftp_connection.cwd(self.ftp_file_path)

        ftp_copy_file_path = copy_file_path + \
            '.gz' if self.ftp_file_name.endswith('.gz') else copy_file_path
        with open(ftp_copy_file_path, 'wb') as output:
            ftp_connection.retrbinary('RETR %s' %
                                      self.ftp_file_name, output.write)
        self.log('Copied FTP file to: %s' % ftp_copy_file_path)

        if self.ftp_file_name.endswith('.gz'):
            self._unpack_gz_file(copy_file_path)

    def _unpack_gz_file(self, copy_file_path):
        with gzip.open(copy_file_path + '.gz', 'rb') as in_file:
            with open(copy_file_path, 'w') as f:
                f.write(in_file.read())
        self.log('Unzipped file: %s' % copy_file_path + '.gz')

    def _check_ftp_connection(self, user_name, password, domain, file_path, file_name):
        """
        _check_ftp_connection: ftp connection checker

        params:
        user_name: FTP user name
        password: FTP user password
        domain: FTP domain
        file_path: target file directory
        file_name: target file name 

        """

        try:
            ftp = ftplib.FTP(domain)
        except ftplib.all_errors, error:
            raise ValueError("Cannot connect: %s" % error)
        else:
            try:
                ftp.login(user_name, password)
            except ftplib.all_errors, error:
                raise ValueError("Cannot login: %s" % error)
            else:
                ftp.cwd(file_path)
                if file_name in ftp.nlst():
                    pass
                else:
                    raise ValueError("File %s does NOT exist in FTP path: %s" % (
                        file_name, domain + '/' + file_path))

    def _download_google_drive_link(self, file_url, copy_file_path):
        """
        _download_google_drive_link: Google Drive download link handler
                                     file needs to be shared publicly 

        params:
        file_url: Google Drive download link
        copy_file_path: output file saving path

        """
        # translate Google Drive URL for direct download
        force_download_link_prefix = 'https://drive.google.com/uc?export=download&id='
        if file_url.find('drive.google.com/file/d/') != -1:
            file_id = file_url.partition('/d/')[-1].partition('/')[0]
        elif file_url.find('drive.google.com/open?id=') != -1:
            file_id = file_url.partition('id=')[-1]
        else:
            raise ValueError("Unexpected Google Drive share link.\n" +
                            "URL: %s" % file_url)
        force_download_link = force_download_link_prefix + file_id

        self.log('Generating Google Drive direct download link\n from: %s\n to: %s' % (
            file_url, force_download_link))
        self._download_direct_download_link(
            force_download_link, copy_file_path)

    def _process_download(self, fwd, rev, reads_source, download_type, user_id):
        """
        _process_download: processing different type of downloads

        fwd: forward shock_id if reads_source is 'shock'
               forward url if reads_source is 'web'
               forward file subdirectory path in staging if reads_source is 'staging'
        rev: reverse shock_id if reads_source is 'shock'
               reverse url if reads_source is 'web'
               reverse file subdirectory path in staging if reads_source is 'staging'
        reads_source: one of 'shock', 'web' or 'staging'
        download_type: one of ['Direct Download', 'FTP', 'DropBox', 'Google Drive']
        user_id: current token user
        """

        # return values
        fwdname = None
        revname = None
        revpath = None

        if reads_source == 'shock':
            # Grab files from Shock
            dfu = DataFileUtil(self.callback_url)
            fileinput = [{'shock_id': fwd,
                          'file_path': self.scratch + '/fwd/',
                          'unpack': 'uncompress'}]
            if rev:
                fileinput.append({'shock_id': rev,
                                  'file_path': self.scratch + '/rev/',
                                  'unpack': 'uncompress'})
            self.log('downloading reads file(s) from Shock')
            files = dfu.shock_to_file_mass(fileinput)
            fwdpath = files[0]["file_path"]
            fwdname = files[0]["node_file_name"]
            if rev:
                revpath = files[1]["file_path"]
                revname = files[1]["node_file_name"]
        elif reads_source == 'web':
            # TODO: Tian move _download_web_file to DFU
            fwdpath = self._download_web_file(fwd, download_type)
            revpath = self._download_web_file(
                rev, download_type, rev_file=True) if rev else None
        elif reads_source == 'staging':
            # TODO: Tian move _download_staging_file to DFU
            fwdpath = self._download_staging_file(user_id, fwd)
            revpath = self._download_staging_file(
                user_id, rev) if rev else None
        elif reads_source == 'local':
            fwdpath = fwd
            revpath = rev
        else:
            raise ValueError(
                "Unexpected reads_source value. reads_source: %s" % reads_source)

        returnVal = {'fwdpath': fwdpath,
                     'revpath': revpath,
                     'fwdname': fwdname,
                     'revname': revname}

        return returnVal

    def _generate_validation_error_message(self, reads_source, actualpath, file_info):
        fwdpath = file_info.get('fwdpath')
        revpath = file_info.get('revpath')
        fwdname = file_info.get('fwdname')
        revname = file_info.get('revname')
        fwdsource = file_info.get('fwdsource')
        revsource = file_info.get('revsource')

        validation_error_message = "Invalid FASTQ file - Path: " + actualpath + "."
        if reads_source == 'shock':
            if revsource:
                validation_error_message += (
                    " Input Shock IDs - FWD Shock ID : " +
                    fwdsource + ", REV Shock ID : " + revsource +
                    ". FWD File Name : " + fwdname +
                    ". REV File Name : " + revname +
                    ". FWD Path : " + fwdpath +
                    ". REV Path : " + revpath + ".")
            else:
                validation_error_message += (" Input Shock ID : " +
                                             fwdsource + ". File Name : " + fwdname + ".")
        elif reads_source == 'web':
            if revsource:
                validation_error_message += (" Input URLs - FWD URL : " +
                                             fwdsource + ", REV URL : " + revsource +
                                             ". FWD Path : " + fwdpath +
                                             ". REV Path : " + revpath + ".")
            else:
                validation_error_message += (" Input URL : " + fwdsource + ".")
        elif reads_source == 'staging':
            if revsource:
                validation_error_message += (" Input Staging files - FWD Staging file : " +
                                             fwdsource +
                                             ", REV Staging file : " +
                                             revsource +
                                             ". FWD Path : " + fwdpath +
                                             ". REV Path : " + revpath + ".")
            else:
                validation_error_message += (" Input Staging : " +
                                             fwdsource + ".")
        elif reads_source == 'local':
            if revpath:
                validation_error_message += (" Input Files Paths - FWD Path : " +
                                             fwdpath + ", REV Path : " + revpath + ".")
        else:
            raise ValueError(
                "Unexpected reads_source value. reads_source: %s" % reads_source)

        return validation_error_message

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
           If web files are specified for upload, a download type one of
           ['Direct Download', 'DropBox', 'FTP', 'Google Drive'] must be
           specified too. The downloadable file must be uncompressed (except
           for FTP, .gz file is acceptable). If staging files are specified
           for upload, the staging file must be uncompressed and must be
           accessible by current user. Note that if a reverse read file is
           specified, it must be a local file if the forward reads file is a
           local file, or a shock id if not. If a reverse web file or staging
           file is specified, the reverse file category must match the
           forward file category. If a reverse file is specified the uploader
           will will automatically intereave the forward and reverse files
           and store that in shock. Additionally the statistics generated are
           on the resulting interleaved file. Required parameters: fwd_id -
           the id of the shock node containing the reads data file: either
           single end reads, forward/left reads, or interleaved reads. - OR -
           fwd_file - a local path to the reads data file: either single end
           reads, forward/left reads, or interleaved reads. - OR -
           fwd_file_url - a download link that contains reads data file:
           either single end reads, forward/left reads, or interleaved reads.
           download_type - download type ['Direct Download', 'FTP',
           'DropBox', 'Google Drive'] - OR - fwd_staging_file_name - reads
           data file name/ subdirectory path in staging area: either single
           end reads, forward/left reads, or interleaved reads.
           sequencing_tech - the sequencing technology used to produce the
           reads. (If source_reads_ref is specified then sequencing_tech must
           not be specified) One of: wsid - the id of the workspace where the
           reads will be saved (preferred). wsname - the name of the
           workspace where the reads will be saved. One of: objid - the id of
           the workspace object to save over name - the name to which the
           workspace object will be saved Optional parameters: rev_id - the
           shock node id containing the reverse/right reads for paired end,
           non-interleaved reads. - OR - rev_file - a local path to the reads
           data file containing the reverse/right reads for paired end,
           non-interleaved reads, note the reverse file will get interleaved
           with the forward file. - OR - rev_file_url - a download link that
           contains reads data file: reverse/right reads for paired end,
           non-interleaved reads. - OR - rev_staging_file_name - reads data
           file name in staging area: reverse/right reads for paired end,
           non-interleaved reads. single_genome - whether the reads are from
           a single genome or a metagenome. Default is single genome. strain
           - information about the organism strain that was sequenced. source
           - information about the organism source. interleaved - specify
           that the fwd reads file is an interleaved paired end reads file as
           opposed to a single end reads file. Default true, ignored if
           rev_id is specified. read_orientation_outward - whether the read
           orientation is outward from the set of primers. Default is false
           and is ignored for single end reads. insert_size_mean - the mean
           size of the genetic fragments. Ignored for single end reads.
           insert_size_std_dev - the standard deviation of the size of the
           genetic fragments. Ignored for single end reads. source_reads_ref
           - A workspace reference to a source reads object. This is used to
           propogate user defined info from the source reads object to the
           new reads object (used for filtering or trimming services). Note
           this causes a passed in insert_size_mean, insert_size_std_dev,
           sequencing_tech, read_orientation_outward, strain, source and/or
           single_genome to throw an error.) -> structure: parameter "fwd_id"
           of String, parameter "fwd_file" of String, parameter "wsid" of
           Long, parameter "wsname" of String, parameter "objid" of Long,
           parameter "name" of String, parameter "rev_id" of String,
           parameter "rev_file" of String, parameter "sequencing_tech" of
           String, parameter "single_genome" of type "boolean" (A boolean - 0
           for false, 1 for true. @range (0, 1)), parameter "strain" of type
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
           Double, parameter "insert_size_std_dev" of Double, parameter
           "source_reads_ref" of String, parameter "fwd_file_url" of String,
           parameter "rev_file_url" of String, parameter
           "fwd_staging_file_name" of String, parameter
           "rev_staging_file_name" of String, parameter "download_type" of
           String
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
        o, wsid, name, objid, kbtype, single_end, fwdsource, revsource, reads_source = (
                                                    self._proc_upload_reads_params(params))
        # If reads_source == 'shock', fwdsource and revsource are shock nodes
        # If reads_source == 'web', fwdsource and revsource are urls
        # If reads_source == 'staging', fwdsource and revsource are file name/subdirectory 
        #                               in staging area
        # If reads_source == 'local', fwdsource and revsource are file paths
        dfu = DataFileUtil(self.callback_url)
        fwdname, revname, fwdid, revid = (None,) * 4
        ret = self._process_download(fwdsource, revsource, reads_source,
                                     params.get('download_type'), ctx['user_id'])

        fwdpath = ret.get('fwdpath')
        revpath = ret.get('revpath')

        if reads_source == 'shock':
            fwdname = ret.get('fwdname')
            revname = ret.get('revname')
            fwdid = fwdsource
            revid = revsource

        actualpath = fwdpath
        if revpath:
            # now interleave the files
            actualpath = os.path.join(
                self.scratch, self.get_file_prefix() + '.inter.fastq')
            self.interleave(None, None, fwdname, fwdid,
                            revname, revid, fwdpath, revpath, actualpath, 
                            reads_source, fwdsource, revsource)

        interleaved = 1 if not single_end else 0
        file_valid = self.validateFASTQ({}, [{'file_path': actualpath,
                                              'interleaved': interleaved}])

        if not file_valid[0][0]['validated']:
            file_info = ret
            file_info['fwdsource'] = fwdsource
            file_info['revsource'] = revsource
            validation_error_message = self._generate_validation_error_message(
                reads_source, actualpath, file_info)
            raise ValueError(validation_error_message)

        self.log('validation complete, uploading files to shock')

        uploadedfile = dfu.file_to_shock({'file_path': actualpath,
                                          'make_handle': 1,
                                          'pack': 'gzip'})
        fhandle = uploadedfile['handle']
        fsize = uploadedfile['size']

        # calculate the stats for file.
        o = self.get_fq_stats(o, actualpath)

        fwdfile = {'file': fhandle,
                   'encoding': 'ascii',
                   'size': fsize,
                   'type': 'fq'
                   }
        if single_end:
            o['lib'] = fwdfile
        else:
            o['lib1'] = fwdfile

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
           sequencing parameter defining the expected read length. For paired
           end reads, this is the expected length of the total of the two
           reads. null if unavailable. float gc_content - the GC content of
           the reads. null if unavailable. int total_bases - The total number
           of bases in all the reads float read_length_mean - The mean read
           length. null if unavailable. float read_length_stdev - The std dev
           of read length. null if unavailable. string phred_type - Phred
           type: 33 or 64. null if unavailable. int number_of_duplicates -
           Number of duplicate reads. null if unavailable. float qual_min -
           Minimum Quality Score. null if unavailable. float qual_max -
           Maximum Quality Score. null if unavailable. float qual_mean - Mean
           Quality Score. null if unavailable. float qual_stdev - Std dev of
           Quality Scores. null if unavailable. mapping<string, float>
           base_percentages - percentage of total bases being a particular
           nucleotide.  Null if unavailable.) -> structure: parameter "files"
           of type "ReadsFiles" (Reads file information. Note that the file
           names provided are those *prior to* interleaving or deinterleaving
           the reads. string fwd - the path to the forward / left reads.
           string fwd_name - the name of the forwards reads file from Shock,
           or if not available, from the Shock handle. string rev - the path
           to the reverse / right reads. null if the reads are single end or
           interleaved. string rev_name - the name of the reverse reads file
           from Shock, or if not available, from the Shock handle. null if
           the reads are single end or interleaved. string otype - the
           original type of the reads. One of 'single', 'paired', or
           'interleaved'. string type - one of 'single', 'paired', or
           'interleaved'.) -> structure: parameter "fwd" of String, parameter
           "fwd_name" of String, parameter "rev" of String, parameter
           "rev_name" of String, parameter "otype" of String, parameter
           "type" of String, parameter "ref" of String, parameter
           "single_genome" of type "tern" (A ternary. Allowed values are
           'false', 'true', or null. Any other value is invalid.), parameter
           "read_orientation_outward" of type "tern" (A ternary. Allowed
           values are 'false', 'true', or null. Any other value is invalid.),
           parameter "sequencing_tech" of String, parameter "strain" of type
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
           external), parameter "insert_size_mean" of Double, parameter
           "insert_size_std_dev" of Double, parameter "read_count" of Long,
           parameter "read_size" of Long, parameter "gc_content" of Double,
           parameter "total_bases" of Long, parameter "read_length_mean" of
           Double, parameter "read_length_stdev" of Double, parameter
           "phred_type" of String, parameter "number_of_duplicates" of Long,
           parameter "qual_min" of Double, parameter "qual_max" of Double,
           parameter "qual_mean" of Double, parameter "qual_stdev" of Double,
           parameter "base_percentages" of mapping from String to Double
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
