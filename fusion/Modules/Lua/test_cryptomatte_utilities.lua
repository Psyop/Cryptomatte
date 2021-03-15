--[[
Requires   : Fusion 9.0.2+
Optional   : cjson
Created by : Cédric Duriau         [duriau.cedric@live.be]
             Kristof Indeherberge  [xmnr0x23@gmail.com]
             Andrew Hazelden       [andrew@andrewhazelden.com]
Version    : 1.2.8
--]]

local cryptoutils = require("cryptomatte_utilities")
local json = require("dkjson")

-- utils
function collect_tests()
    --[[
    Returns function names detected as test.

    Functions with names starting with "test_" will be picked up.

    :rtype: table[stri]
    ]]
    local tests = {}
    local substr = "cryptomatte_test_"
    for name, _ in pairs(_G) do
        if string.sub(name, 1, string.len(substr)) == substr then
            table.insert(tests, name)
        end
    end
    table.sort(tests)
    return tests
end

function run_tests()
    --[[
    Detects and runs all test functions of a module.

    :param module: Module to run all tests for.
    :type module: table[string, function]
    ]]
    -- collect all tests from module
    print("collectings test(s) ...")
    local tests = collect_tests()
    local ntests = #tests
    print(string.format("detected %s test(s) ...", ntests))

    print("running tests ...")
    local count = 0
    for _, name in ipairs(tests) do
        count = count + 1

        -- build progess percentage
        local percentage = (count / ntests) * 100
        local percentage_str = string.format("%.0f%%", percentage)
        local padding = string.rep(" ", 4 - string.len(percentage_str))
        percentage_str = string.format("%s%s", padding, percentage_str)

        -- build test report
        local report = string.format("[%s] %s ... ", percentage_str, name)

        -- add leading spaces to allign results
        while report:len() < 60 do
            report = report.." "
        end

        -- safe call test function
        local status, err = pcall(_G[name])

        -- error handling & final report update
        if status then
            report = string.format("%s [%s]", report, "OK")
        else
            report = string.format("%s [%s]\n%s", report, "FAILED", err)
        end
        print(report)
    end
end

function assert_equal(x, y)
    --[[
    Tests the equality of two variables.

    :rtype: boolean
    ]]
    local _x, _y = x, y

    -- transform values for equality
    if type(x) == "table" and type(y) == "table" then
        _x = json.encode(_x)
        _y = json.encode(_y)
    end

    if _x == _y then
        return true
    else
        error(string.format("%s\nassertion failed: %s != %s", debug.traceback(), _x, _y))
    end
end

-- mock funtions
storage = {}

function mock_error(message)
    storage["error_return"] = message
end

function mock_print(message)
    storage["print_return"] = message
end

function mock_log_level_unset()
    return nil
end

function mock_log_level_error()
    return "0"
end

function mock_log_level_warning()
    return "1"
end

function mock_log_level_info()
    return "2"
end

mock_self_node = {Name="NODE1", Comp=fusion}

-- tests
function cryptomatte_test__format_log()
    local old_self = self
    self = mock_self_node
    assert_equal(cryptoutils._format_log("LEVEL", "MESSAGE"), "[Cryptomatte][NODE1][LEVEL] MESSAGE")
    self = old_self
end

function cryptomatte_test__get_log_level()
    -- store original function pre mock
    old_get_env = _G["os"]["getenv"]

    -- mock log level not set in environment
    _G["os"]["getenv"] = mock_log_level_unset
    local r1 = cryptoutils._get_log_level()
    _G["os"]["getenv"] = old_get_env
    assert_equal(r1, 1)

    -- mock log level info set in environment (string -> number cast)
    _G["os"]["getenv"] = mock_log_level_info
    local r2 = cryptoutils._get_log_level()
    _G["os"]["getenv"] = old_get_env
    assert_equal(r2, 2)
end

function cryptomatte_test__string_starts_with()
    assert_equal(cryptoutils._string_starts_with("foo_bar", "foo_"), true)
    assert_equal(cryptoutils._string_starts_with("foo_bar", "bar"), false)
