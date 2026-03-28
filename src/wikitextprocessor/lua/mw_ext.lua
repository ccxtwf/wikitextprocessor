-- Simplified sub implementation of mw.ext for running WikiMedia Scribunto
-- code under Python
--
-- Copyright (c) 2021 Tatu Ylonen.  See file LICENSE and https://ylonen.org

-- https://www.mediawiki.org/wiki/Extension:Scribunto/Lua_reference_manual#mw.ext.data
-- https://www.mediawiki.org/wiki/Extension:JsonConfig/Tabular
-- https://www.mediawiki.org/wiki/Help:Tabular_Data
local mw_ext = {
    data = {},
    ParserFunctions = {},
    seo = {},
    VariablesLua = {}
}

-- https://github.com/wikimedia/mediawiki-extensions-JsonConfig/blob/master/includes/JCLuaLibrary.php
function mw_ext.data.get(title, lang_code)
    return {
        license = "CC0-1.0",
        schema = { fields = {} },
        data = {},
    }
end


function mw_ext.ParserFunctions.expr(arg)
    local frame = mw.getCurrentFrame()
    return frame:callParserFunction("#expr", arg)
end

function mw_ext.seo.set()
    -- do nothing
    return ""
end

function mw_ext.VariablesLua.var(name, default)
    return variables_lua_var(name, default)
end

function mw_ext.VariablesLua.varexists(name)
    return variables_lua_varexists(name)
end

function mw_ext.VariablesLua.vardefine(name, value)
    variables_lua_vardefine(name, value)
end

function mw_ext.VariablesLua.vardefineecho(name, value)
    return variables_lua_vardefineecho(name, value)
end

function mw_ext.VariablesLua.var_final(name, value)
    return variables_lua_varfinal(name, value)
end

return mw_ext
