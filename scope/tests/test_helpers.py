from django.test import TestCase

from scope import helpers


class HelpersTests(TestCase):
    def test_ss_hosts_parser_success(self):
        hosts = [
            "http://user:secret@localhost:62081",
            "https://user:secret@192.168.1.128",
        ]
        parsed_hosts = helpers.ss_hosts_parser(hosts)
        expected_hosts = {
            "http://localhost:62081": {"user": "user", "secret": "secret"},
            "https://192.168.1.128": {"user": "user", "secret": "secret"},
        }
        self.assertEqual(parsed_hosts, expected_hosts)

    def test_ss_hosts_parser_error(self):
        hosts = [
            "http://user@localhost:62081",
            "//user:secret@192.168.1.128",
            "http://user:secret@localhost:ABC",
        ]
        for host in hosts:
            self.assertRaises(ValueError, helpers.ss_hosts_parser, [host])
