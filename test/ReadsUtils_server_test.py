import unittest
import time

from os import environ
import shutil
import os
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

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'ws_info'):
            cls.ws.delete_workspace({'id': cls.ws_info[0]})
            print('Test workspace was deleted')

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

    def fail_val_FASTA(self, filename, error, exception=ValueError):
        with self.assertRaises(exception) as context:
            self.impl.validateFASTA(self.ctx, {'file_path': filename})
        self.assertEqual(error, str(context.exception.message))

    def fail_val_FASTQ(self, filename, error, exception=ValueError):
        with self.assertRaises(exception) as context:
            self.impl.validateFASTQ(self.ctx, filename)
        self.assertEqual(error, str(context.exception.message))
