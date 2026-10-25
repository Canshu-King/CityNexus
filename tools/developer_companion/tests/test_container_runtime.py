"""Control-plane/transport tests; TEST_UPSTREAM is not real container acceptance."""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import threading
from types import SimpleNamespace
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from tools.developer_companion.container_runtime import (
    ContainerConfig, IsolationUnavailable, ModelMailboxBroker, _read_plain_file,
    prepare_container, worker_command,
)

IMAGE = "sha256:" + "a" * 64
MODEL = "cn:deepseek-v4.1-flash"
KEY = "TEST_UPSTREAM_OWNER_KEY_0123456789"


class _Upstream(BaseHTTPRequestHandler):
    calls = []
    redirect = False
    hold_body = False
    headers_ready = threading.Event()
    release_body = threading.Event()
    def do_POST(self):
        value = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.calls.append({"authorization": self.headers.get("Authorization"), "body": value})
        if self.redirect:
            self.send_response(307)
            self.send_header("Location", "http://127.0.0.1:1/private")
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            if self.hold_body:
                self.headers_ready.set()
                self.release_body.wait(5)
            try:
                self.wfile.write(b'data: {"TEST_UPSTREAM":"ok"}\n\ndata: [DONE]\n\n')
            except OSError:
                pass
    def log_message(self, *args):
        pass


class ContainerRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.checkout = self.root / "checkout"
        self.checkout.mkdir()
        self.mailbox = self.root / "mailbox"
        self.mailbox.mkdir()
        self.key_file = self.root / "host-only.key"
        self.key_file.write_text(KEY, encoding="utf-8")
        self.config = ContainerConfig(IMAGE, "http://127.0.0.1:8080/v1", self.key_file, MODEL)
    def tearDown(self):
        self.temp.cleanup()
    def test_worker_mounts_only_task_data_and_readonly_task_git(self):
        command = worker_command(IMAGE, self.checkout, self.mailbox, "cn51-test", "node", "entry.mjs")
        self.assertIn("--network=none", command)
        self.assertIn("--read-only", command)
        self.assertIn("--cap-drop=ALL", command)
        self.assertIn("--security-opt=no-new-privileges", command)
        self.assertEqual(command[command.index("--user")+1], "10001:10001")
        self.assertEqual(command.count("--mount"), 4)
        git_mounts=[value for value in command if "target=/taskgit" in value or "target=/workspace/.git" in value]
        self.assertEqual(len(git_mounts),2)
        self.assertTrue(all(value.endswith(",readonly") for value in git_mounts))
        self.assertNotIn(str(self.key_file), str(command))
        self.assertNotIn(KEY, str(command))
        self.assertNotIn("--privileged", command)
    def test_mutable_images_remote_plaintext_and_key_inside_workspace_rejected(self):
        for config in (
            ContainerConfig("node:latest", self.config.endpoint, self.key_file, MODEL),
            ContainerConfig(IMAGE, "http://example.com/v1", self.key_file, MODEL),
            ContainerConfig(IMAGE, "https://example.com/v1?key=x", self.key_file, MODEL),
        ):
            with self.assertRaises(IsolationUnavailable):
                config.validate(self.checkout)
        inside = self.checkout / "key.txt"
        inside.write_text(KEY)
        with self.assertRaisesRegex(IsolationUnavailable, "INSIDE_WORKSPACE"):
            ContainerConfig(IMAGE, self.config.endpoint, inside, MODEL).validate(self.checkout)
    def test_engine_failure_occurs_before_credential_broker_or_model_start(self):
        with patch("tools.developer_companion.container_runtime._docker", side_effect=IsolationUnavailable("CONTAINER_ENGINE_UNAVAILABLE")), patch.object(ModelMailboxBroker, "__init__", side_effect=AssertionError("must not read key")):
            with self.assertRaisesRegex(IsolationUnavailable, "ENGINE_UNAVAILABLE"):
                prepare_container(self.checkout, self.root, self.config)
        self.assertFalse((self.root / "container-mailbox").exists())

    def test_failed_boundary_probe_cannot_start_a_model(self):
        observed={'uid':0,'forbidden_reads':{'/host':'READABLE'},'root_write_succeeded':True,'external_network_connected':True}
        with patch("tools.developer_companion.container_runtime._docker", side_effect=['version',json.dumps([{'Config':{'User':'10001:10001'}}]),'']), patch("tools.developer_companion.container_runtime.subprocess.run", return_value=SimpleNamespace(returncode=0,stdout=json.dumps(observed).encode())):
            with self.assertRaisesRegex(IsolationUnavailable,"BOUNDARY_PROBE_FAILED"):
                prepare_container(self.checkout,self.root,self.config)

    def test_cleanup_requires_confirmed_container_exit(self):
        from tools.developer_companion.container_runtime import ContainerDshSdkProcess
        worker=object.__new__(ContainerDshSdkProcess)
        worker.container_name='cn51-test-owned'
        worker._container_lock=threading.Lock()
        worker._container_stopped=False
        with patch("tools.developer_companion.container_runtime._docker", side_effect=[IsolationUnavailable('failed'),'running']):
            worker._stop_container()
        self.assertEqual(worker.cleanup_error,'CONTAINER_STOP_NOT_CONFIRMED')
        with patch("tools.developer_companion.container_runtime._docker", side_effect=[IsolationUnavailable('already removed'),'']):
            worker._stop_container()
        self.assertIsNone(worker.cleanup_error)
    def test_broker_rejects_arbitrary_url_method_model_and_headers(self):
        broker = ModelMailboxBroker(self.mailbox, self.config)
        for value in (
            {"method":"GET","path":"/v1/chat/completions","body":{}},
            {"method":"POST","path":"http://internal/secret","body":{}},
            {"method":"POST","path":"/v1/chat/completions","body":{"model":"other","messages":[]}},
            {"method":"POST","path":"/v1/chat/completions","body":{},"headers":{"Authorization":"forged"}},
        ):
            with self.assertRaises(ValueError):
                broker.dispatch(value)
        self.assertEqual(broker.requests, 0)
        broker.close()
    def test_mailbox_plain_reader_limits_size_and_rejects_directories(self):
        with self.assertRaises(OSError):
            _read_plain_file(self.checkout, 10)
        self.assertEqual(_read_plain_file(self.key_file, 100), KEY.encode())
        with self.assertRaises(ValueError):
            _read_plain_file(self.key_file, 2)
    def test_mailbox_symlink_cannot_read_an_outside_file(self):
        link=self.mailbox/('req-'+'a'*32+'.json')
        try:
            link.symlink_to(self.key_file)
        except OSError:
            self.skipTest("Creating symlinks is not allowed for this OS account")
        with self.assertRaises(OSError):
            _read_plain_file(link, 1000)
    def test_stop_aborts_an_upstream_body_read(self):
        _Upstream.redirect=False
        _Upstream.hold_body=True
        _Upstream.headers_ready.clear()
        _Upstream.release_body.clear()
        server=ThreadingHTTPServer(('127.0.0.1',0),_Upstream)
        serving=threading.Thread(target=server.serve_forever,daemon=True);serving.start()
        broker=ModelMailboxBroker(self.mailbox,ContainerConfig(IMAGE,f'http://127.0.0.1:{server.server_port}/v1',self.key_file,MODEL))
        result={}
        thread=threading.Thread(target=lambda:result.update(broker.dispatch({'method':'POST','path':'/v1/chat/completions','body':{'model':MODEL,'messages':[]}})),daemon=True)
        thread.start()
        try:
            self.assertTrue(_Upstream.headers_ready.wait(3))
            broker.close()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(broker._key,'')
        finally:
            _Upstream.release_body.set();_Upstream.hold_body=False
            server.shutdown();server.server_close();serving.join(2);thread.join(3)
    @unittest.skipUnless(shutil.which("node"), "Node transport integration")
    def test_actual_node_http_to_mailbox_to_host_fixed_upstream(self):
        _Upstream.calls=[]
        _Upstream.redirect=False
        _Upstream.hold_body=False
        server=ThreadingHTTPServer(("127.0.0.1",0),_Upstream)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        config=ContainerConfig(IMAGE,f"http://127.0.0.1:{server.server_port}/v1",self.key_file,MODEL)
        broker=ModelMailboxBroker(self.mailbox,config)
        broker.start()
        module=(Path(__file__).resolve().parents[1]/'mailbox_proxy.mjs').as_uri()
        script=f"import{{startMailboxProxy}}from {json.dumps(module)};const s=await startMailboxProxy({json.dumps(str(self.mailbox))},0);console.log(s.address().port);process.stdin.resume();process.stdin.on('end',()=>s.close());"
        process=subprocess.Popen([shutil.which('node'),'--input-type=module','-e',script],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            port=int(process.stdout.readline())
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            request=urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",data=json.dumps({'model':MODEL,'messages':[{'role':'user','content':'TEST_UPSTREAM'}],'stream':True}).encode(),headers={'Content-Type':'application/json'})
            with opener.open(request,timeout=8) as response:
                self.assertIn(b'[DONE]',response.read())
            self.assertEqual(len(_Upstream.calls),1)
            self.assertEqual(_Upstream.calls[0]['authorization'],'Bearer '+KEY)
            self.assertEqual(_Upstream.calls[0]['body']['model'],MODEL)
            for path in self.mailbox.iterdir():
                self.assertNotIn(KEY.encode(),path.read_bytes())
            _Upstream.redirect=True
            result=broker.dispatch({'method':'POST','path':'/v1/chat/completions','body':{'model':MODEL,'messages':[]}})
            self.assertEqual(result['status'],502)
            self.assertNotIn(KEY,base64.b64decode(result['body_base64']).decode())
        finally:
            process.stdin.close()
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=3)
            for stream in (process.stdout,process.stderr): stream.close()
            broker.close();server.shutdown();server.server_close();thread.join(2)


if __name__ == '__main__':
    unittest.main()
