import unittest
import time

from os import environ
import shutil
import os
from DataFileUtil.DataFileUtilClient import DataFileUtil
import requests
from pprint import pprint
import subprocess
import hashlib
import inspect
import tempfile
from zipfile import ZipFile
try:
    from ConfigParser import ConfigParser  # py2 @UnusedImport
except:
    from configparser import ConfigParser  # py3 @UnresolvedImport @Reimport

from Workspace.WorkspaceClient import Workspace
from Workspace.baseclient import ServerError as WorkspaceError
from biokbase.AbstractHandle.Client import AbstractHandle as HandleService
from DataFileUtil.baseclient import ServerError as DFUError
from ReadsUtils.ReadsUtilsImpl import ReadsUtils
from ReadsUtils.ReadsUtilsServer import MethodContext


class TestError(Exception):
    pass


def dictmerge(x, y):
    z = x.copy()
    z.update(y)
    return z


class ReadsUtilsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = environ.get('KB_AUTH_TOKEN', None)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': cls.token,
                        'provenance': [
                            {'service': 'ReadsUtils',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('ReadsUtils'):
            cls.cfg[nameval[0]] = nameval[1]
        cls.shockURL = cls.cfg['shock-url']
        cls.ws = Workspace(cls.cfg['workspace-url'], token=cls.token)
        cls.hs = HandleService(url=cls.cfg['handle-service-url'],
                               token=cls.token)
        cls.impl = ReadsUtils(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        shutil.rmtree(cls.scratch)
        os.mkdir(cls.scratch)
        suffix = int(time.time() * 1000)
        wsName = "test_ReadsUtils_" + str(suffix)
        cls.ws_info = cls.ws.create_workspace({'workspace': wsName})
        cls.dfu = DataFileUtil(os.environ['SDK_CALLBACK_URL'], token=cls.token)
        cls.staged = {}
        cls.nodes_to_delete = []
        cls.handles_to_delete = []
        cls.setupTestData()
        print('\n\n=============== Starting tests ==================')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'ws_info'):
            cls.ws.delete_workspace({'id': cls.ws_info[0]})
            print('Deleted test workspace: '.format(cls.ws_info[0]))
        if hasattr(cls, 'nodes_to_delete'):
            for node in cls.nodes_to_delete:
                cls.delete_shock_node(node)
        if hasattr(cls, 'handles_to_delete'):
            cls.hs.delete_handles(cls.hs.ids_to_handles(cls.handles_to_delete))
            print('Deleted handles ' + str(cls.handles_to_delete))

    @classmethod
    def getWsName(cls):
        return cls.ws_info[1]

    @classmethod
    def delete_shock_node(cls, node_id):
        header = {'Authorization': 'Oauth {0}'.format(cls.token)}
        requests.delete(cls.shockURL + '/node/' + node_id, headers=header,
                        allow_redirects=True)
        print('Deleted shock node ' + node_id)

    @classmethod
    def upload_file_to_shock(cls, file_path):
        """
        Use HTTP multi-part POST to save a file to a SHOCK instance.
        """

        header = dict()
        header["Authorization"] = "Oauth {0}".format(cls.token)

        if file_path is None:
            raise Exception("No file given for upload to SHOCK!")

        with open(os.path.abspath(file_path), 'rb') as dataFile:
            files = {'upload': dataFile}
            print('POSTing data')
            response = requests.post(
                cls.shockURL + '/node', headers=header, files=files,
                stream=True, allow_redirects=True)
            print('got response')

        if not response.ok:
            response.raise_for_status()

        result = response.json()

        if result['error']:
            raise Exception(result['error'][0])
        else:
            return result["data"]

    @classmethod
    def upload_file_to_shock_and_get_handle(cls, test_file):
        '''
        Uploads the file in test_file to shock and returns the node and a
        handle to the node.
        '''
        print('loading file to shock: ' + test_file)
        node = cls.upload_file_to_shock(test_file)
        pprint(node)
        cls.nodes_to_delete.append(node['id'])

        print('creating handle for shock id ' + node['id'])
        handle_id = cls.hs.persist_handle({'id': node['id'],
                                           'type': 'shock',
                                           'url': cls.shockURL
                                           })
        cls.handles_to_delete.append(handle_id)

        md5 = node['file']['checksum']['md5']
        return node['id'], handle_id, md5, node['file']['size']

    @classmethod
    def upload_assembly(cls, wsobjname, object_body, fwd_reads,
                        rev_reads=None, kbase_assy=False, single_end=False):
        if single_end and rev_reads:
            raise ValueError('u r supr dum')

        print('\n===============staging data for object ' + wsobjname +
              '================')
        print('uploading forward reads file ' + fwd_reads['file'])
        fwd_id, fwd_handle_id, fwd_md5, fwd_size = \
            cls.upload_file_to_shock_and_get_handle(fwd_reads['file'])
        fwd_handle = {
                      'hid': fwd_handle_id,
                      'file_name': fwd_reads['name'],
                      'id': fwd_id,
                      'url': cls.shockURL,
                      'type': 'shock',
                      'remote_md5': fwd_md5
                      }

        ob = dict(object_body)  # copy
        if kbase_assy:
            if single_end:
                wstype = 'KBaseAssembly.SingleEndLibrary'
                ob['handle'] = fwd_handle
            else:
                wstype = 'KBaseAssembly.PairedEndLibrary'
                ob['handle_1'] = fwd_handle
        else:
            if single_end:
                wstype = 'KBaseFile.SingleEndLibrary'
                obkey = 'lib'
            else:
                wstype = 'KBaseFile.PairedEndLibrary'
                obkey = 'lib1'
            ob[obkey] = \
                {'file': fwd_handle,
                 'encoding': 'UTF8',
                 'type': fwd_reads['type'],
                 'size': fwd_size
                 }

        rev_id = None
        rev_handle = None
        if rev_reads:
            print('uploading reverse reads file ' + rev_reads['file'])
            rev_id, rev_handle_id, rev_md5, rev_size = \
                cls.upload_file_to_shock_and_get_handle(rev_reads['file'])
            rev_handle = {
                          'hid': rev_handle_id,
                          'file_name': rev_reads['name'],
                          'id': rev_id,
                          'url': cls.shockURL,
                          'type': 'shock',
                          'remote_md5': rev_md5
                          }
            if kbase_assy:
                ob['handle_2'] = rev_handle
            else:
                ob['lib2'] = \
                    {'file': rev_handle,
                     'encoding': 'UTF8',
                     'type': rev_reads['type'],
                     'size': rev_size
                     }

        print('Saving object data')
        objdata = cls.save_ws_obj(ob, wsobjname, wstype)
        print('Saved object: ')
        pprint(objdata)
        pprint(ob)
        cls.staged[wsobjname] = {'info': objdata,
                                 'ref': cls.make_ref(objdata),
                                 'fwd_node_id': fwd_id,
                                 'rev_node_id': rev_id,
                                 'fwd_handle': fwd_handle,
                                 'rev_handle': rev_handle,
                                 }

    @classmethod
    def upload_file_ref(cls, wsobjname, file_):
        fwd_id, fwd_handle_id, fwd_md5, fwd_size = \
            cls.upload_file_to_shock_and_get_handle(file_)
        ob = {'file': {'hid': fwd_handle_id,
                       'file_name': file_,
                       'id': fwd_id,
                       'url': cls.shockURL,
                       'type': 'shock',
                       'remote_md5': fwd_md5
                       },
              'encoding': 'UTF8',
              'type': 'stuff',
              'size': fwd_size
              }
        info = cls.save_ws_obj(ob, wsobjname, 'KBaseFile.FileRef')
        cls.staged[wsobjname] = {'info': info,
                                 'ref': cls.make_ref(info)}

    @classmethod
    def upload_empty_data(cls, wsobjname):
        info = cls.save_ws_obj({}, wsobjname, 'Empty.AType')
        cls.staged[wsobjname] = {'info': info,
                                 'ref': cls.make_ref(info)}

    @classmethod
    def save_ws_obj(cls, obj, objname, objtype):
        return cls.ws.save_objects({
            'workspace': cls.getWsName(),
            'objects': [{'type': objtype,
                         'data': obj,
                         'name': objname
                         }]
            })[0]

    @classmethod
    def gzip(cls, *files):
        for f in files:
            if subprocess.call(['gzip', '-f', '-k', f]):
                raise TestError(
                    'Error zipping file {}'.format(f))

    @classmethod
    def setupTestData(cls):
        print('Shock url ' + cls.shockURL)
        print('WS url ' + cls.ws._client.url)
        print('Handle service url ' + cls.hs.url)
        print('staging data')
        sq = {'sequencing_tech': 'fake data'}
        cls.gzip('data/small.forward.fq', 'data/small.reverse.fq',
                 'data/interleaved.fq')
        # get file type from type
        fwd_reads = {'file': 'data/small.forward.fq',
                     'name': 'test_fwd.fastq',
                     'type': 'fastq'}
        fwd_reads2 = {'file': 'data/small.forward.fq',
                      'name': 'test_fwd.fnq',
                      'type': 'fnq.gz'}
        fwd_reads_gz = {'file': 'data/small.forward.fq.gz',
                        'name': 'test_fwd.fastq.gz',
                        'type': '.fastq.Gz'}
        # get file type from handle file name
        rev_reads = {'file': 'data/small.reverse.fq',
                     'name': 'test_rev.FQ',
                     'type': ''}
        rev_reads_gz = {'file': 'data/small.reverse.fq.gz',
                        'name': 'test_rev.FQ.gZ',
                        'type': ''}
        # get file type from shock node file name
        int_reads = {'file': 'data/interleaved.fq',
                     'name': '',
                     'type': ''}
        int_reads_gz = {'file': 'data/interleaved.fq.gz',
                        'name': '',
                        'type': ''}
        # happy path objects
        # load KBF.P int, KBF.P fr, KBF.S KBA.P int, KBA.P fr, KBA.S
        # w/wo gz
        cls.upload_assembly('frbasic', sq, fwd_reads, rev_reads=rev_reads)
        cls.upload_assembly('frbasic_gz', sq, fwd_reads_gz,
                            rev_reads=rev_reads)
        cls.upload_assembly('intbasic', sq, int_reads)
        cls.upload_assembly('intbasic_gz', sq, int_reads_gz)
        cls.upload_assembly('frbasic_kbassy', {}, fwd_reads2,
                            rev_reads=rev_reads, kbase_assy=True)
        cls.upload_assembly('frbasic_kbassy_gz', {}, fwd_reads,
                            rev_reads=rev_reads_gz, kbase_assy=True)
        cls.upload_assembly('intbasic_kbassy', {}, int_reads, kbase_assy=True)
        cls.upload_assembly('intbasic_kbassy_gz', {}, int_reads_gz,
                            kbase_assy=True)
        cls.upload_assembly('single_end', sq, fwd_reads, single_end=True)
        cls.upload_assembly('single_end_gz', sq, fwd_reads_gz, single_end=True)
        cls.upload_assembly('single_end_kbassy', {}, rev_reads,
                            single_end=True, kbase_assy=True)
        cls.upload_assembly('single_end_kbassy_gz', {}, rev_reads_gz,
                            single_end=True, kbase_assy=True)

        # load objects with optional fields
        cls.upload_assembly(
            'kbassy_roo_t',
            {'insert_size_mean': 42,
             'insert_size_std_dev': 1000000,
             'read_orientation_outward': 1},
            fwd_reads, kbase_assy=True)
        cls.upload_assembly(
            'kbassy_roo_f',
            {'insert_size_mean': 43,
             'insert_size_std_dev': 1000001,
             'read_orientation_outward': 0},
            fwd_reads, kbase_assy=True)
        cls.upload_assembly(
            'kbfile_sing_sg_t',
            {'single_genome': 1,
             'strain': {'genus': 'Yersinia',
                        'species': 'pestis',
                        'strain': 'happypants'
                        },
             'source': {'source': 'my pants'},
             'sequencing_tech': 'IonTorrent',
             'read_count': 3,
             'read_size': 12,
             'gc_content': 2.3
             },
            fwd_reads, single_end=True)
        cls.upload_assembly(
            'kbfile_sing_sg_f',
            {'single_genome': 0,
             'strain': {'genus': 'Deinococcus',
                        'species': 'radiodurans',
                        'strain': 'radiopants'
                        },
             'source': {'source': 'also my pants'},
             'sequencing_tech': 'PacBio CCS',
             'read_count': 4,
             'read_size': 13,
             'gc_content': 2.4
             },
            fwd_reads, single_end=True)
        cls.upload_assembly(
            'kbfile_pe_t',
            {'single_genome': 1,
             'read_orientation_outward': 1,
             'insert_size_mean': 50,
             'insert_size_std_dev': 1000002,
             'strain': {'genus': 'Bacillus',
                        'species': 'subtilis',
                        'strain': 'soilpants'
                        },
             'source': {'source': 'my other pants'},
             'sequencing_tech': 'Sanger',
             'read_count': 5,
             'read_size': 14,
             'gc_content': 2.5
             },
            fwd_reads)
        cls.upload_assembly(
            'kbfile_pe_f',
            {'single_genome': 0,
             'read_orientation_outward': 0,
             'insert_size_mean': 51,
             'insert_size_std_dev': 1000003,
             'strain': {'genus': 'Escheria',
                        'species': 'coli',
                        'strain': 'poopypants'
                        },
             'source': {'source': 'my ex-pants'},
             'sequencing_tech': 'PacBio CLR',
             'read_count': 6,
             'read_size': 15,
             'gc_content': 2.6
             },
            fwd_reads)

        # load bad data for unhappy path testing
        shutil.copy2('data/small.forward.fq', 'data/small.forward.bad')
        bad_fn_reads = {'file': 'data/small.forward.bad',
                        'name': '',
                        'type': ''}
        cls.upload_assembly('bad_shk_name', sq, bad_fn_reads)
        bad_fn_reads['file'] = 'data/small.forward.fq'
        bad_fn_reads['name'] = 'file.terrible'
        cls.upload_assembly('bad_file_name', sq, bad_fn_reads)
        bad_fn_reads['name'] = 'small.forward.fastq'
        bad_fn_reads['type'] = 'xls'
        cls.upload_assembly('bad_file_type', sq, bad_fn_reads)
#         cls.upload_assembly('no_file_info', sq,
#                             {'file': None, 'name': None, 'type': None})
        cls.upload_assembly('bad_node', sq, fwd_reads)
        cls.delete_shock_node(cls.nodes_to_delete.pop())
        cls.upload_empty_data('empty')
        cls.upload_file_ref('fileref', 'data/small.forward.fq')

        # file type testing
        # at this point the 3 basic filetypes + gz are staged
        cls.upload_assy_fileext('gzip', sq, 'fq.gzip', 'foo.FNQ.GZIP')
        cls.upload_assy_fileext('bz', sq, 'fastQ.bz', 'foo.fnq.BZ2')
        cls.upload_assy_fileext('bzip', sq, 'FQ.bzip', 'foo.FASTQ.BZIP2')
        # bad file type testing
        cls.upload_assy_fileext('bad_ext', sq, 'foo.gzip', 'foo.FNQ.GZIP')

        # interleave testing
        cls.upload_assy_with_file(
            'fr_blank_line', sq,
            'data/Sample5_noninterleaved.1.blank_lines.fastq',
            'data/Sample5_noninterleaved.2.fastq')
        cls.upload_assy_with_file(
            'fr_missing_line', sq,
            'data/Sample5_noninterleaved.1.missing_line.fastq',
            'data/Sample5_noninterleaved.2.fastq')
        cls.upload_assy_with_file(
            'fr_missing_rec_f', sq,
            'data/Sample5_noninterleaved.1.missing_rec.fastq',
            'data/Sample5_noninterleaved.2.fastq')
        cls.upload_assy_with_file(
            'fr_missing_rec_r', sq,
            'data/Sample5_noninterleaved.1.fastq',
            'data/Sample5_noninterleaved.2.missing_rec.fastq')

        # deinterleave testing
        cls.upload_assy_with_file(
            'int_blank_line', sq, 'data/Sample5_interleaved_blank_lines.fastq')
        cls.upload_assy_with_file(
            'int_miss_line', sq,
            'data/Sample5_interleaved_missing_line.fastq')

        print('Data staged.')

    @classmethod
    def upload_assy_with_file(cls, wsobjname, object_body, fwdfile,
                              revfile=None):
        fwd = {'file': fwdfile,
               'name': '',
               'type': None
               }
        rev = None
        if revfile:
            rev = {'file': revfile,
                   'name': None,
                   'type': ''
                   }
        cls.upload_assembly(wsobjname, object_body, fwd, rev)

    @classmethod
    def upload_assy_fileext(cls, wsobjname, object_body, file_type,
                            handle_file_name):
        cls.upload_assembly(
            wsobjname, object_body,
            {'file': 'data/small.forward.fq',
             'name': handle_file_name,
             'type': file_type
             }
        )

    @classmethod
    def make_ref(self, objinfo):
        return str(objinfo[6]) + '/' + str(objinfo[0]) + '/' + str(objinfo[4])

    def md5(self, filename):
        with open(filename, 'rb') as file_:
            hash_md5 = hashlib.md5()
            buf = file_.read(65536)
            while len(buf) > 0:
                hash_md5.update(buf)
                buf = file_.read(65536)
            return hash_md5.hexdigest()

    # MD5s not repeatable if the same file is gzipped again
    MD5_SM_F = 'e7dcea3e40d73ca0f71d11b044f30ded'
    MD5_SM_R = '2cf41e49cd6b9fdcf1e511b083bb42b5'
    MD5_SM_I = '6271cd02987c9d1c4bdc1733878fe9cf'
    MD5_FR_TO_I = '1c58d7d59c656db39cedcb431376514b'
    MD5_FR_TO_I_BLANK = '971a5f445055c85fd45b17459e15e3ed'
    MD5_I_TO_F = '4a5f4c05aae26dcb288c0faec6583946'
    MD5_I_TO_R = '2be8de9afa4bcd1f437f35891363800a'
    MD5_I_BLANK_TO_F = '140a61c7f183dd6a2b93ef195bb3ec63'
    MD5_I_BLANK_TO_R = 'a5c6dc77baf9b245ad61a1053864ef88'

    STD_OBJ_KBF_P = {'gc_content': None,
                     'insert_size_mean': None,
                     'insert_size_std_dev': None,
                     'read_count': None,
                     'read_orientation_outward': 'false',
                     'read_size': None,
                     'sequencing_tech': u'fake data',
                     'single_genome': 'true',
                     'source': None,
                     'strain': None
                     }
    STD_OBJ_KBF_S = dictmerge(STD_OBJ_KBF_P,
                              {'read_orientation_outward': None})

    STD_OBJ_KBA = dictmerge(
        STD_OBJ_KBF_P,
        {'read_orientation_outward': None,
         'sequencing_tech': None,
         'single_genome': None
         })

    # FASTA/Q tests ########################################################

    def check_FASTA(self, filename, result):
        self.assertEqual(
            self.impl.validateFASTA(
                self.ctx, {'file_path': filename})[0]['valid'], result)

    def test_FASTA_validation(self):
        self.check_FASTA('data/sample.fa', 1)
        self.check_FASTA('data/sample.fas', 1)
        self.check_FASTA('data/sample.fna', 1)
        self.check_FASTA('data/sample.fasta', 1)
        self.check_FASTA('data/sample_missing_data.fa', 0)

    def fail_val_FASTA(self, filename, error, exception=ValueError):
        with self.assertRaises(exception) as context:
            self.impl.validateFASTA(self.ctx, {'file_path': filename})
        self.assertEqual(error, str(context.exception.message))

    def fail_val_FASTQ(self, params, error, exception=ValueError):
        with self.assertRaises(exception) as context:
            self.impl.validateFASTQ(self.ctx, params)
        self.assertEqual(error, str(context.exception.message))

    def test_FASTA_val_fail_no_file(self):
        self.fail_val_FASTA('nofile', 'No such file: nofile')
        self.fail_val_FASTA(None, 'No such file: None')
        self.fail_val_FASTA('', 'No such file: ')

    def test_FASTA_val_fail_bad_ext(self):
        self.fail_val_FASTA('data/sample.txt',
                            'File data/sample.txt is not a FASTA file')

    def test_FASTQ_validation(self):
        self.check_fq('data/Sample1.fastq', 0, 1)
        self.check_fq('data/Sample2_interleaved_illumina.fnq', 1, 1)
        # fail on interleaved file specified as non-interleaved
        self.check_fq('data/Sample2_interleaved_illumina.fnq', 0, 0)
        self.check_fq('data/Sample3_interleaved_casava1.8.fq', 1, 1)
        self.check_fq('data/Sample4_interleaved_NCBI_SRA.fastq', 1, 1)
        self.check_fq('data/Sample5_interleaved.fastq', 1, 1)
        self.check_fq('data/Sample5_interleaved_blank_lines.fastq', 1, 1)
        self.check_fq('data/Sample5_noninterleaved.1.fastq', 0, 1)
        self.check_fq('data/Sample5_noninterleaved.2.fastq', 0, 1)
        self.check_fq('data/Sample1_invalid.fastq', 0, 0)
        self.check_fq('data/Sample5_interleaved_missing_line.fastq', 1, 0)

    def test_FASTQ_multiple(self):
        f1 = 'data/Sample1.fastq'
        f2 = 'data/Sample4_interleaved_NCBI_SRA.fastq'
        fn1 = os.path.basename(f1)
        fn2 = os.path.basename(f2)
        nfn1 = self.cfg['scratch'] + '/' + fn1
        nfn2 = self.cfg['scratch'] + '/' + fn2
        shutil.copyfile(f1, nfn1)
        shutil.copyfile(f2, nfn2)
        self.assertEqual(self.impl.validateFASTQ(
            self.ctx, [{'file_path': nfn1,
                       'interleaved': 0},
                       {'file_path': nfn2,
                       'interleaved': 1}
                       ])[0], [{'validated': 1}, {'validated': 1}])

    def check_fq(self, filepath, interleaved, ok):
        fn = os.path.basename(filepath)
        newfn = self.cfg['scratch'] + '/' + fn
        shutil.copyfile(filepath, newfn)
        self.assertEqual(self.impl.validateFASTQ(
            self.ctx, [{'file_path': newfn,
                       'interleaved': interleaved}])[0][0]['validated'], ok)
        for l in open(newfn):
            self.assertNotEqual(l, '')

    def test_FASTQ_val_fail_no_file(self):
        self.fail_val_FASTQ([{'file_path': 'nofile'}], 'No such file: nofile')
        self.fail_val_FASTQ([{'file_path': None}], 'No such file: None')
        self.fail_val_FASTQ([{'file_path': ''}], 'No such file: ')

    def test_FASTQ_val_fail_bad_ext(self):
        self.fail_val_FASTQ([{'file_path': 'data/sample.txt'}],
                            'File data/sample.txt is not a FASTQ file')

    # Upload tests ########################################################

    def test_single_end_reads_gzip(self):
        # gzip, minimum inputs
        ret = self.upload_file_to_shock('data/Sample1.fastq.gz')
        ref = self.impl.upload_reads(self.ctx, {'fwd_id': ret['id'],
                                                'sequencing_tech': 'seqtech',
                                                'wsname': self.ws_info[1],
                                                'name': 'singlereads1'})
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/singlereads1']})['data'][0]
        self.delete_shock_node(ret['id'])
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.SingleEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.check_lib(d['lib'], 2835, 'Sample1.fastq.gz', 'f118ee769a5e1b40ec44629994dfc3cd')

    def test_forward_reads_file(self):
        tf = 'Sample1.fastq'
        target = os.path.join(self.scratch, tf)
        shutil.copy('data/' + tf, target)
        ref = self.impl.upload_reads(
            self.ctx, {'fwd_file': target,
                       'sequencing_tech': 'seqtech',
                       'wsname': self.ws_info[1],
                       'name': 'filereads1'})
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/filereads1']})['data'][0]

        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.SingleEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.check_lib(d['lib'], 2835, 'Sample1.fastq.gz', 'f118ee769a5e1b40ec44629994dfc3cd')

    def test_single_end_reads_metagenome_objid(self):
        # single genome = 0, test saving to an object id
        ret = self.upload_file_to_shock('data/Sample5_noninterleaved.1.fastq')
        ref = self.impl.upload_reads(self.ctx, {'fwd_id': ret['id'],
                                                'sequencing_tech': 'seqtech2',
                                                'wsname': self.ws_info[1],
                                                'name': 'singlereads2',
                                                'single_genome': 0})
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/singlereads2']})['data'][0]
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.SingleEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech2')
        self.assertEqual(d['single_genome'], 0)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.check_lib(d['lib'], 604, 'Sample5_noninterleaved.1.fastq.gz',
                       '140a61c7f183dd6a2b93ef195bb3ec63')

        # test saving with IDs only
        ref = self.impl.upload_reads(
            self.ctx, {'fwd_id': ret['id'],
                       'sequencing_tech': 'seqtech2-1',
                       'wsid': self.ws_info[0],
                       'objid': obj['info'][0]})
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/singlereads2/2']})['data'][0]
        self.delete_shock_node(ret['id'])
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.SingleEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech2-1')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.check_lib(d['lib'], 604, 'Sample5_noninterleaved.1.fastq.gz',
                       '140a61c7f183dd6a2b93ef195bb3ec63')

    def test_single_end_reads_genome_source_strain(self):
        # specify single genome, source, strain, use workspace id
        ret = self.upload_file_to_shock('data/Sample1.fastq')
        strain = {'genus': 'Yersinia',
                  'species': 'pestis',
                  'strain': 'happypants'
                  }
        source = {'source': 'my pants'}
        ref = self.impl.upload_reads(
            self.ctx,
            {'fwd_id': ret['id'],
             'sequencing_tech': 'seqtech3',
             'wsid': self.ws_info[0],
             'name': 'singlereads3',
             'single_genome': 1,
             'strain': strain,
             'source': source,
             'interleaved': 0
             })
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/singlereads3']})['data'][0]

        self.delete_shock_node(ret['id'])
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.SingleEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech3')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual(d['source'], source)
        self.assertEqual(d['strain'], strain)
        self.assertEqual(d['read_count'], 50)
        self.assertEqual(d['read_size'], 2500)
        self.assertEqual(d['number_of_duplicates'], 0)
        self.assertEqual(d['base_percentages']['A'], 31.8286)
        self.assertEqual(d['base_percentages']['T'], 22.8571)
        self.assertEqual(d['base_percentages']['N'], 1.3143)
        self.assertEqual(d['base_percentages']['C'], 19.6571)
        self.assertEqual(d['base_percentages']['G'], 24.3429)
        self.assertEqual(d["phred_type"], "64")
        self.assertEqual(d["qual_mean"], 37.5537)
        self.assertEqual(d["qual_min"], 2)
        self.assertEqual(d["qual_max"], 40)
        self.assertEqual(d["qual_stdev"], 5.2006)
        self.assertEqual(d["gc_content"], 0.44)
        self.assertEqual(d["read_length_mean"], 50)
        self.assertEqual(d["read_length_stdev"], 0)
        self.check_lib(d['lib'], 2835, 'Sample1.fastq.gz', 'f118ee769a5e1b40ec44629994dfc3cd')

    def test_paired_end_reads(self):
        # paired end non interlaced, minimum inputs
        ret1 = self.upload_file_to_shock('data/small.forward.fq')
        ret2 = self.upload_file_to_shock('data/small.reverse.fq')
        ref = self.impl.upload_reads(
            self.ctx, {'fwd_id': ret1['id'],
                       'rev_id': ret2['id'],
                       'sequencing_tech': 'seqtech-pr1',
                       'wsname': self.ws_info[1],
                       'name': 'pairedreads1',
                       'interleaved': 0})
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/pairedreads1']})['data'][0]
        self.delete_shock_node(ret1['id'])
        self.delete_shock_node(ret2['id'])
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.PairedEndLibrary'), True)
        d = obj['data']
        file_name = d["lib1"]["file"]["file_name"]
        self.assertEqual(d['sequencing_tech'], 'seqtech-pr1')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.assertEqual(d['interleaved'], 1)
        self.assertEqual(d['read_orientation_outward'], 0)
        self.assertEqual(d['insert_size_mean'], None)
        self.assertEqual(d['insert_size_std_dev'], None)
        self.check_lib(d['lib1'], 2491520, file_name, '1c58d7d59c656db39cedcb431376514b')

    def test_paired_end_reads_file(self):
        # paired end non interlaced, minimum inputs
        fwdtf = 'small.forward.fq'
        revtf = 'small.reverse.fq'
        fwdtarget = os.path.join(self.scratch, fwdtf)
        revtarget = os.path.join(self.scratch, revtf)
        shutil.copy('data/' + fwdtf, fwdtarget)
        shutil.copy('data/' + revtf, revtarget)

        ref = self.impl.upload_reads(
            self.ctx, {'fwd_file': fwdtarget,
                       'rev_file': revtarget,
                       'sequencing_tech': 'seqtech-pr1',
                       'wsname': self.ws_info[1],
                       'name': 'pairedreadsfile1',
                       'interleaved': 0})
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/pairedreadsfile1']}
        )['data'][0]
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.PairedEndLibrary'), True)
        d = obj['data']
        file_name = d["lib1"]["file"]["file_name"]
        self.assertEqual(d['sequencing_tech'], 'seqtech-pr1')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.assertEqual(d['interleaved'], 1)
        self.assertEqual(d['read_orientation_outward'], 0)
        self.assertEqual(d['insert_size_mean'], None)
        self.assertEqual(d['insert_size_std_dev'], None)
        self.assertNotIn('lib2', d)
        self.assertEqual(d['read_count'], 25000)
        self.assertEqual(d['read_size'], 2500000)
        self.assertEqual(d['number_of_duplicates'], 792)
        self.assertEqual(d['base_percentages']['A'], 16.0727)
        self.assertEqual(d['base_percentages']['T'], 16)
        self.assertEqual(d['base_percentages']['N'], 0)
        self.assertEqual(d['base_percentages']['C'], 33.9538)
        self.assertEqual(d['base_percentages']['G'], 33.9735)
        self.assertEqual(d["phred_type"], "33")
        self.assertEqual(d["qual_mean"], 43.0493)
        self.assertEqual(d["qual_min"], 10)
        self.assertEqual(d["qual_max"], 51)
        self.assertEqual(d["qual_stdev"], 10.545)
        self.assertEqual(d["gc_content"], 0.679273)
        self.assertEqual(d["read_length_mean"], 100)
        self.assertEqual(d["read_length_stdev"], 0)

        self.check_lib(d['lib1'], 2491520, file_name, '1c58d7d59c656db39cedcb431376514b')

    def test_interleaved_with_pe_inputs(self):
        # paired end interlaced with the 4 pe input set
        ret = self.upload_file_to_shock('data/Sample5_interleaved.fastq')
        ref = self.impl.upload_reads(
            self.ctx, {'fwd_id': ret['id'],
                       'sequencing_tech': 'seqtech-pr2',
                       'wsname': self.ws_info[1],
                       'name': 'pairedreads2',
                       'interleaved': 1,
                       'read_orientation_outward': 'a',
                       'insert_size_mean': 72.1,
                       'insert_size_std_dev': 84.0
                       })
        obj = self.ws.get_objects2(
            {'objects': [{'ref': self.ws_info[1] + '/pairedreads2'}]}
            )['data'][0]
        self.delete_shock_node(ret['id'])
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.PairedEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech-pr2')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.assertEqual(d['interleaved'], 1)
        self.assertEqual(d['read_orientation_outward'], 1)
        self.assertEqual(d['insert_size_mean'], 72.1)
        self.assertEqual(d['insert_size_std_dev'], 84.0)
        self.assertNotIn('lib2', d)
        self.assertEqual(d['read_count'], 4)
        self.assertEqual(d['read_size'], 1004)
        self.assertEqual(d['number_of_duplicates'], 0)
        self.assertEqual(d['base_percentages']['A'], 20)
        self.assertEqual(d['base_percentages']['T'], 20)
        self.assertEqual(d['base_percentages']['N'], 0)
        self.assertEqual(d['base_percentages']['C'], 26.4286)
        self.assertEqual(d['base_percentages']['G'], 33.5714)
        self.assertEqual(d["phred_type"], "33")
        self.assertEqual(d["qual_mean"], 25.1143)
        self.assertEqual(d["qual_min"], 10)
        self.assertEqual(d["qual_max"], 40)
        self.assertEqual(d["qual_stdev"], 10.081)
        self.assertEqual(d["gc_content"], 0.6)
        self.assertEqual(d["read_length_mean"], 251)
        self.assertEqual(d["read_length_stdev"], 0)
        self.check_lib(d['lib1'], 1050, 'Sample5_interleaved.fastq.gz',
                       '971a5f445055c85fd45b17459e15e3ed')

    def check_lib(self, lib, size, filename, md5):
        shock_id = lib["file"]["id"]
        print "LIB: {}".format(str(lib))
        print "Shock ID: {}".format(str(shock_id))
        fileinput = [{'shock_id': shock_id,
                      'file_path': self.scratch + '/temp',
                      'unpack': 'uncompress'}]
        print "File Input: {}".format(str(fileinput))
        files = self.dfu.shock_to_file_mass(fileinput)
        path = files[0]["file_path"]
        file_md5 = hashlib.md5(open(path, 'rb').read()).hexdigest()
        libfile = lib['file']
        self.assertEqual(file_md5, md5)
        self.assertEqual(lib['size'], size)
        self.assertEqual(lib['type'], 'fq')
        self.assertEqual(lib['encoding'], 'ascii')

        self.assertEqual(libfile['file_name'], filename)
        self.assertEqual(libfile['hid'].startswith('KBH_'), True)

        self.assertEqual(libfile['type'], 'shock')
        self.assertEqual(libfile['url'], self.shockURL)

    def fail_upload_reads(self, params, error, exception=ValueError):
        with self.assertRaises(exception) as context:
            self.impl.upload_reads(self.ctx, params)
        self.assertEqual(error, str(context.exception.message))

    def test_upload_fail_no_reads(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'name': 'foo'
             },
            'Exactly one of a file or shock id containing a forwards reads ' +
            'file must be specified')

    def test_upload_fail_fwd_reads_spec_twice(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'name': 'foo',
             'fwd_id': 'whee',
             'fwd_file': 'whoo'
             },
            'Exactly one of a file or shock id containing a forwards reads ' +
            'file must be specified')

    def test_upload_fail_rev_reads_spec_twice(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'name': 'foo',
             'fwd_id': 'whoa',
             'rev_id': 'whee',
             'rev_file': 'whoo'
             },
            'Specified both a local file and a shock node for the reverse ' +
            'reads file')

    def test_upload_fail_spec_fwd_id_rev_file(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'name': 'foo',
             'fwd_id': 'whee',
             'rev_file': 'whoo'
             },
            'Cannot specify a local reverse reads file with a forward reads ' +
            'file in shock')

    def test_upload_fail_spec_fwd_file_rev_id(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'name': 'foo',
             'fwd_file': 'whee',
             'rev_id': 'whoo'
             },
            'Cannot specify a reverse reads file in shock with a local ' +
            'forward reads file')

    def test_upload_fail_no_seqtech(self):
        self.fail_upload_reads(
            {'fwd_id': 'foo',
             'wsname': self.ws_info[1],
             'name': 'foo'
             },
            'The sequencing technology must be provided')

    def test_upload_fail_no_ws(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'fwd_id': 'bar',
             'name': 'foo'
             },
            'Exactly one of the workspace ID or name must be provided')

    def test_upload_fail_no_obj_id(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'fwd_id': 'bar',
             'wsname': self.ws_info[1],
             },
            'Exactly one of the object ID or name must be provided')

    def test_upload_fail_non_existant_objid(self):
        ret = self.upload_file_to_shock('data/Sample1.fastq')
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': ret['id'],
             'objid': 1000000
             },
            'There is no object with id 1000000', exception=DFUError)
        self.delete_shock_node(ret['id'])

    def test_upload_fail_non_existant_shockid(self):
        ret = self.upload_file_to_shock('data/Sample1.fastq')
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': 'foo',
             'name': 'bar'
             },
            'Error downloading file from shock node foo: Node not found',
            exception=DFUError)
        self.delete_shock_node(ret['id'])

    def test_upload_fail_non_existant_file(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_file': 'foo',
             'name': 'bar'
             },
            'No such file: /kb/module/test/foo')

    def test_upload_fail_non_string_wsname(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': 1,
             'fwd_id': 'bar',
             'name': 'foo'
             },
            'wsname must be a string')

    def test_upload_fail_bad_wsname(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': '&bad',
             'fwd_id': 'bar',
             'name': 'foo'
             },
            'Illegal character in workspace name &bad: &', exception=DFUError)

    def test_upload_fail_non_num_mean(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': 'bar',
             'name': 'foo',
             'insert_size_mean': 'foo'
             },
            'insert_size_mean must be a number')

    def test_upload_fail_non_num_std(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': 'bar',
             'name': 'foo',
             'insert_size_std_dev': 'foo'
             },
            'insert_size_std_dev must be a number')

    def test_upload_fail_neg_mean(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': 'bar',
             'name': 'foo',
             'insert_size_mean': 0
             },
            'insert_size_mean must be > 0')

    def test_upload_fail_neg_std(self):
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': 'bar',
             'name': 'foo',
             'insert_size_std_dev': 0
             },
            'insert_size_std_dev must be > 0')

    def test_upload_fail_bad_fastq(self):
        print('*** upload_fail_bad_fastq ***')
        ret = self.upload_file_to_shock('data/Sample1_invalid.fastq')
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': ret['id'],
             'name': 'bar'
             },
            'Invalid fasta file /kb/module/work/tmp/fwd/Sample1_invalid.fastq')
