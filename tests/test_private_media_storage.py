import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import httpx
from packages.media.storage import BUCKET, materialize_render, render_path


class PrivateMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.uri = '.local/production-renders/test/draft.mp4'
        env = patch.dict(os.environ, {'PRIVATE_MEDIA_BUCKET': BUCKET})
        env.start(); self.addCleanup(env.stop)

    def download(self, data=b'governed bytes', expected=None, maximum=100, size=None):
        requests = []
        def respond(request):
            requests.append(request)
            if request.url.params.get('alt') == 'media':
                self.assertEqual(request.url.params.get('generation'), '7')
                return httpx.Response(200, content=data)
            return httpx.Response(200, json={'size': str(len(data) if size is None else size), 'generation': '7'})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            path = materialize_render(self.root, self.uri, expected, maximum,
                                      client=client, token_source=lambda: 'test-only-token')
        return path, requests

    def test_generation_pinned_download_and_hash(self):
        data=b'governed bytes'; path,requests=self.download(expected=hashlib.sha256(data).hexdigest())
        self.assertEqual(path.read_bytes(),data);self.assertEqual(len(requests),2)
        self.assertTrue(all(request.url.host=='storage.googleapis.com' for request in requests))

    def test_local_cache_does_not_require_identity(self):
        path,_=self.download();result=materialize_render(self.root,self.uri,token_source=lambda: self.fail('No cloud identity needed'))
        self.assertEqual(result,path)

    def test_hash_mismatch_never_creates_cache(self):
        with self.assertRaises(ValueError):self.download(expected='0'*64)
        self.assertFalse((self.root/self.uri).exists())

    def test_oversized_cloud_asset_is_rejected(self):
        with self.assertRaises(ValueError):self.download(maximum=2)

    def test_size_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):self.download(size=1)

    def test_outside_render_path_is_rejected(self):
        with self.assertRaises(ValueError):render_path(self.root,'../../outside.mp4')

    def test_unconfigured_bucket_fails_closed(self):
        with patch.dict(os.environ,{'PRIVATE_MEDIA_BUCKET':''}):
            with self.assertRaises(FileNotFoundError):materialize_render(self.root,self.uri)

    def test_modified_cached_bytes_are_rejected(self):
        self.download()
        with self.assertRaises(ValueError):materialize_render(self.root,self.uri,'0'*64)
