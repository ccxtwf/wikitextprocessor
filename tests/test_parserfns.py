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
        # Assert simple variable usage is possible
        self.assertEqual(
            self.wtp.expand(
                "{{#var:foo}} {{#var:foo|bar}} {{#vardefineecho:foo|baz}} {{#var:foo|bar}} {{#vardefine:foo|goo}} {{#var:foo}}"
            ),
            " bar baz baz  goo"
        )
        # Assert variable store is not cleared until a page is restarted
        self.assertTrue(len(self.wtp.variable_store) > 0, "Variable store is empty")
        self.wtp.start_page("clearstate")
        self.assertTrue(len(self.wtp.variable_store) == 0, "Variable store is not cleared")

    def test_variable_2(self):
        self.wtp.start_page("testvar")
        # Assert simple variable usage in template transclusions is possible
        self.wtp.add_page(
            "Template:Testvar",
            10,
            "{{#vardefine:hello|world}}{{#vardefineecho:n| {{#expr: 1 + 1 }} }}",
        )
        self.assertEqual(
            self.wtp.expand(
                "{{Testvar}}"
            ),
            "2"
        )
        # Assert variable store is not cleared until a page is restarted
        self.assertTrue(len(self.wtp.variable_store) > 0, "Variable store is empty")

    def test_variable_3(self):
        test_cases = [
            # assert that expansion in parser func arguments works correctly
            (
                "{{#var:foo1| {{#expr: 0 - 1 }} }} {{#vardefine:foo1| {{#expr: 1 + 1 }} }} {{#var:foo1| {{#expr: 0 - 1 }} }} {{#vardefineecho:foo2| {{#expr: 2 + 3 }} }}",
                "-1  2 5"
            ),
            (
                "{{#vardefine:i|1}}{{#var:foo{{#var:i}}|{{#expr: 0 - 1 }}}} {{#vardefine:foo1|{{#expr: 1 + 1 }}}} {{#var:foo{{#var:i}}|{{#expr: 0 - 1 }}}} {{#vardefineecho:foo{{#expr:1+1}}|{{#expr: 2 + 3 }}}}",
                "-1  2 5"
            ),

            # assert that whitespace does not affect expansion in parser func arguments
            (
                "{{#var: foo1\n|{{#expr: 0 - 1 }}}} {{#vardefine: foo1\n|{{#expr: 1 + 1 }}}} {{#var: foo1\n|{{#expr: 0 - 1 }}}} {{#vardefineecho: foo2\n|{{#expr: 2 + 3 }}}}",
                "-1  2 5"
            ),

            # Extra tests
            (
                "{{#vardefine:n|{{#expr:{{#var:n|0}}+2}}}}{{#var:n}}",
                "2"
            ),
            (
                "{{#vardefine:foo1|{{#expr:1+1}}}}{{#vardefine:foo{{#var:foo1}}|world{{#expr:2+3}}}}foo{{#var:foo1}}={{#var:foo{{#var:foo1}}}}",
                "foo2=world5"
            )
        ]
        for wikitext, result in test_cases:
            self.wtp.start_page("testvar")
            assert(len(self.wtp.variable_store) == 0)
            with self.subTest(wikitext=wikitext, result=result):
                self.assertEqual(self.wtp.expand(wikitext), result)

    def test_variable_varfinal(self):
        test_cases = [
            (
                "{{#var_final:foo}} {{#var:foo}} {{#vardefineecho:foo|bar}} {{#var:foo|bak}} {{#vardefine:foo|goo}}",
                "goo  bar bar "
            ),
            (
                "{{#var_final:foo}} {{#var:foo}} {{#vardefineecho:foo|{{#expr:1+3}}}} {{#var:foo|{{#expr:2+4}}}} {{#vardefine:foo|{{#expr:3+6}}}}",
                "9  4 4 "
            ),
            (
                "{{#var_final:goo|red}} {{#var:goo|blue}}",
                "red blue"
            ),
            (
                "{{#var_final:goo|{{#expr: 20 + 1 }}}} {{#var:goo|blue}}",
                "21 blue"
            ),
            (
                "{{#var_final:goo}} {{#var:goo|blue}}",
                " blue"
            )
        ]
        for wikitext, result in test_cases:
            self.wtp.start_page("testvar")
            assert(len(self.wtp.variable_store) == 0)
            with self.subTest(wikitext=wikitext, result=result):
                self.assertEqual(self.wtp.expand(wikitext), result)

    def test_loops_while(self):
        test_cases = [
            (
                "{{#vardefine:i|0}}{{#while:|{{#ifexpr:{{#var:i}} < 5|true}}|<nowiki />\n* {{#var:i}}{{#vardefine:i|{{#expr: {{#var:i}} + 1 }}}}}}",
                "<nowiki />\n* 0<nowiki />\n* 1<nowiki />\n* 2<nowiki />\n* 3<nowiki />\n* 4"
            ),
            (
                "{{#vardefine:i|6}}{{#while:|{{#ifexpr:{{#var:i}} < 5|true}}|<nowiki />\n* {{#var:i}}{{#vardefine:i|{{#expr: {{#var:i}} + 1 }}}}}}",
                ""
            )
        ]
        for wikitext, result in test_cases:
            self.wtp.start_page("testwhile")
            assert(len(self.wtp.variable_store) == 0)
            with self.subTest(wikitext=wikitext, result=result):
                self.assertEqual(self.wtp.expand(wikitext), result)

    def test_loops_dowhile(self):
        test_cases = [
            (
                "{{#vardefine:i|0}}{{#dowhile:|{{#ifexpr: {{#var: i }} < 5|true}}|<nowiki />\n* {{#var:i}}{{#vardefine:i|{{#expr: {{#var:i}} + 1 }} }}}}",
                "<nowiki />\n* 0<nowiki />\n* 1<nowiki />\n* 2<nowiki />\n* 3<nowiki />\n* 4"
            ),
            (
                "{{#vardefine:i|5}}{{#dowhile:|{{#ifexpr:{{#var: i }} < 5|true}}|<nowiki />\n* {{#var:i}}{{#vardefine:i| {{#expr: {{#var:i}} + 1 }} }}}}",
                "<nowiki />\n* 5"
            )
        ]
        for wikitext, result in test_cases:
            self.wtp.start_page("testdowhile")
            assert(len(self.wtp.variable_store) == 0)
            with self.subTest(wikitext=wikitext, result=result):
                self.assertEqual(self.wtp.expand(wikitext), result)

    def test_loops_loop(self):
        self.wtp.start_page("testdowhile")
        self.assertEqual(
            self.wtp.expand(
                "{{#loop: varname\n | 4\n | 4\n | <nowiki />\n* This is round {{#var: varname }} and we have {{#expr: 7 - {{#var: varname }} }} more to go\n}}"
            ),
            "<nowiki />\n* This is round 4 and we have 3 more to go<nowiki />\n* This is round 5 and we have 2 more to go<nowiki />\n* This is round 6 and we have 1 more to go<nowiki />\n* This is round 7 and we have 0 more to go"
        )