#            'Invalid fasta file /kb/module/work/tmp/fwd/Sample1_invalid' +
#            '.fastq from Shock node ' + ret['id'])
        self.delete_shock_node(ret['id'])

    def test_upload_fail_bad_fastq_file(self):
        print('*** upload_fail_bad_fastq_file***')
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_file': 'data/Sample1_invalid.fastq',
             'name': 'bar'
             },
            'Invalid fasta file /kb/module/test/data/Sample1_invalid' +
            '.fastq')

    def test_upload_fail_interleaved_for_single(self):
        ret = self.upload_file_to_shock('data/Sample5_interleaved.fastq')
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': ret['id'],
             'name': 'bar'
             },
            'Invalid fasta file /kb/module/work/tmp/fwd/Sample5_interleaved.fastq')
#            'Invalid fasta file /kb/module/work/tmp/fwd/Sample5_interleaved' +
#            '.fastq from Shock node ' + ret['id'])
        self.delete_shock_node(ret['id'])

    # Download tests ########################################################

    def test_download_one(self):
        self.download_success(
            {'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                }
             }
        )

    def test_multiple(self):
        self.download_success(
            {'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'intbasic': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                }
             }
        )

    def test_single_end(self):
        self.download_success(
            {'single_end': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end']['ref']
                     })
                },
             'single_end_kbassy': {
                'md5': {'fwd': self.MD5_SM_R},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.reverse.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end_kbassy']['ref']
                     })
                },
             'single_end_gz': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.forward.fq.gz',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end_gz']['ref']
                     })
                },
             'single_end_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_R},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.reverse.fq.gz',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end_kbassy_gz']['ref']
                     })
                }
             }
        )

    def test_paired(self):
        self.download_success(
            {'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'frbasic_kbassy': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq'
                               },
                     'ref': self.staged['frbasic_kbassy']['ref']
                     })
                },
             'frbasic_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq.gz',
                               'rev_name': 'small.reverse.fq'
                               },
                     'ref': self.staged['frbasic_gz']['ref']
                     })
                },
             'frbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq.gz'
                               },
                     'ref': self.staged['frbasic_kbassy_gz']['ref']
                     })
                }
             }
        )

    def test_interleaved(self):
        self.download_success(
            {'intbasic': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic_kbassy']['ref']
                     })
                },
             'intbasic_gz': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq.gz',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic_gz']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq.gz',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                }
             }, interleave='none'
        )

    # test some compressed, some uncompressed
    def test_fr_to_interleave(self):
        fn = 'Sample5_noninterleaved.1.blank_lines.fastq'
        self.download_success(
            {'frbasic': {
                'md5': {'fwd': self.MD5_FR_TO_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq',
                               'rev': None
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'frbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_FR_TO_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'interleaved',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq.gz',
                               'rev': None
                               },
                     'ref': self.staged['frbasic_kbassy_gz']['ref']
                     })
                },
             'intbasic': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_I},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq.gz',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                },
             'single_end': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end']['ref']
                     })
                },
             'single_end_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_R},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.reverse.fq.gz',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end_kbassy_gz']['ref']
                     })
                },
             'fr_blank_line': {
                'md5': {'fwd': self.MD5_FR_TO_I_BLANK},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'paired',
                               'fwd_name': fn,
                               'rev_name': 'Sample5_noninterleaved.2.fastq',
                               'rev': None
                               },
                     'ref': self.staged['fr_blank_line']['ref']
                     })
                },
             }, interleave='true'
        )

    # test some compressed, some uncompressed
    def test_deinterleave(self):
        self.download_success(
            {'intbasic': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'paired',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq',
                               'rev_name': None
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'paired',
                               'otype': 'interleaved',
                               'fwd_name': 'interleaved.fq.gz',
                               'rev_name': None
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                },
             'frbasic_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq.gz',
                               'rev_name': 'small.reverse.fq'
                               },
                     'ref': self.staged['frbasic_gz']['ref']
                     })
                },
             'frbasic_kbassy': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'paired',
                               'otype': 'paired',
                               'fwd_name': 'small.forward.fq',
                               'rev_name': 'small.reverse.fq'
                               },
                     'ref': self.staged['frbasic_kbassy']['ref']
                     })
                },
             'single_end_gz': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.forward.fq.gz',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end_gz']['ref']
                     })
                },
             'single_end_kbassy': {
                'md5': {'fwd': self.MD5_SM_R},
                'fileext': {'fwd': 'single'},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'type': 'single',
                               'otype': 'single',
                               'fwd_name': 'small.reverse.fq',
                               'rev_name': None,
                               'rev': None
                               },
                     'ref': self.staged['single_end_kbassy']['ref']
                     })
                },
             'int_blank_line': {
                'md5': {'fwd': self.MD5_I_BLANK_TO_F,
                        'rev': self.MD5_I_BLANK_TO_R},
                'fileext': {'fwd': 'fwd', 'rev': 'rev'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'paired',
                               'otype': 'interleaved',
                               'fwd_name':
                                   'Sample5_interleaved_blank_lines.fastq',
                               'rev_name': None
                               },
                     'ref': self.staged['int_blank_line']['ref']
                     })
                },
             }, interleave='false'
        )

    def test_compressed_file_extensions(self):
        self.download_success(
            {'gzip': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'small.forward.fq',
                               'rev': None,
                               'rev_name': None
                               },
                     'ref': self.staged['gzip']['ref']
                     })
                },
             'bz': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'small.forward.fq',
                               'rev': None,
                               'rev_name': None
                               },
                     'ref': self.staged['bz']['ref']
                     })
                },
             'bzip': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'inter'},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'type': 'interleaved',
                               'otype': 'interleaved',
                               'fwd_name': 'small.forward.fq',
                               'rev': None,
                               'rev_name': None
                               },
                     'ref': self.staged['bzip']['ref']
                     })
                }
             })

    def test_object_contents_single_end_single_genome(self):
        self.download_success(
            {'kbfile_sing_sg_t': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'single'},
                'obj': {'files': {'type': 'single',
                                  'otype': 'single',
                                  'fwd_name': 'small.forward.fq',
                                  'rev_name': None,
                                  'rev': None
                                  },
                        'ref': self.staged['kbfile_sing_sg_t']['ref'],
                        'single_genome': 'true',
                        'strain': {u'genus': u'Yersinia',
                                   u'species': u'pestis',
                                   u'strain': u'happypants'
                                   },
                        'source': {u'source': u'my pants'},
                        'sequencing_tech': u'IonTorrent',
                        'read_count': 3,
                        'read_size': 12,
                        'gc_content': 2.3,
                        'read_orientation_outward': None,
                        'insert_size_mean': None,
                        'insert_size_std_dev': None
                        }
                }
             }
        )

    def test_object_contents_single_end_metagenome(self):
        self.download_success(
            {'kbfile_sing_sg_f': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'single'},
                'obj': {'files': {'type': 'single',
                                  'otype': 'single',
                                  'fwd_name': 'small.forward.fq',
                                  'rev_name': None,
                                  'rev': None
                                  },
                        'ref': self.staged['kbfile_sing_sg_f']['ref'],
                        'single_genome': 'false',
                        'strain': {u'genus': u'Deinococcus',
                                   u'species': u'radiodurans',
                                   u'strain': u'radiopants'
                                   },
                        'source': {u'source': u'also my pants'},
                        'sequencing_tech': u'PacBio CCS',
                        'read_count': 4,
                        'read_size': 13,
                        'gc_content': 2.4,
                        'read_orientation_outward': None,
                        'insert_size_mean': None,
                        'insert_size_std_dev': None
                        }
                }
             }
        )

    def test_object_contents_kbassy_roo_true(self):
        self.download_success(
            {'kbassy_roo_t': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'inter'},
                'obj': {'files': {'type': 'interleaved',
                                  'otype': 'interleaved',
                                  'fwd_name': 'small.forward.fq',
                                  'rev_name': None,
                                  'rev': None
                                  },
                        'ref': self.staged['kbassy_roo_t']['ref'],
                        'single_genome': None,
                        'strain': None,
                        'source': None,
                        'sequencing_tech': None,
                        'read_count': None,
                        'read_size': None,
                        'gc_content': None,
                        'read_orientation_outward': 'true',
                        'insert_size_mean': 42,
                        'insert_size_std_dev': 1000000
                        }
                }
             }
        )

    def test_object_contents_kbassy_roo_false(self):
        self.download_success(
            {'kbassy_roo_f': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'inter'},
                'obj': {'files': {'type': 'interleaved',
                                  'otype': 'interleaved',
                                  'fwd_name': 'small.forward.fq',
                                  'rev_name': None,
                                  'rev': None
                                  },
                        'ref': self.staged['kbassy_roo_f']['ref'],
                        'single_genome': None,
                        'strain': None,
                        'source': None,
                        'sequencing_tech': None,
                        'read_count': None,
                        'read_size': None,
                        'gc_content': None,
                        'read_orientation_outward': 'false',
                        'insert_size_mean': 43,
                        'insert_size_std_dev': 1000001
                        }
                }
             }
        )

    def test_object_contents_kbfile_true(self):
        self.download_success(
            {'kbfile_pe_t': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'inter'},
                'obj': {'files': {'type': 'interleaved',
                                  'otype': 'interleaved',
                                  'fwd_name': 'small.forward.fq',
                                  'rev_name': None,
                                  'rev': None
                                  },
                        'ref': self.staged['kbfile_pe_t']['ref'],
                        'single_genome': 'true',
                        'strain': {u'genus': u'Bacillus',
                                   u'species': u'subtilis',
                                   u'strain': u'soilpants'
                                   },
                        'source': {u'source': u'my other pants'},
                        'sequencing_tech': 'Sanger',
                        'read_count': 5,
                        'read_size': 14,
                        'gc_content': 2.5,
                        'read_orientation_outward': 'true',
                        'insert_size_mean': 50,
                        'insert_size_std_dev': 1000002
                        }
                }
             }
        )

    def test_object_contents_kbfile_false(self):
        self.download_success(
            {'kbfile_pe_f': {
                'md5': {'fwd': self.MD5_SM_F},
                'fileext': {'fwd': 'inter'},
                'obj': {'files': {'type': 'interleaved',
                                  'otype': 'interleaved',
                                  'fwd_name': 'small.forward.fq',
                                  'rev_name': None,
                                  'rev': None
                                  },
                        'ref': self.staged['kbfile_pe_f']['ref'],
                        'single_genome': 'false',
                        'strain': {u'genus': u'Escheria',
                                   u'species': u'coli',
                                   u'strain': u'poopypants'
                                   },
                        'source': {u'source': u'my ex-pants'},
                        'sequencing_tech': 'PacBio CLR',
                        'read_count': 6,
                        'read_size': 15,
                        'gc_content': 2.6,
                        'read_orientation_outward': 'false',
                        'insert_size_mean': 51,
                        'insert_size_std_dev': 1000003
                        }
                }
             }
        )

    def test_no_workspace_param(self):

        self.download_error(
            ['foo'], 'Error on ObjectSpecification #1: Illegal number ' +
            'of separators / in object reference foo',
            exception=DFUError)

    def test_bad_workspace_name(self):

        self.download_error(
            ['bad*name/foo'],
            'Error on ObjectSpecification #1: Illegal character in ' +
            'workspace name bad*name: *', exception=DFUError)

    def test_non_extant_workspace(self):

        self.download_error(
            ['Ireallyhopethisworkspacedoesntexistorthistestwillfail/foo'],
            'Object foo cannot be accessed: No workspace with name ' +
            'Ireallyhopethisworkspacedoesntexistorthistestwillfail exists',
            exception=DFUError)

    def test_bad_lib_name(self):

        self.download_error(
            [self.getWsName() + '/bad&name'],
            'Error on ObjectSpecification #1: Illegal character in object ' +
            'name bad&name: &', exception=DFUError)

    def test_no_libs_param(self):

        self.download_error(None, 'read_libraries parameter is required')

    def test_no_libs_list(self):

        self.download_error('foo', 'read_libraries must be a list')

    def test_non_extant_lib(self):

        self.download_error(
            [self.getWsName() + '/foo'],
            'No object with name foo exists in workspace ' +
            str(self.ws_info[0]), exception=DFUError)

    def test_no_libs(self):

        self.download_error([], 'At least one reads library must be provided')

    def test_null_libs(self):

        self.download_error([None],
                            'Invalid workspace object name: None')

    def test_empty_name_libs(self):

        self.download_error([''],
                            'Invalid workspace object name: ')

    def test_bad_module(self):

        self.download_error(
            [self.getWsName() + '/empty'],
            ('Invalid type for object {} (empty). Supported ' +
             'types: KBaseFile.SingleEndLibrary ' +
             'KBaseFile.PairedEndLibrary ' +
             'KBaseAssembly.SingleEndLibrary ' +
             'KBaseAssembly.PairedEndLibrary').format(
                self.staged['empty']['ref']))

    def test_bad_type(self):

        self.download_error(
            [self.getWsName() + '/fileref'],
            ('Invalid type for object {} (fileref). Supported ' +
             'types: KBaseFile.SingleEndLibrary ' +
             'KBaseFile.PairedEndLibrary ' +
             'KBaseAssembly.SingleEndLibrary ' +
             'KBaseAssembly.PairedEndLibrary').format(
                self.staged['fileref']['ref']))

    def test_bad_shock_filename(self):

        self.download_error(
            [self.getWsName() + '/bad_shk_name'],
            ('Shock file name is illegal: small.forward.bad. Expected FASTQ ' +
             'file. Reads object bad_shk_name ({}). Shock node {}').format(
                self.staged['bad_shk_name']['ref'],
                self.staged['bad_shk_name']['fwd_node_id']))

    def test_bad_handle_filename(self):

        self.download_error(
            [self.getWsName() + '/bad_file_name'],
            ('Handle file name from reads Workspace object is illegal: ' +
             'file.terrible. Expected FASTQ file. Reads object ' +
             'bad_file_name ({}). Shock node {}').format(
                self.staged['bad_file_name']['ref'],
                self.staged['bad_file_name']['fwd_node_id']))

    def test_bad_file_type(self):

        self.download_error(
            [self.getWsName() + '/bad_file_type'],
            ('File type from reads Workspace object is illegal: .xls. ' +
             'Expected FASTQ file. Reads object bad_file_type ({}). ' +
             'Shock node {}').format(
                self.staged['bad_file_type']['ref'],
                self.staged['bad_file_type']['fwd_node_id']))

    def test_bad_file_type_good_compress_ext(self):

        self.download_error(
            [self.getWsName() + '/bad_ext'],
            ('File type from reads Workspace object is illegal: .foo.gzip. ' +
             'Expected FASTQ file. Reads object bad_ext ({}). ' +
             'Shock node {}').format(
                self.staged['bad_ext']['ref'],
                self.staged['bad_ext']['fwd_node_id']))

