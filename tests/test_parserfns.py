from unittest import TestCase
from unittest.mock import patch


class TestParserFunctions(TestCase):
    def setUp(self) -> None:
        from wikitextprocessor import Wtp

        self.wtp = Wtp()

    def tearDown(self) -> None:
        self.wtp.close_db_conn()

    def test_time_fn_with_mediawiki_timestamp(self) -> None:
        # GitHub issue #211
        # https://fr.wikipedia.org/wiki/Arabie_saoudite
        self.wtp.start_page("Arabie saoudite")
        self.assertEqual(
            self.wtp.expand("{{#time:j F Y|20130914013636}}"),
            "14 September 2013",
        )

    def test_coordinates_fn(self) -> None:
        self.wtp.start_page("Test")
        self.assertEqual(
            self.wtp.expand("{{#coordinates|foo|bar|baz}}"),
            "",
        )

    def test_pagesize_fn(self) -> None:
        self.wtp.add_page("sizetestA", 0, body="AAAAAAA" * 1000)
        self.wtp.add_page("sizetestB", 0, body="ÄÄÄÄÄÄÄ" * 1000)
        self.wtp.start_page("Test")
        self.assertEqual(
            self.wtp.expand("{{PAGESIZE:sizetestA|R}}"),
            "7,000",
        )
        self.assertEqual(
            self.wtp.expand("{{PAGESIZE:sizetestB|R}}"),
            "14,000",
        )
        self.assertEqual(
            self.wtp.expand("{{PAGESIZE:sizetestA}}"),
            "7000",
        )
        self.assertEqual(
            self.wtp.expand("{{PAGESIZE:sizetestB}}"),
            "14000",
        )

    def test_filepath_fn1(self) -> None:
        self.wtp.start_page("Test")
        self.assertEqual(
            self.wtp.expand("{{filepath:foo.jpg}}"), "//unimplemented/foo.jpg"
        )

    def test_filepath_fn2(self) -> None:
        self.wtp.start_page("Test")
        self.assertEqual(
            self.wtp.expand("{{filepath:foo.jpg|nowiki}}"),
            "//unimplemented/foo.jpg",
        )

    def test_filepath_fn3(self) -> None:
        self.wtp.start_page("Test")
        self.assertEqual(
            self.wtp.expand("{{filepath:foo.jpg|300|nowiki}}"),
            "//unimplemented/foo.jpg",
        )

    def test_filepath_fn4(self) -> None:
        self.wtp.start_page("Test")
        self.assertEqual(self.wtp.expand("{{filepath}}"), "")

    def test_timel(self):
        from datetime import datetime, timezone

        self.wtp.start_page("")
        expanded = self.wtp.expand("{{#timel:c}}")
        time = datetime.fromisoformat(expanded)
        delta = datetime.now(timezone.utc) - time
        self.assertLess(abs(delta.total_seconds()), 1)

    def test_rel2abs(self):
        # https://www.mediawiki.org/wiki/Help:Extension:ParserFunctions##rel2abs
        self.wtp.start_page("test")
        test_cases = (
            (
                "{{#rel2abs: /quok | Help:Foo/bar/baz }}",
                "Help:Foo/bar/baz/quok",
            ),
            (
                "{{#rel2abs: ./quok | Help:Foo/bar/baz }}",
                "Help:Foo/bar/baz/quok",
            ),
            ("{{#rel2abs: ../quok | Help:Foo/bar/baz }}", "Help:Foo/bar/quok"),
            ("{{#rel2abs: ../. | Help:Foo/bar/baz }}", "Help:Foo/bar"),
            (
                "{{#rel2abs: ../quok/. | Help:Foo/bar/baz }}",
                "Help:Foo/bar/quok",
            ),
            ("{{#rel2abs: ../../quok | Help:Foo/bar/baz }}", "Help:Foo/quok"),
            ("{{#rel2abs: ../../../quok | Help:Foo/bar/baz }}", "quok"),
            ("{{#rel2abs: b }}", "b"),
            ("{{#rel2abs: /b }}", "test/b"),
        )
        for wikitext, result in test_cases:
            with self.subTest(wikitext=wikitext, result=result):
                self.assertEqual(self.wtp.expand(wikitext), result)

    def test_ns_empty_str(self):
        # https://ru.wiktionary.org/wiki/Шаблон:--lang--
        self.wtp.start_page("test")
        self.assertEqual(self.wtp.expand("{{ns:0}}"), "")
        self.assertEqual(self.wtp.expand("{{ns:}}"), "")

    def test_int(self):
        # https://nl.wiktionary.org/wiki/Module:ISOdate
        self.wtp.start_page("test")
        self.wtp.lang_code = "en"
        self.assertEqual(self.wtp.expand("{{int:lang}}"), "⧼lang⧽")
        self.assertEqual(self.wtp.expand("{{int:}}"), "[[:Template:int:]]")

    def test_padleft_zero_division(self):
        # https://en.wiktionary.org/wiki/land
        # https://en.wiktionary.org/wiki/Template:R:osx:Kobler
        self.wtp.start_page("land")
        self.assertEqual(self.wtp.expand("{{padleft:|1|}}"), "")
        self.assertEqual(self.wtp.expand("{{padleft:|1}}"), "0")

    def test_padright_zero_division(self):
        self.wtp.start_page("land")
        self.assertEqual(self.wtp.expand("{{padright:|1|}}"), "")
        self.assertEqual(self.wtp.expand("{{padright:|1}}"), "0")

    def test_expand_int_fn_args(self):
        # https://vi.wiktionary.org/wiki/Bản_mẫu:like-entry
        self.wtp.start_page("trở thành")
        self.wtp.add_page("MediaWiki:wiktionary-like", 8, "Như $1")
        self.assertEqual(
            self.wtp.expand("{{int:wiktionary-like|first arg}}"),
            "Như first arg",
        )

    def test_html_attibute_in_switch_arg(self):
        # https://ru.wiktionary.org/wiki/больной
        self.wtp.start_page("больной")
        self.wtp.add_page(
            "Template:прил",
            10,
            "{{#switch:{{{краткая}}}|?|−|✕=not this|{{{srt-sg-m}}}}}",
        )
        self.assertEqual(
            self.wtp.expand(
                '{{прил|краткая=1|srt-sg-m=бо́лен<span style="color:#c0a300;"><sup>△</sup></span>}}'  # noqa: E501
            ),
            'бо́лен<span style="color:#c0a300;"><sup>△</sup></span>',
        )
    def test_variable_1(self):
        self.wtp.start_page("testvar")
        self.assertEqual(
            self.wtp.expand(
                "{{#var:foo}} {{#var:foo|bar}} {{#vardefineecho:foo|baz}} {{#var:foo|bar}} {{#vardefine:foo|goo}} {{#var:foo}}"
            ),
            " bar baz baz  goo"
        )
        self.assertTrue(len(self.wtp.variable_store) > 0, "Variable store is empty")
        self.wtp.start_page("clearstate")
        self.assertTrue(len(self.wtp.variable_store) == 0, "Variable store is not cleared")
    def test_variable_2(self):
        self.wtp.start_page("testvar")
        self.wtp.add_page(
            "Template:Testvar",
            10,
            "{{#vardefine:hello|world}}{{#vardefineecho:n|{{#expr:1+1}}}}",
        )
        self.assertEqual(
            self.wtp.expand(
                "{{Testvar}}"
            ),
            "2"
        )
        self.assertEqual(
            self.wtp.expand(
                "{{#var:hello|green}}{{#vardefine:n|{{#expr:{{#var:n|0}}+2}}}}{{#var:n}}"
            ),
            "world4"
        )
    def test_variable_varfinal(self):
        self.wtp.start_page("testvar")
        self.assertEqual(
            self.wtp.expand(
                "{{#var_final:foo}} {{#var:foo}} {{#vardefineecho:foo|bar}} {{#var:foo|bak}} {{#vardefine:foo|goo}}"
            ),
            "goo  bar bar "
        )
        self.assertEqual(
            self.wtp.expand(
                "{{#var_final:goo|red}} {{#var:goo|blue}}"
            ),
            "red blue"
        )
        self.assertEqual(
            self.wtp.expand(
                "{{#var_final:goo}} {{#var:goo|blue}}"
            ),
            " blue"
        )
