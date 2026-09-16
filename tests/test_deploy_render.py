import contextlib
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts import deploy_render


class DeployTests(unittest.TestCase):
    def response(self, data):
        response = io.BytesIO(json.dumps(data).encode())
        response.status = 200
        return response

    def setUp(self):
        self.sha = 'a' * 40
        self.hook = 'https://api.render.com/deploy/unit-test?key=not-a-real-credential'
        self.env = patch.dict('os.environ', {
            'GITHUB_SHA': self.sha, 'GITHUB_REPOSITORY': 'example/project',
            'GH_TOKEN': 'test-token', 'RENDER_DEPLOY_HOOK': self.hook})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_skips_superseded_main_without_deploying(self):
        with patch.object(deploy_render.urllib.request, 'urlopen', return_value=self.response({'object': {'sha': 'b' * 40}})) as request:
            deploy_render.main()
        self.assertEqual(request.call_count, 1)

    def test_deploys_exact_sha_and_waits_for_matching_revision(self):
        replies = [self.response({'object': {'sha': self.sha}}), self.response({}),
                   self.response({'status': 'ok', 'revision': 'previous'}),
                   self.response({'status': 'ok', 'revision': self.sha})]
        with patch.object(deploy_render.urllib.request, 'urlopen', side_effect=replies) as request, patch.object(deploy_render.time, 'sleep') as sleep:
            deploy_render.main()
        deploy_request = request.call_args_list[1].args[0]
        self.assertEqual(deploy_request.method, 'POST')
        self.assertEqual(deploy_render.urllib.parse.parse_qs(deploy_render.urllib.parse.urlsplit(deploy_request.full_url).query)['ref'], [self.sha])
        sleep.assert_called_once_with(15)
        self.assertEqual(request.call_count, 4)

    def test_hook_failure_does_not_disclose_url(self):
        replies = [self.response({'object': {'sha': self.sha}}), HTTPError(self.hook, 401, self.hook, {}, None)]
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(deploy_render.urllib.request, 'urlopen', side_effect=replies):
            with self.assertRaises(SystemExit) as error:
                deploy_render.main()
        self.assertNotIn(self.hook, str(error.exception) + output.getvalue())
        self.assertNotIn('not-a-real-credential', str(error.exception) + output.getvalue())

    def test_unverified_revision_times_out(self):
        replies = [self.response({'object': {'sha': self.sha}}), self.response({}),
                   self.response({'status': 'ok', 'revision': 'previous'})]
        with patch.object(deploy_render.urllib.request, 'urlopen', side_effect=replies), patch.object(deploy_render.time, 'sleep'), patch.object(deploy_render.time, 'monotonic', side_effect=[0, 0, 721]):
            with self.assertRaisesRegex(SystemExit, 'did not become healthy'):
                deploy_render.main()


if __name__ == '__main__':
    unittest.main()