#     def test_no_file_info(self):
#
#         self.download_error(
#             [self.getWsName() + '/no_file_info'],
#             ('Unable to determine file type from Shock or Workspace ' +
#              'data. Reads object no_file_info ({}). Shock node {}').format(
#                 self.staged['no_file_info']['ref'],
#                 self.staged['no_file_info']['fwd_node_id']))

    def test_bad_shock_node(self):

        self.download_error(
            [self.getWsName() + '/bad_node'],
            ('Handle error for object {}: The Handle Manager reported a ' +
             'problem while attempting to set Handle ACLs: Unable to set ' +
             'acl(s) on handles {}').format(
                self.staged['bad_node']['ref'],
                self.staged['bad_node']['fwd_handle']['hid']),
            exception=DFUError)

    def test_invalid_interleave_input(self):

        self.download_error(
            ['foo'], 'Illegal value for ternary parameter interleaved: ' +
            'wubba. Allowed values are "true", "false", and null.',
            interleave='wubba')

    def test_bad_deinterleave(self):
        self.download_error(
            [self.getWsName() + '/int_miss_line'],
            ('Deinterleave failed - line count is not divisible by 8. ' +
             'Workspace reads object int_miss_line ({}), Shock node {}, ' +
             'Shock filename Sample5_interleaved_missing_line.fastq.')
            .format(self.staged['int_miss_line']['ref'],
                    self.staged['int_miss_line']['fwd_node_id']),
            interleave='false')

    def test_bad_interleave_missing_line(self):
        self.download_error(
            [self.getWsName() + '/fr_missing_line'],
            ('Reading FASTQ record failed - non-blank lines ' +
             'are not a multiple of four. Workspace reads ' +
             'object fr_missing_line ({}), Shock node {}, Shock filename ' +
             'Sample5_noninterleaved.1.missing_line.fastq')
            .format(self.staged['fr_missing_line']['ref'],
                    self.staged['fr_missing_line']['fwd_node_id']),
            interleave='true')

    def test_bad_interleave_missing_record_fwd(self):
        self.download_error(
            [self.getWsName() + '/fr_missing_rec_f'],
            ('Interleave failed - reads files do not have ' +
             'an equal number of records. Workspace reads ' +
             'object fr_missing_rec_f ({}), ' +
             'forward Shock node {}, filename ' +
             'Sample5_noninterleaved.1.missing_rec.fastq, ' +
             'reverse Shock node {}, filename Sample5_noninterleaved.2.fastq')
            .format(self.staged['fr_missing_rec_f']['ref'],
                    self.staged['fr_missing_rec_f']['fwd_node_id'],
                    self.staged['fr_missing_rec_f']['rev_node_id']),
            interleave='true')

    def test_bad_interleave_missing_record_rev(self):
        self.download_error(
            [self.getWsName() + '/fr_missing_rec_r'],
            ('Interleave failed - reads files do not have ' +
             'an equal number of records. Workspace reads ' +
             'object fr_missing_rec_r ({}), ' +
             'forward Shock node {}, filename ' +
             'Sample5_noninterleaved.1.fastq, ' +
             'reverse Shock node {}, filename ' +
             'Sample5_noninterleaved.2.missing_rec.fastq')
            .format(self.staged['fr_missing_rec_r']['ref'],
                    self.staged['fr_missing_rec_r']['fwd_node_id'],
                    self.staged['fr_missing_rec_r']['rev_node_id']),
            interleave='true')

    def download_error(self, readnames, error,
                       interleave=None, exception=ValueError):

        test_name = inspect.stack()[1][3]
        print('\n****** starting expected fail test: ' + test_name + ' ******')

        params = {'interleaved': interleave}

        if (readnames is not None):
            params['read_libraries'] = readnames

        print('Running test with {} libs. Params:'.format(
            0 if not readnames else len(readnames)))
        pprint(params)

        with self.assertRaises(exception) as context:
            self.impl.download_reads(self.ctx, params)
        self.assertEqual(error, str(context.exception.message))

    def download_success(self, testspecs, interleave=None):
        self.maxDiff = None
        test_name = inspect.stack()[1][3]
        print('\n**** starting expected success test: ' + test_name + ' ***\n')

        params = {'read_libraries':
                  [(self.getWsName() + '/' + f) for f in testspecs]
                  }
        if interleave != 'none':
            params['interleaved'] = interleave

        print('Running test with {} libs. Params:'.format(len(testspecs)))
        pprint(params)

        ret = self.impl.download_reads(self.ctx, params)[0]
        print('\n== converter returned:')
        pprint(ret)
        retmap = ret['files']
        self.assertEqual(len(retmap), len(testspecs))
        for f in testspecs:
            wsref = self.getWsName() + '/' + f
            print('== checking testspec ' + f)
            for dirc in testspecs[f]['md5']:
                print('\t== checking md5s for read set ' + dirc)
                expectedmd5 = testspecs[f]['md5'][dirc]
                file_ = retmap[wsref]['files'][dirc]
                fileext = testspecs[f]['fileext'][dirc]
                if not file_.endswith('.' + fileext + '.fastq'):
                    raise TestError('Expected file {} to end with .{}.fastq'
                                    .format(file_, fileext))
                self.assertEqual(expectedmd5, self.md5(file_))
                del retmap[wsref]['files'][dirc]
            self.assertDictEqual(testspecs[f]['obj'], retmap[wsref])

    # exporter tests #####################################################

    def test_fail_export_no_ref(self):
        self.export_error(None, 'No input_ref specified')

    def test_fail_export_bad_ref(self):
        self.export_error(
            '1000000000/10000000000/10000000',
            'Object 10000000000 cannot be accessed: No workspace with id ' +
            '1000000000 exists', exception=WorkspaceError)

    def test_export_fr(self):
        self.export_success('frbasic', self.MD5_SM_F, self.MD5_SM_R)

    def test_export_sing(self):
        self.export_success('single_end', self.MD5_SM_F)

    def export_error(self, ref, error, exception=ValueError):
        test_name = inspect.stack()[1][3]
        print('\n*** starting expected export fail test: ' + test_name + ' **')
        print('ref: ' + str(ref))
        with self.assertRaises(exception) as context:
            self.impl.export_reads(self.ctx, {'input_ref': ref})
        self.assertEqual(error, str(context.exception.message))

    def export_success(self, stagedname, fwdmd5, revmd5=None):
        test_name = inspect.stack()[1][3]
        print('\n*** starting expected export pass test: ' + test_name + ' **')
        shocknode = self.impl.export_reads(
            self.ctx,
            {'input_ref': self.staged[stagedname]['ref']})[0]['shock_id']
        node_url = self.shockURL + '/node/' + shocknode
        headers = {'Authorization': 'OAuth ' + self.token}
        r = requests.get(node_url, headers=headers, allow_redirects=True)
        fn = r.json()['data']['file']['name']
        self.assertEquals(fn, stagedname + '.zip')
        tempdir = tempfile.mkdtemp(dir=self.scratch)
        file_path = os.path.join(tempdir, test_name) + '.zip'
        print('zip file path: ' + file_path)
        print('downloading shocknode ' + shocknode)
        with open(file_path, 'wb') as fhandle:
            r = requests.get(node_url + '?download_raw', stream=True,
                             headers=headers, allow_redirects=True)
            for chunk in r.iter_content(1024):
                if not chunk:
                    break
                fhandle.write(chunk)
        with ZipFile(file_path) as z:
            z.extractall(tempdir)
        print('zip file contents: ' + str(os.listdir(tempdir)))
        foundf = False
        foundr = False
        for f in os.listdir(tempdir):
            if '.fwd.' in f or '.inter.' in f or '.single.' in f:
                foundf = True
                print('fwd reads: ' + f)
                with open(os.path.join(tempdir, f)) as fl:
                    md5 = hashlib.md5(fl.read()).hexdigest()
                    self.assertEqual(md5, fwdmd5)
            if '.rev.' in f:
                foundr = True
                print('rev reads: ' + f)
                with open(os.path.join(tempdir, f)) as fl:
                    md5 = hashlib.md5(fl.read()).hexdigest()
                    self.assertEqual(md5, revmd5)
        if not foundf:
            raise TestError('no fwd reads file')
        if revmd5 and not foundr:
            raise TestError('no rev reads file when expected')
        if foundr and not revmd5:
            raise TestError('found rev reads when unexpected')
        count = 4 if revmd5 else 3
        if len(os.listdir(tempdir)) != count:
            raise TestError('found extra files in testdir {}: {}'.format(
                os.path.abspath(tempdir), str(os.listdir(tempdir))))
