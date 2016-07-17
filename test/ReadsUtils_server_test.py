import unittest
import time

from os import environ
import shutil
import os
from DataFileUtil.DataFileUtilClient import DataFileUtil
import requests
try:
    from ConfigParser import ConfigParser  # py2 @UnusedImport
except:
    from configparser import ConfigParser  # py3 @UnresolvedImport @Reimport

from biokbase.workspace.client import Workspace  # @UnresolvedImport
from ReadsUtils.ReadsUtilsImpl import ReadsUtils
from ReadsUtils.ReadsUtilsServer import MethodContext


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
        cls.impl = ReadsUtils(cls.cfg)
        shutil.rmtree(cls.cfg['scratch'])
        os.mkdir(cls.cfg['scratch'])
        suffix = int(time.time() * 1000)
        wsName = "test_ReadsUtils_" + str(suffix)
        cls.ws_info = cls.ws.create_workspace({'workspace': wsName})
        cls.dfu = DataFileUtil(os.environ['SDK_CALLBACK_URL'], token=cls.token)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'ws_info'):
            cls.ws.delete_workspace({'id': cls.ws_info[0]})
            print('Test workspace was deleted')

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

    def test_FASTA_validation(self):
        self.check_FASTA('data/sample.fa', 1)
        self.check_FASTA('data/sample.fas', 1)
        self.check_FASTA('data/sample.fna', 1)
        self.check_FASTA('data/sample.fasta', 1)
        self.check_FASTA('data/sample_missing_data.fa', 0)

    def check_FASTA(self, filename, result):
        self.assertEqual(
            self.impl.validateFASTA(
                self.ctx, {'file_path': filename})[0]['valid'], result)

    def test_FASTA_val_fail_no_file(self):
        self.fail_val_FASTA('nofile', 'No such file: nofile')
        self.fail_val_FASTA(None, 'No such file: None')
        self.fail_val_FASTA('', 'No such file: ')

    def test_FASTA_val_fail_bad_ext(self):
        self.fail_val_FASTA('data/sample.txt',
                            'File data/sample.txt is not a FASTA file')

    def test_FASTQ_validation(self):
        self.check_fq('data/Sample1.fastq', 1)
        self.check_fq('data/Sample1.fastq', 1)
        self.check_fq('data/Sample2_interleaved_illumina.fnq', 1)
        self.check_fq('data/Sample3_interleaved_casava1.8.fq', 1)
        self.check_fq('data/Sample4_interleaved_NCBI_SRA.fastq', 1)
        self.check_fq('data/Sample5_interleaved.fastq', 1)
        self.check_fq('data/Sample5_interleaved_blank_lines.fastq', 1)
        self.check_fq('data/Sample5_noninterleaved.1.fastq', 1)
        self.check_fq('data/Sample5_noninterleaved.2.fastq', 1)
        self.check_fq('data/Sample1_invalid.fastq', 0)
        self.check_fq('data/Sample4_interleaved_NCBI_SRA_duplicate_IDs.fastq',
                      0)
        self.check_fq('data/Sample5_interleaved_missing_line.fastq', 0)

    def check_fq(self, filepath, ok):
        fn = os.path.basename(filepath)
        newfn = self.cfg['scratch'] + '/' + fn
        shutil.copyfile(filepath, self.cfg['scratch'] + '/' + fn)
        self.assertEqual(self.impl.validateFASTQ(self.ctx, newfn)[0], ok)
        for l in open(newfn):
            self.assertNotEqual(l, '')

    def test_FASTQ_val_fail_no_file(self):
        self.fail_val_FASTQ('nofile', 'No such file: nofile')
        self.fail_val_FASTQ(None, 'No such file: None')
        self.fail_val_FASTQ('', 'No such file: ')

    def test_FASTQ_val_fail_bad_ext(self):
        self.fail_val_FASTQ('data/sample.txt',
                            'File data/sample.txt is not a FASTQ file')

    def test_single_end_reads_gzip(self):
        # gzip, minimum inputs
        ret = self.upload_file_to_shock('data/Sample1.fastq.gz')
        self.impl.upload_reads(self.ctx, {'fwd_id': ret['id'],
                                          'sequencing_tech': 'seqtech',
                                          'wsname': self.ws_info[1],
                                          'name': 'singlereads1'})
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/singlereads1']})['data'][0]
        # TODO strain and source
        # TODO single genome specified as true and false
        # TODO paired end params
        self.delete_shock_node(ret['id'])
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.SingleEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.check_lib(d['lib'], 2847, 'Sample1.fastq.gz', ret['id'],
                       '48efea6945c4382c68f5eac485c177c2')

    def check_lib(self, lib, size, filename, id_, md5):
        self.assertEqual(lib['size'], size)
        self.assertEqual(lib['type'], 'fq')
        self.assertEqual(lib['encoding'], 'ascii')
        libfile = lib['file']
        self.assertEqual(libfile['file_name'], filename)
        self.assertEqual(libfile['id'], id_)
        self.assertEqual(libfile['hid'].startswith('KBH_'), True)
        self.assertEqual(libfile['remote_md5'], md5)
        self.assertEqual(libfile['type'], 'shock')
        self.assertEqual(libfile['url'], self.shockURL)

    def fail_val_FASTA(self, filename, error, exception=ValueError):
        with self.assertRaises(exception) as context:
            self.impl.validateFASTA(self.ctx, {'file_path': filename})
        self.assertEqual(error, str(context.exception.message))

    def fail_val_FASTQ(self, filename, error, exception=ValueError):
        with self.assertRaises(exception) as context:
            self.impl.validateFASTQ(self.ctx, filename)
        self.assertEqual(error, str(context.exception.message))
