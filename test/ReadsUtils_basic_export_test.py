import unittest
import time

from pprint import pprint

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
        print('====created ws:'+cls.ws_info[1])
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

    def test_export(self):
        # paired end non interlaced, minimum inputs, upload it
        print('========uploading test data to shock========')
        ret1 = self.upload_file_to_shock('data/small.forward.fq')
        ret2 = self.upload_file_to_shock('data/small.reverse.fq')
        ref = self.impl.upload_reads(
            self.ctx, {'fwd_id': ret1['id'],
                       'rev_id': ret2['id'],
                       'sequencing_tech': 'seqtech-pr1',
                       'wsname': self.ws_info[1],
                       'name': 'pairedreads1',
                       'interleaved': 1})
        print('reference to new obj:')
        pprint(ref)

        print('========checking what we got========')
        pprint(self.ws.get_object_info_new({'objects':[{'ref':ref[0]['obj_ref']}]}))
        #obj = self.dfu.get_objects(
        #    {'object_refs': [self.ws_info[1] + '/pairedreads1']})['data'][0]
        #info = obj['info']
        #pprint(info)

        # try to download it
        download_package = self.impl.export_reads(self.ctx, {'input_ref': ref[0]['obj_ref'] })
        pprint(download_package)



