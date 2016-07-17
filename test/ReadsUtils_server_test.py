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

from Workspace.WorkspaceClient import Workspace
from DataFileUtil.baseclient import ServerError as DFUError
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

    def make_ref(self, objinfo):
        return str(objinfo[6]) + '/' + str(objinfo[0]) + '/' + str(objinfo[4])

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
        self.check_lib(d['lib'], 2847, 'Sample1.fastq.gz', ret['id'],
                       '48efea6945c4382c68f5eac485c177c2')

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
        self.check_lib(d['lib'], 1116, 'Sample5_noninterleaved.1.fastq',
                       ret['id'], '140a61c7f183dd6a2b93ef195bb3ec63')

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
        self.check_lib(d['lib'], 1116, 'Sample5_noninterleaved.1.fastq',
                       ret['id'], '140a61c7f183dd6a2b93ef195bb3ec63')

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
        self.check_lib(d['lib'], 9648, 'Sample1.fastq', ret['id'],
                       'f118ee769a5e1b40ec44629994dfc3cd')

    def test_paired_end_reads(self):
        # paired end non interlaced, minimum inputs
        ret1 = self.upload_file_to_shock('data/Sample5_noninterleaved.1.fastq')
        ret2 = self.upload_file_to_shock('data/Sample1.fastq.gz')
        ref = self.impl.upload_reads(
            self.ctx, {'fwd_id': ret1['id'],
                       'rev_id': ret2['id'],
                       'sequencing_tech': 'seqtech-pr1',
                       'wsname': self.ws_info[1],
                       'name': 'pairedreads1',
                       'interleaved': 1})
        obj = self.dfu.get_objects(
            {'object_refs': [self.ws_info[1] + '/pairedreads1']})['data'][0]
        self.delete_shock_node(ret1['id'])
        self.delete_shock_node(ret2['id'])
        self.assertEqual(ref[0]['obj_ref'], self.make_ref(obj['info']))
        self.assertEqual(obj['info'][2].startswith(
                        'KBaseFile.PairedEndLibrary'), True)
        d = obj['data']
        self.assertEqual(d['sequencing_tech'], 'seqtech-pr1')
        self.assertEqual(d['single_genome'], 1)
        self.assertEqual('source' not in d, True)
        self.assertEqual('strain' not in d, True)
        self.assertEqual(d['interleaved'], 0)
        self.assertEqual(d['read_orientation_outward'], 0)
        self.assertEqual(d['insert_size_mean'], None)
        self.assertEqual(d['insert_size_std_dev'], None)
        self.check_lib(d['lib1'], 1116, 'Sample5_noninterleaved.1.fastq',
                       ret1['id'], '140a61c7f183dd6a2b93ef195bb3ec63')
        self.check_lib(d['lib2'], 2847, 'Sample1.fastq.gz',
                       ret2['id'], '48efea6945c4382c68f5eac485c177c2')

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
        self.check_lib(d['lib1'], 2232, 'Sample5_interleaved.fastq',
                       ret['id'], '971a5f445055c85fd45b17459e15e3ed')

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
            'No reads file provided')

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

    def test_upload_fail_bad_fasta(self):
        print('*** upload_fail_bad_fasta ***')
        ret = self.upload_file_to_shock('data/Sample1_invalid.fastq')
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': ret['id'],
             'name': 'bar'
             },
            'Invalid fasta file /kb/module/work/tmp/fwd/Sample1_invalid' +
            '.fastq from Shock node ' + ret['id'])
        self.delete_shock_node(ret['id'])

    def test_upload_fail_interleaved_for_single(self):
        ret = self.upload_file_to_shock('data/Sample5_interleaved.fastq')
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': ret['id'],
             'name': 'bar'
             },
            'Invalid fasta file /kb/module/work/tmp/fwd/Sample5_interleaved' +
            '.fastq from Shock node ' + ret['id'])
        self.delete_shock_node(ret['id'])

    def test_upload_fail_interleaved_for_paired(self):
        ret1 = self.upload_file_to_shock('data/Sample1.fastq')
        ret2 = self.upload_file_to_shock('data/Sample5_interleaved.fastq')
        self.fail_upload_reads(
            {'sequencing_tech': 'tech',
             'wsname': self.ws_info[1],
             'fwd_id': ret1['id'],
             'rev_id': ret2['id'],
             'name': 'bar'
             },
            'Invalid fasta file /kb/module/work/tmp/rev/Sample5_interleaved' +
            '.fastq from Shock node ' + ret2['id'])
        self.delete_shock_node(ret1['id'])
        self.delete_shock_node(ret2['id'])

    def fail_val_FASTA(self, filename, error, exception=ValueError):
        with self.assertRaises(exception) as context:
            self.impl.validateFASTA(self.ctx, {'file_path': filename})
        self.assertEqual(error, str(context.exception.message))

    def fail_val_FASTQ(self, params, error, exception=ValueError):
        with self.assertRaises(exception) as context:
            self.impl.validateFASTQ(self.ctx, params)
        self.assertEqual(error, str(context.exception.message))
