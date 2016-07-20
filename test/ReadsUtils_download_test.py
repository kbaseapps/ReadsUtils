import unittest
import os
import time

from os import environ
from ConfigParser import ConfigParser
from pprint import pprint

from biokbase.workspace.client import Workspace as workspaceService  # @UnresolvedImport @IgnorePep8
from kb_read_library_to_file.kb_read_library_to_fileImpl import kb_read_library_to_file  # @IgnorePep8
from biokbase.AbstractHandle.Client import AbstractHandle as HandleService  # @UnresolvedImport @IgnorePep8
from kb_read_library_to_file.kb_read_library_to_fileImpl import ShockError
from kb_read_library_to_file.kb_read_library_to_fileImpl import InvalidFileError  # @IgnorePep8
from biokbase.workspace.client import ServerError as WorkspaceError  # @UnresolvedImport @IgnorePep8
import shutil
import requests
import inspect
import hashlib
import subprocess


class TestError(Exception):
    pass


def dictmerge(x, y):
    z = x.copy()
    z.update(y)
    return z


class kb_read_library_to_fileTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = environ.get('KB_AUTH_TOKEN', None)
        cls.ctx = {'token': cls.token,
                   'authenticated': 1
                   }
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('kb_read_library_to_file'):
            cls.cfg[nameval[0]] = nameval[1]
        cls.wsURL = cls.cfg['workspace-url']
        cls.shockURL = cls.cfg['shock-url']
        cls.hs = HandleService(url=cls.cfg['handle-service-url'],
                               token=cls.token)
        cls.wsClient = workspaceService(cls.wsURL, token=cls.token)
        wssuffix = int(time.time() * 1000)
        wsName = "test_gaprice_SPAdes_" + str(wssuffix)
        cls.wsinfo = cls.wsClient.create_workspace({'workspace': wsName})
        print('created workspace ' + cls.getWsName())
        cls.serviceImpl = kb_read_library_to_file(cls.cfg)
        cls.staged = {}
        cls.nodes_to_delete = []
        cls.handles_to_delete = []
        cls.setupTestData()
        print('\n\n=============== Starting tests ==================')

    @classmethod
    def tearDownClass(cls):

        print('\n\n=============== Cleaning up ==================')

        if hasattr(cls, 'wsinfo'):
            cls.wsClient.delete_workspace({'workspace': cls.getWsName()})
            print('Test workspace was deleted: ' + cls.getWsName())
        if hasattr(cls, 'nodes_to_delete'):
            for node in cls.nodes_to_delete:
                cls.delete_shock_node(node)
        if hasattr(cls, 'handles_to_delete'):
            cls.hs.delete_handles(cls.hs.ids_to_handles(cls.handles_to_delete))
            print('Deleted handles ' + str(cls.handles_to_delete))

    @classmethod
    def getWsName(cls):
        return cls.wsinfo[1]

    def getImpl(self):
        return self.serviceImpl

    @classmethod
    def delete_shock_node(cls, node_id):
        header = {'Authorization': 'Oauth {0}'.format(cls.token)}
        requests.delete(cls.shockURL + '/node/' + node_id, headers=header,
                        allow_redirects=True)
        print('Deleted shock node ' + node_id)

    # Helper script borrowed from the transform service, logger removed
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
                                 'rev_node_id': rev_id
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
        return cls.wsClient.save_objects({
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
        print('WS url ' + cls.wsClient.url)
        print('Handle service url ' + cls.hs.url)
        print('staging data')
        sq = {'sequencing_tech': 'fake data'}
        cls.gzip('data/small.forward.fq', 'data/small.reverse.fq',
                 'data/interleaved.fq')
        # get file type from type
        fwd_reads = {'file': 'data/small.forward.fq',
                     'name': 'test_fwd.fastq',
                     'type': 'fastq'}
        fwd_reads_gz = {'file': 'data/small.forward.fq.gz',
                        'name': 'test_fwd.fastq.gz',
                        'type': 'fastq.Gz'}
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
        cls.upload_assembly('frbasic_kbassy', {}, fwd_reads,
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
        cls.upload_assembly('bad_node', sq, fwd_reads)
        cls.delete_shock_node(cls.nodes_to_delete.pop())
        cls.upload_empty_data('empty')
        cls.upload_file_ref('fileref', 'data/small.forward.fq')
        print('Data staged.')

    @classmethod
    def make_ref(cls, object_info):
        return str(object_info[6]) + '/' + str(object_info[0]) + \
            '/' + str(object_info[4])

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
    MD5_I_TO_F = '4a5f4c05aae26dcb288c0faec6583946'
    MD5_I_TO_R = '2be8de9afa4bcd1f437f35891363800a'

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

    def test_one(self):
        self.run_success(
            {'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                }
             }
        )

    def test_multiple(self):
        self.run_success(
            {'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'intbasic': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                }
             }
        )

    def test_single_end(self):
        self.run_success(
            {'single_end': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end']['ref']
                     })
                },
             'single_end_kbassy': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end_kbassy']['ref']
                     })
                },
             'single_end_gz': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_gz']['ref']
                     })
                },
             'single_end_kbassy_gz': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_kbassy_gz']['ref']
                     })
                }
             }
        )

    def test_paired(self):
        self.run_success(
            {'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'frbasic_kbassy': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic_kbassy']['ref']
                     })
                },
             'frbasic_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': True, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic_gz']['ref']
                     })
                },
             'frbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['frbasic_kbassy_gz']['ref']
                     })
                }
             }, gzip='none'
        )

    def test_interleaved(self):
        self.run_success(
            {'intbasic': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['intbasic_kbassy']['ref']
                     })
                },
             'intbasic_gz': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'true',
                               },
                     'ref': self.staged['intbasic_gz']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'true',
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                }
             }, interleave='none'
        )

    def test_gzip(self):
        self.run_success(
            {'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': True, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'frbasic_kbassy': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': True, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['frbasic_kbassy']['ref']
                     })
                },
             'intbasic': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'true',
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'true',
                               },
                     'ref': self.staged['intbasic_kbassy']['ref']
                     })
                },
             'single_end': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end']['ref']
                     })
                },
             'single_end_kbassy': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_kbassy']['ref']
                     })
                },
             'frbasic_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': True, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['frbasic_gz']['ref']
                     })
                },
             'frbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': True, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['frbasic_kbassy_gz']['ref']
                     })
                },
             'intbasic_gz': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'true',
                               },
                     'ref': self.staged['intbasic_gz']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'true',
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                },
             'single_end_gz': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_gz']['ref']
                     })
                },
             'single_end_kbassy_gz': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_kbassy_gz']['ref']
                     })
                }
             }, gzip='true', interleave='none'
        )

    def test_gunzip(self):
        self.run_success(
            {'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'frbasic_kbassy': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic_kbassy']['ref']
                     })
                },
             'intbasic': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['intbasic_kbassy']['ref']
                     })
                },
             'single_end': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end']['ref']
                     })
                },
             'single_end_kbassy': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end_kbassy']['ref']
                     })
                },
             'frbasic_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic_gz']['ref']
                     })
                },
             'frbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic_kbassy_gz']['ref']
                     })
                },
             'intbasic_gz': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['intbasic_gz']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                },
             'single_end_gz': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end_gz']['ref']
                     })
                },
             'single_end_kbassy_gz': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end_kbassy_gz']['ref']
                     })
                }
             }, gzip='false'
        )

    def test_fr_to_interleave(self):
        self.run_success(
            {'frbasic': {
                'md5': {'inter': self.MD5_FR_TO_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'frbasic_kbassy': {
                'md5': {'inter': self.MD5_FR_TO_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'false'},
                     'ref': self.staged['frbasic_kbassy']['ref']
                     })
                },
             'intbasic': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['intbasic_kbassy']['ref']
                     })
                },
             'single_end': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end']['ref']
                     })
                },
             'single_end_kbassy': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end_kbassy']['ref']
                     })
                },
             'frbasic_gz': {
                'md5': {'inter': self.MD5_FR_TO_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'false'},
                     'ref': self.staged['frbasic_gz']['ref']
                     })
                },
             'frbasic_kbassy_gz': {
                'md5': {'inter': self.MD5_FR_TO_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'false'},
                     'ref': self.staged['frbasic_kbassy_gz']['ref']
                     })
                },
             'intbasic_gz': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'true',
                               },
                     'ref': self.staged['intbasic_gz']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'true',
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                },
             'single_end_gz': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_gz']['ref']
                     })
                },
             'single_end_kbassy_gz': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_kbassy_gz']['ref']
                     })
                }
             }, interleave='true'
        )

    def test_fr_to_interleave_and_gzip(self):
        self.run_success(
            {'frbasic': {
                'md5': {'inter': self.MD5_FR_TO_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'true',
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'frbasic_kbassy': {
                'md5': {'inter': self.MD5_FR_TO_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'true'},
                     'ref': self.staged['frbasic_kbassy']['ref']
                     })
                },
             'intbasic': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'true',
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'true',
                               },
                     'ref': self.staged['intbasic_kbassy']['ref']
                     })
                },
             'single_end': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end']['ref']
                     })
                },
             'single_end_kbassy': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_kbassy']['ref']
                     })
                },
             'frbasic_gz': {
                'md5': {'inter': self.MD5_FR_TO_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'true'},
                     'ref': self.staged['frbasic_gz']['ref']
                     })
                },
             'frbasic_kbassy_gz': {
                'md5': {'inter': self.MD5_FR_TO_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'true'},
                     'ref': self.staged['frbasic_kbassy_gz']['ref']
                     })
                },
             'intbasic_gz': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'true',
                               },
                     'ref': self.staged['intbasic_gz']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'true',
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                },
             'single_end_gz': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_gz']['ref']
                     })
                },
             'single_end_kbassy_gz': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_kbassy_gz']['ref']
                     })
                }
             }, interleave='true', gzip='true'
        )

    def test_fr_to_interleave_and_ungzip(self):
        self.run_success(
            {'frbasic': {
                'md5': {'inter': self.MD5_FR_TO_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'frbasic_kbassy': {
                'md5': {'inter': self.MD5_FR_TO_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'false'},
                     'ref': self.staged['frbasic_kbassy']['ref']
                     })
                },
             'intbasic': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['intbasic_kbassy']['ref']
                     })
                },
             'single_end': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end']['ref']
                     })
                },
             'single_end_kbassy': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end_kbassy']['ref']
                     })
                },
             'frbasic_gz': {
                'md5': {'inter': self.MD5_FR_TO_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'false'},
                     'ref': self.staged['frbasic_gz']['ref']
                     })
                },
             'frbasic_kbassy_gz': {
                'md5': {'inter': self.MD5_FR_TO_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'false'},
                     'ref': self.staged['frbasic_kbassy_gz']['ref']
                     })
                },
             'intbasic_gz': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['intbasic_gz']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'inter': self.MD5_SM_I},
                'gzp': {'inter': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'inter_gz': 'false',
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                },
             'single_end_gz': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end_gz']['ref']
                     })
                },
             'single_end_kbassy_gz': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end_kbassy_gz']['ref']
                     })
                }
             }, interleave='true', gzip='false'
        )

    def test_deinterleave(self):
        self.run_success(
            {'intbasic': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['intbasic_kbassy']['ref']
                     })
                },
             'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'frbasic_kbassy': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic_kbassy']['ref']
                     })
                },
             'single_end': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end']['ref']
                     })
                },
             'single_end_kbassy': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end_kbassy']['ref']
                     })
                },
             'frbasic_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': True, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic_gz']['ref']
                     })
                },
             'frbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['frbasic_kbassy_gz']['ref']
                     })
                },
             'intbasic_gz': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['intbasic_gz']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                },
             'single_end_gz': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_gz']['ref']
                     })
                },
             'single_end_kbassy_gz': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_kbassy_gz']['ref']
                     })
                }
             }, interleave='false', gzip='none'
        )

    def test_deinterleave_and_gzip(self):
        self.run_success(
            {'intbasic': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'gzp': {'fwd': True, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'gzp': {'fwd': True, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['intbasic_kbassy']['ref']
                     })
                },
             'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': True, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'frbasic_kbassy': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': True, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['frbasic_kbassy']['ref']
                     })
                },
             'single_end': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end']['ref']
                     })
                },
             'single_end_kbassy': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_kbassy']['ref']
                     })
                },
             'frbasic_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': True, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['frbasic_gz']['ref']
                     })
                },
             'frbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': True, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['frbasic_kbassy_gz']['ref']
                     })
                },
             'intbasic_gz': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'gzp': {'fwd': True, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['intbasic_gz']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'gzp': {'fwd': True, 'rev': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'true',
                               'rev_gz': 'true'
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                },
             'single_end_gz': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_gz']['ref']
                     })
                },
             'single_end_kbassy_gz': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': True},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'true'},
                     'ref': self.staged['single_end_kbassy_gz']['ref']
                     })
                }
             }, interleave='false', gzip='true'
        )

    def test_deinterleave_and_ungzip(self):
        self.run_success(
            {'intbasic': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['intbasic']['ref']
                     })
                },
             'intbasic_kbassy': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['intbasic_kbassy']['ref']
                     })
                },
             'frbasic': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic']['ref']
                     })
                },
             'frbasic_kbassy': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic_kbassy']['ref']
                     })
                },
             'single_end': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end']['ref']
                     })
                },
             'single_end_kbassy': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end_kbassy']['ref']
                     })
                },
             'frbasic_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic_gz']['ref']
                     })
                },
             'frbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_SM_F, 'rev': self.MD5_SM_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['frbasic_kbassy_gz']['ref']
                     })
                },
             'intbasic_gz': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_P,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['intbasic_gz']['ref']
                     })
                },
             'intbasic_kbassy_gz': {
                'md5': {'fwd': self.MD5_I_TO_F, 'rev': self.MD5_I_TO_R},
                'gzp': {'fwd': False, 'rev': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'fwd_gz': 'false',
                               'rev_gz': 'false'
                               },
                     'ref': self.staged['intbasic_kbassy_gz']['ref']
                     })
                },
             'single_end_gz': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBF_S,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end_gz']['ref']
                     })
                },
             'single_end_kbassy_gz': {
                'md5': {'sing': self.MD5_SM_R},
                'gzp': {'sing': False},
                'obj': dictmerge(
                    self.STD_OBJ_KBA,
                    {'files': {'sing_gz': 'false'},
                     'ref': self.staged['single_end_kbassy_gz']['ref']
                     })
                }
             }, interleave='false', gzip='false'
        )

    def test_object_contents_single_end_single_genome(self):
        self.run_success(
            {'kbfile_sing_sg_t': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': False},
                'obj': {'files': {'sing_gz': 'false'},
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
        self.run_success(
            {'kbfile_sing_sg_f': {
                'md5': {'sing': self.MD5_SM_F},
                'gzp': {'sing': False},
                'obj': {'files': {'sing_gz': 'false'},
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
        self.run_success(
            {'kbassy_roo_t': {
                'md5': {'inter': self.MD5_SM_F},
                'gzp': {'inter': False},
                'obj': {'files': {'inter_gz': 'false'},
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
        self.run_success(
            {'kbassy_roo_f': {
                'md5': {'inter': self.MD5_SM_F},
                'gzp': {'inter': False},
                'obj': {'files': {'inter_gz': 'false'},
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
        self.run_success(
            {'kbfile_pe_t': {
                'md5': {'inter': self.MD5_SM_F},
                'gzp': {'inter': False},
                'obj': {'files': {'inter_gz': 'false'},
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
        self.run_success(
            {'kbfile_pe_f': {
                'md5': {'inter': self.MD5_SM_F},
                'gzp': {'inter': False},
                'obj': {'files': {'inter_gz': 'false'},
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

        self.run_error(['foo'], 'Error on ObjectIdentity #1: Illegal number ' +
                       'of separators / in object reference foo',
                       exception=WorkspaceError)

    def test_bad_workspace_name(self):

        self.run_error(
            ['bad*name/foo'],
            'Error on ObjectIdentity #1: Illegal character in workspace ' +
            'name bad*name: *', exception=WorkspaceError)

    def test_non_extant_workspace(self):

        self.run_error(
            ['Ireallyhopethisworkspacedoesntexistorthistestwillfail/foo'],
            'Object foo cannot be accessed: No workspace with name ' +
            'Ireallyhopethisworkspacedoesntexistorthistestwillfail exists',
            exception=WorkspaceError)

    def test_bad_lib_name(self):

        self.run_error(
            [self.getWsName() + '/bad&name'],
            'Error on ObjectIdentity #1: Illegal character in object name ' +
            'bad&name: &', exception=WorkspaceError)

    def test_no_libs_param(self):

        self.run_error(None, 'read_libraries parameter is required')

    def test_no_libs_list(self):

        self.run_error('foo', 'read_libraries must be a list')

    def test_non_extant_lib(self):

        self.run_error(
            [self.getWsName() + '/foo'],
            'No object with name foo exists in workspace ' +
            str(self.wsinfo[0]), exception=WorkspaceError)

    def test_no_libs(self):

        self.run_error([], 'At least one reads library must be provided')

    def test_bad_module(self):

        self.run_error([self.getWsName() + '/empty'],
                       ('Invalid type for object {} (empty). Supported ' +
                        'types: KBaseFile.SingleEndLibrary ' +
                        'KBaseFile.PairedEndLibrary ' +
                        'KBaseAssembly.SingleEndLibrary ' +
                        'KBaseAssembly.PairedEndLibrary').format(
                            self.staged['empty']['ref']))

    def test_bad_type(self):

        self.run_error([self.getWsName() + '/fileref'],
                       ('Invalid type for object {} (fileref). Supported ' +
                        'types: KBaseFile.SingleEndLibrary ' +
                        'KBaseFile.PairedEndLibrary ' +
                        'KBaseAssembly.SingleEndLibrary ' +
                        'KBaseAssembly.PairedEndLibrary').format(
                            self.staged['fileref']['ref']))

    def test_bad_shock_filename(self):

        self.run_error(
            [self.getWsName() + '/bad_shk_name'],
            ('Error downloading reads for object {} (bad_shk_name) from ' +
             'Shock node {}: A valid file extension could not be determined ' +
             'for the reads file. In order of precedence:\n' +
             'File type is: \nHandle file name is: \n' +
             'Shock file name is: small.forward.bad\n' +
             'Acceptable extensions: .fq .fastq .fq.gz ' +
             '.fastq.gz').format(self.staged['bad_shk_name']['ref'],
                                 self.staged['bad_shk_name']['fwd_node_id']),
            exception=InvalidFileError)

    def test_bad_handle_filename(self):

        self.run_error(
            [self.getWsName() + '/bad_file_name'],
            ('Error downloading reads for object {} (bad_file_name) from ' +
             'Shock node {}: A valid file extension could not be determined ' +
             'for the reads file. In order of precedence:\n' +
             'File type is: \nHandle file name is: file.terrible\n' +
             'Shock file name is: small.forward.fq\n' +
             'Acceptable extensions: .fq .fastq .fq.gz ' +
             '.fastq.gz').format(self.staged['bad_file_name']['ref'],
                                 self.staged['bad_file_name']['fwd_node_id']),
            exception=InvalidFileError)

    def test_bad_file_type(self):

        self.run_error(
            [self.getWsName() + '/bad_file_type'],
            ('Error downloading reads for object {} (bad_file_type) from ' +
             'Shock node {}: A valid file extension could not be determined ' +
             'for the reads file. In order of precedence:\n' +
             'File type is: .xls\nHandle file name is: small.forward.fastq\n' +
             'Shock file name is: small.forward.fq\n' +
             'Acceptable extensions: .fq .fastq .fq.gz ' +
             '.fastq.gz').format(self.staged['bad_file_type']['ref'],
                                 self.staged['bad_file_type']['fwd_node_id']),
            exception=InvalidFileError)

    def test_bad_shock_node(self):

        self.run_error([self.getWsName() + '/bad_node'],
                       ('Error downloading reads for object {} (bad_node) ' +
                        'from Shock node {}: Node not found').format(
                            self.staged['bad_node']['ref'],
                            self.staged['bad_node']['fwd_node_id']),
                       exception=ShockError)

    def test_invalid_gzip_input(self):

        self.run_error(
            ['foo'], 'Illegal value for ternary parameter gzip: foofoo. ' +
            'Allowed values are "true", "false", and null.', gzip='foofoo')

    def test_invalid_interleave_input(self):

        self.run_error(
            ['foo'], 'Illegal value for ternary parameter interleaved: ' +
            'wubba. Allowed values are "true", "false", and null.',
            interleave='wubba')

    def run_error(self, readnames, error, gzip=None,
                  interleave=None, exception=ValueError):

        test_name = inspect.stack()[1][3]
        print('\n****** starting expected fail test: ' + test_name + ' ******')

        params = {'gzip': gzip,
                  'interleaved': interleave}

        if (readnames is not None):
            params['read_libraries'] = readnames

        print('Running test with {} libs. Params:'.format(
            0 if not readnames else len(readnames)))
        pprint(params)

        with self.assertRaises(exception) as context:
            self.getImpl().convert_read_library_to_file(self.ctx, params)
        self.assertEqual(error, str(context.exception.message))

    def run_success(self, testspecs, gzip=None, interleave=None):
        self.maxDiff = None
        test_name = inspect.stack()[1][3]
        print('\n**** starting expected success test: ' + test_name + ' ***\n')

        params = {'read_libraries':
                  [(self.getWsName() + '/' + f) for f in testspecs]
                  }
        if gzip != 'none':
            params['gzip'] = gzip
        if interleave != 'none':
            params['interleaved'] = interleave

        print('Running test with {} libs. Params:'.format(len(testspecs)))
        pprint(params)

        ret = self.getImpl().convert_read_library_to_file(self.ctx, params)[0]
        print('\n== converter returned:')
        pprint(ret)
        retmap = ret['files']
        self.assertEqual(len(retmap), len(testspecs))
        for f in testspecs:
            wsref = self.getWsName() + '/' + f
            print('== checking testspec ' + f)
            for dirc in testspecs[f]['md5']:
                print('\t== checking read set ' + dirc)
                gz = testspecs[f]['gzp'][dirc]
                expectedmd5 = testspecs[f]['md5'][dirc]
                file_ = retmap[wsref]['files'][dirc]
                if gz:
                    if not file_.endswith('.' + dirc + '.fastq.gz'):
                        raise TestError(
                            'Expected file {} to end with .{}.fastq.gz'
                            .format(file_, dirc))
                    if subprocess.call(['gunzip', '-f', file_]):
                        raise TestError(
                            'Error unzipping file {}'.format(file_))
                    file_ = file_[: -3]
                elif not file_.endswith('.' + dirc + '.fastq'):
                    raise TestError('Expected file {} to end with .{}.fastq'
                                    .format(file_, dirc))
                self.assertEqual(expectedmd5, self.md5(file_))
                del retmap[wsref]['files'][dirc]
            self.assertDictEqual(testspecs[f]['obj'], retmap[wsref])
