from unittest import TestCase
from unittest.mock import patch


class MockRequests:
    def __init__(self, ok, result):
        self.ok = ok
        self.result = result

    def json(self):
        return self.result


class TestLua(TestCase):
    def setUp(self):
        from wikitextprocessor import Wtp

        self.wtp = Wtp()

    def tearDown(self):
        self.wtp.close_db_conn()

    def test_fetchlanguage(self):
        self.wtp.add_page(
            "Module:test",
            828,
            body="""
            local export = {}
            function export.test()
              value = mw.language.fetchLanguageName("fr")
              value = value .. " " .. mw.language.fetchLanguageName("fr", "en")
              return value
            end
            return export
            """,
            model="Scribunto",
        )
        self.wtp.start_page("")
        self.assertEqual(
            self.wtp.expand("{{#invoke:test|test}}"), "français French"
        )

    def test_isolated_lua_env(self):
        # each Lua moudle uses by `#invoke` runs in cloned environment
        self.wtp.add_page(
            "Module:a",
            828,
            """
        local export = {}

        value = "a"

        function export.func()
          return mw.getCurrentFrame():expandTemplate{title="b"} .. " " .. value
        end

        return export
        """,
            model="Scribunto",
        )
        self.wtp.add_page(
            "Module:b",
            828,
            """
        local export = {}

        value = 'b'

        function export.func()
            return value
        end

        return export
        """,
            model="Scribunto",
        )
        self.wtp.add_page(
            "Module:c",
            828,
            """
        local export = {}

        function export.func()
            return value or "c"
        end

        return export
        """,
            model="Scribunto",
        )
        self.wtp.add_page("Template:a", 10, "{{#invoke:a|func}}")
        self.wtp.add_page("Template:b", 10, "{{#invoke:b|func}}")
        self.wtp.add_page(
            "Template:c", 10, "{{#invoke:b|func}} {{#invoke:c|func}}"
        )
        self.wtp.start_page("test lua env")
        self.assertEqual(self.wtp.expand("{{c}}"), "b c")
        self.assertEqual(self.wtp.expand("{{a}}"), "b a")

    def test_cloned_lua_env(self):
        # https://fr.wiktionary.org/wiki/responsable des services généraux
        # https://fr.wiktionary.org/wiki/Module:section
        self.wtp.add_page(
            "Module:a",
            828,
            """
        local export = {}

        b = require("Module:b")
        c = require("Module:c")

        function export.func()
            return c.func()
        end

        return export
        """,
            model="Scribunto",
        )
        self.wtp.add_page(
            "Module:b",
            828,
            """
        local export = {}

        function export.func()
            return "b"
        end

        return export
        """,
            model="Scribunto",
        )
        self.wtp.add_page(
            "Module:c",
            828,
            """
        local export = {}

        function export.func()
            return b.func()
        end

        return export
        """,
            model="Scribunto",
        )
        self.wtp.start_page("test lua env")
        self.assertEqual(self.wtp.expand("{{#invoke:a|func}}"), "b")

    @patch(
        "wikitextprocessor.interwiki.get_interwiki_data",
        return_value=[
            {
                "prefix": "en",
                "local": True,
                "language": "English",
                "bcp47": "en",
                "url": "https://en.wikipedia.org/wiki/$1",
                "protorel": False,
            }
        ],
    )
    def test_intewiki_map(self, mock_func):
        from wikitextprocessor.interwiki import init_interwiki_map

        init_interwiki_map(self.wtp)
        self.wtp.add_page(
            "Module:test",
            828,
            """
        local export = {}

        function export.test()
          return mw.site.interwikiMap().en.url
        end

        return export
        """,
        )
        self.wtp.start_page("test")
        self.assertEqual(
            self.wtp.expand("{{#invoke:test|test}}"),
            "https://en.wikipedia.org/wiki/$1",
        )

    def test_extension_tag_nowiki_strip_marker(self):
        # GitHub issue tatuylonen/wiktextract#238
        self.wtp.add_page(
            "Module:test",
            828,
            """
        local export = {}

        function export.test(frame)
          return frame:extensionTag("nowiki", "") ..
            frame:extensionTag("nowiki", "")
        end

        return export
        """,
        )
        self.wtp.start_page("test")
        self.assertEqual(
            self.wtp.expand("{{#invoke:test|test}}"),
            """\x7f'"`UNIQ--nowiki-00000000-QINU`"'\x7f"""
            """\x7f'"`UNIQ--nowiki-00000001-QINU`"'\x7f""",
        )

    def test_preprocess_heading_strip_marker(self):
        # GitHub issue tatuylonen/wiktextract#238
        self.wtp.add_page(
            "Module:test",
            828,
            """
        local export = {}

        function export.test(frame)
          return frame:preprocess("==a==") ..
            frame:preprocess("==a==") ..
            frame:preprocess("==b==") ..
            frame:preprocess("=b=")
        end

        return export
        """,
        )
        self.wtp.start_page("test")
        self.assertEqual(
            self.wtp.expand("{{#invoke:test|test}}"),
            """==\x7f'"`UNIQ--h-0-QINU`"'\x7fa=="""
            """==\x7f'"`UNIQ--h-0-QINU`"'\x7fa=="""
            """==\x7f'"`UNIQ--h-1-QINU`"'\x7fb=="""
            """=\x7f'"`UNIQ--h-2-QINU`"'\x7fb=""",
        )

    def test_mw_html(self):
        self.wtp.add_page(
            "Module:test",
            828,
            body="""
            local export = {}
            function export.test()
                local wikiHtml = mw.html.create( '' )
                wikiHtml:tag('span')
                        :wikitext('foo')
                        :done()
                return tostring(wikiHtml)
            end
            return export
            """,
            model="Scribunto",
        )
        self.wtp.start_page("")
        self.assertEqual(
            # Should not result in "<><span>foo</span>" or
            # <><span>foo</span></> due to the empty string in `create('')`
            self.wtp.expand("{{#invoke:test|test}}"),
            "<span>foo</span>",
        )

    def test_text_decode(self):
        # GH pr #244
        self.wtp.add_page(
            "Module:test",
            828,
            """
local export = {}
function export.test(frame)
  local a = mw.text.decode("&lt;-&vert;-&#124;-&#x7c;")
  local b = mw.text.decode("&lt;-&vert;-&#124;-&#x7c;", true)
  return a .. "--" .. b
end
return export""",
            model="Scribunto",
        )
        self.wtp.start_page("")
        self.assertEqual(
            self.wtp.expand("{{#invoke:test|test}}"), "<-&vert;-|-|--<-|-|-|"
        )

    def test_pass_nil_to_callParserFunction(self):
        # https://de.wiktionary.org/wiki/anachoreta
        # https://de.wiktionary.org/wiki/Modul:DateTime#L-1218
        self.wtp.add_page(
            "Module:test",
            828,
            """
local export = {}
function export.test(frame)
  return frame:callParserFunction("#tag", "a", "text", nil)
end
return export""",
            model="Scribunto",
        )
        self.wtp.start_page("")
        self.assertEqual(
            self.wtp.expand("{{#invoke:test|test}}"), "<a>text</a>"
        )

    def test_mw_loaddata_run_in_isolated_env(self):
        # GH issue #90, #258
        self.wtp.add_page(
            "Module:Citation/CS1",
            828,
            """
require ('strict');  -- check use of undefined global variable
local export = {}
function export.citation(frame)
  return mw.loadData('Module:Citation/CS1/Configuration');
end
return export""",
            model="Scribunto",
        )
        self.wtp.add_page(
            "Module:Citation/CS1/Configuration",
            828,
            """
uncategorized_namespaces_t = {[2]=true};  -- no error here
return "Configuration"
""",
            model="Scribunto",
        )
        self.wtp.start_page("")
        self.assertEqual(
            self.wtp.expand("{{#invoke:Citation/CS1|citation}}"),
            "Configuration",
        )

    def test_mw_load_json_data(self):
        self.wtp.add_page(
            "Module:test.json", 828, '{"key": "value"}', model="json"
        )
        self.wtp.add_page(
            "Module:test",
            828,
            """local export = {}
function export.test(frame)
  local data = mw.loadJsonData('Module:test.json')
  return data["key"]
end
return export""",
            model="Scribunto",
        )
        self.wtp.start_page("")
        self.assertEqual(self.wtp.expand("{{#invoke:test|test}}"), "value")

    def test_math_module_sum(self):
        # load "Module:math" not Lua's math library
        self.wtp.start_page("sea")
        self.wtp.add_page(
            "Module:math",
            828,
            """local export = {}
function export.sum(frame)
  return 1
end
return export""",
        )
        self.assertEqual(self.wtp.expand("{{#invoke:math|sum}}"), "1")

    def test_mw_uri_anchorEncode(self):
        # GH PR #276
        self.wtp.start_page("Reconstruction:Proto-Turkic/us-")
        self.wtp.add_page(
            "Module:test",
            828,
            """local export = {}
function export.test(frame)
  return mw.uri.anchorEncode("&#42;") .. mw.uri.anchorEncode("&#x2A;")
end
return export""",
        )
        self.assertEqual(self.wtp.expand("{{#invoke:test|test}}"), "**")

    def test_el_zero_arg(self):
        # https://el.wiktionary.org/wiki/Πρότυπο:ετ
        # Unnamed template parameters and numbered parameters can only
        # be positive non-zero integers; zero or "00" or negative is a string
        self.wtp.start_page("θηλυκός")
        self.wtp.add_page(
            "Module:test",
            828,
            """local export = {}
function export.test(frame)
  return tostring(frame.args['0']) .. "|" ..
         --tostring(frame.args[0]) .. "|" ..
         tostring(frame.args['00']) .. "|" ..
         tostring(frame.args[1]) .. "|" ..
         tostring(frame.args[2]) .. "|" ..
         tostring(frame.args['named'])
end
return export""",
        )
        self.assertEqual(
            self.wtp.expand(
                "{{#invoke:test|test|0= 0 |00= 00 | first |2= second |named= named }}"  # noqa: E501
            ),
            "0|00| first |second|named",
        )

    def test_el_strip_arg(self):
        self.wtp.start_page("θηλυκός")
        self.wtp.add_page(
            "Module:test",
            828,
            """local export = {}
function export.test(frame)
  return tostring(frame.args['foo'])
end
return export""",
        )
        self.assertEqual(
            self.wtp.expand("{{#invoke:test|test|foo=  {{#if||}} {{#if||}} }}"),
            "",
        )

    def test_mw_site_canonical_ns_key(self):
        # https://cs.wiktionary.org/wiki/Modul:Maintenance#L-193
        # `mw.site.namespaces.Category.name`
        self.wtp.start_page("")
        self.wtp.add_page(
            "Module:test",
            828,
            """local export = {}
function export.test(frame)
  return mw.site.namespaces.Project.name
end
return export""",
        )
        self.assertEqual(self.wtp.expand("{{#invoke:test|test}}"), "Vocaloid Lyrics Wiki")