end

function cryptomatte_test__string_ends_with()
    assert_equal(cryptoutils._string_ends_with("foo_bar", "_bar"), true)
    assert_equal(cryptoutils._string_ends_with("foo_bar", "foo"), false)
end

function cryptomatte_test__string_split()
    result = cryptoutils._string_split("foo, bar,bunny", "([^,]+),?%s*")
    assert_equal(#result, 3)
    expected = {"foo", "bar", "bunny"}
    for i, v in ipairs(result) do
        assert_equal(v, expected[i])
    end
end

function cryptomatte_test__get_absolute_path()
    -- store original pre mock
    old_self = _G["self"]

    -- mock
    _G["self"] = mock_self_node

    -- linux absolute path with forward path sep
    local r1 = cryptoutils._get_absolute_path("/tmp/test.exr")

    -- windows absolute path with double backward path sep
    local r2 = cryptoutils._get_absolute_path("C:\\Temp\\test.exr")

    -- windows absolute path with double backward path sep
    local r3 = cryptoutils._get_absolute_path("Temp:/test.exr")

    -- reset mock
    _G["self"] = old_self

    assert_equal(r1, "/tmp/test.exr")
    assert_equal(r2, "C:/Temp/test.exr")
    local pathsep = package.config:sub(1,1)
    if pathsep == "/" then
        assert_equal(r3, "/tmp/test.exr")
    else
        assert_equal(r3, "C:\\Temp\\test.exr")
    end
end

function cryptomatte_test__solve_channel_name()
    -- r
    assert_equal(cryptoutils._solve_channel_name("r"), "r")
    assert_equal(cryptoutils._solve_channel_name("R"), "r")
    assert_equal(cryptoutils._solve_channel_name("red"), "r")
    assert_equal(cryptoutils._solve_channel_name("RED"), "r")

    -- g
    assert_equal(cryptoutils._solve_channel_name("g"), "g")
    assert_equal(cryptoutils._solve_channel_name("G"), "g")
    assert_equal(cryptoutils._solve_channel_name("green"), "g")
    assert_equal(cryptoutils._solve_channel_name("GREEN"), "g")

    -- b
    assert_equal(cryptoutils._solve_channel_name("b"), "b")
    assert_equal(cryptoutils._solve_channel_name("B"), "b")
    assert_equal(cryptoutils._solve_channel_name("blue"), "b")
    assert_equal(cryptoutils._solve_channel_name("BLUE"), "b")

    -- a
    assert_equal(cryptoutils._solve_channel_name("a"), "a")
    assert_equal(cryptoutils._solve_channel_name("A"), "a")
    assert_equal(cryptoutils._solve_channel_name("alpha"), "a")
    assert_equal(cryptoutils._solve_channel_name("ALPHA"), "a")
end

function cryptomatte_test__get_channel_hierarchy()
    local channels = {
        {Name="Layer.R"},  -- will be skipped
        {Name="Layer.G"},  -- will be skipped
        {Name="Layer.B"},  -- will be skipped
        {Name="Layer.A"},  -- will be skipped
        {Name="Layer00.R"},
        {Name="Layer00.G"},
        {Name="Layer00.B"},
        {Name="Layer00.A"},
        {Name="Layer01.R"},
        {Name="Layer01.G"},
        {Name="Layer01.B"},
        {Name="Layer01.A"}
    }
    local result = cryptoutils._get_channel_hierarchy("Layer", channels)
    local expected = {}
    expected["Layer"] = {}
    expected["Layer"]["0"] = {r="Layer00.R",g="Layer00.G",b="Layer00.B",a="Layer00.A"}
    expected["Layer"]["1"] = {r="Layer01.R",g="Layer01.G",b="Layer01.B",a="Layer01.A"}
    assert_equal(result, expected)
end

function cryptomatte_test__get_absolute_position()
    local x, y = cryptoutils._get_absolute_position(10, 10, 0.5, 0.5)
    assert_equal(x, 5)
    assert_equal(y, 5)
end

function cryptomatte_test__is_position_in_rect()
    -- NOTE: fusion rectangles follow mathematical convention, (origin=left,bottom)
    local rect = {left=0, top=10, right=10, bottom=0}
    assert_equal(cryptoutils._is_position_in_rect(rect, 5, 5), true)
    assert_equal(cryptoutils._is_position_in_rect(rect, 12, 5), false)
    assert_equal(cryptoutils._is_position_in_rect(rect, 5, 12), false)
end

function cryptomatte_test__hex_to_float()
    assert_equal(cryptoutils._hex_to_float("3f800000"), 1.0)
    assert_equal(cryptoutils._hex_to_float("bf800000"), -1.0)
end

function cryptomatte_test_log_error()
    -- store original pre mock
    old_get_env = _G["os"]["getenv"]
    old_self = self
    old_print = _G["print"]
    old_error = _G["error"]

    -- mock
    _G["os"]['getenv'] = mock_log_level_error
    self = mock_self_node
    _G["print"] = mock_print
    _G["error"] = mock_error

    cryptoutils.log_error("HELP")

    -- reset mock
    _G["os"]["getenv"] = old_get_env
    self = old_self
    _G["print"] = old_print
    _G["error"] = old_error

    assert_equal(storage["print_return"], "[Cryptomatte][NODE1][ERROR] HELP")
    assert_equal(storage["error_return"], "ERROR")
end

function cryptomatte_test_log_warning()
    -- store original pre mock
    old_get_env = _G["os"]["getenv"]
    old_self = self
    old_print = _G["print"]

    -- mock with matching log level
    _G["os"]['getenv'] = mock_log_level_warning
    self = mock_self_node
    _G["print"] = mock_print

    cryptoutils.log_warning("HELP")
    local pr1 = storage["print_return"]
    storage["print_return"] = nil  -- clear print result for next run

    -- mock with non matching log level
    _G["os"]['getenv'] = mock_log_level_error

    cryptoutils.log_warning("HELP")
    local pr2 = storage["print_return"]

    -- reset mock
    _G["os"]["getenv"] = old_get_env
    self = old_self
    _G["print"] = old_print

    assert_equal(pr1, "[Cryptomatte][NODE1][WARNING] HELP")
    assert_equal(pr2, nil)  -- never got called
end

function cryptomatte_test_log_info()
    -- store original pre mock
    old_get_env = _G["os"]["getenv"]
    old_self = self
    old_print = _G["print"]

    -- mock
    _G["os"]['getenv'] = mock_log_level_info
    self = mock_self_node
    _G["print"] = mock_print

    cryptoutils.log_info("HELP")
    local pr1 = storage["print_return"]
    storage["print_return"] = nil  -- clear print result for next run

    -- mock with non matching log level
    _G["os"]['getenv'] = mock_log_level_unset

    cryptoutils.log_info("HELP")
    local pr2 = storage["print_return"]

    -- reset mock
    _G["os"]["getenv"] = old_get_env
    self = old_self
    _G["print"] = old_print

    assert_equal(pr1, "[Cryptomatte][NODE1][INFO] HELP")
    assert_equal(pr2, nil)  -- never got called
end

function cryptomatte_test_get_cryptomatte_metadata()
    local metadata = {}
    metadata["cryptomatte/123456/conversion"] = "uint32_to_float32"
    metadata["cryptomatte/123456/hash"] = "MurmurHash3_32"
    metadata["cryptomatte/123456/manifest"] = "{\"bunny\": \"3f800000\"}"
    metadata["cryptomatte/123456/name"] = "Layer"
    metadata["Filename"] = "/tmp/foo"

    -- store original pre mock
    old_self = _G["self"]

    -- mock
    _G["self"] = mock_self_node

    local result = cryptoutils.get_cryptomatte_metadata(metadata)

    -- reset mock
    _G["self"] = old_self

    local expected = {}
    expected["path"] = "/tmp/foo"
    expected["layer_count"] = 1
    expected["id_to_name"] = {}
    expected["id_to_name"]["123456"]="Layer"
    expected["name_to_id"] = {}
    expected["name_to_id"]["Layer"] = "123456"
    expected["index_to_id"] = {}
    expected["index_to_id"]["1"] = "123456"
    expected["id_to_index"] = {}
    expected["id_to_index"]["123456"] = "1"
    expected["layers"] = {}
    expected["layers"]["123456"] = {}
    expected["layers"]["123456"]["conversion"] = "uint32_to_float32"
    expected["layers"]["123456"]["hash"] = "MurmurHash3_32"
    expected["layers"]["123456"]["manifest"] = "{\"bunny\": \"3f800000\"}"
    expected["layers"]["123456"]["name"] = "Layer"
    assert_equal(result, expected)
end

function cryptomatte_test_read_manifest_file()
    -- valid manifest file
    local tmp_file = os.tmpname()
    local fp = io.open(tmp_file, "w")
    fp:write("{\"bunny\": \"3f800000\"}")
    fp:close()

    local dir, file = string.match(tmp_file, "(.-)([^\\/]-%.?[^%.\\/]*)$")
    local result = cryptoutils.read_manifest_file(dir, file)
    os.remove(tmp_file)
    assert_equal(result, "{\"bunny\": \"3f800000\"}")

    -- invalid manifest file, file does not exist
    -- store original pre mock
    old_print = _G["print"]
    old_self = self
    old_error = _G["error"]

    -- mock
    _G["print"] = mock_print
    self = mock_self_node
    _G["error"] = mock_error

    local result = cryptoutils.read_manifest_file(dir, file)

    -- reset mock
    _G["print"] = old_print
    self = old_self
    _G["error"] = old_error

    assert_equal(result, "")
end

function cryptomatte_test_decode_manifest()
    local result = cryptoutils.decode_manifest("{\"bunny\": \"3f800000\"}")
    assert_equal(result, {bunny="3f800000"})
end

function cryptomatte_test_get_matte_names()
    -- valid single name string
    assert_equal(cryptoutils.get_matte_names("\"bunny\""), {bunny=true})

    -- valid multiple names string
    assert_equal(cryptoutils.get_matte_names("\"bunny\", \"flower\""), {bunny=true, flower=true})

    -- valid name string with numbers
    assert_equal(cryptoutils.get_matte_names("\"bunny123\""), {bunny123=true})

    -- valid name string with escaped quotes (single & double)
    local result = cryptoutils.get_matte_names("\"bunny'\"\"")
    local expected = {}
    expected["bunny'\""] = true
    assert_equal(result, expected)

    -- valid name string with spaces
    result = cryptoutils.get_matte_names("\"b u n n y\"")
    expected = {}
    expected["b u n n y"] = true
    assert_equal(result, expected)

    -- valid name string with special characters
    result = cryptoutils.get_matte_names("\"bunny?!\"")
    expected = {}
    expected["bunny?!"] = true
    assert_equal(result, expected)

    -- valid name string with latin encoding characters
    result = cryptoutils.get_matte_names("\"itsabunnyé\"")
    expected = {}
    expected["itsabunnyé"] = true
    assert_equal(result, expected)

    -- valid name string in Russian cyrillic
    result = cryptoutils.get_matte_names("\"кролик\"")
    expected = {}
    expected["кролик"] = true
    assert_equal(result, expected)

    -- invalid name strings
    -- store original pre mock
    old_self = self
    old_print = _G["print"]

    -- mock
    self = mock_self_node
    _G["print"] = mock_print

    local no_quotes = cryptoutils.get_matte_names("bunny")
    local comma = cryptoutils.get_matte_names("bu,nny")

    -- reset mock
    self = old_self
    _G["print"] = old_print

    assert_equal(no_quotes, {})
    assert_equal(comma, {})
end

run_tests()
