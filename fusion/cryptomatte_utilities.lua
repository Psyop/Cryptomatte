-- module table
cryptomatte_utilities = {}

-- ===========================================================================
-- constants
-- ===========================================================================
CJSON_LOADED = false
METADATA_PREFIX = "cryptomatte/"
METADATA_REGEX = "%a+/([a-z0-9]+)/(.+)"
MATTE_LIST_REGEX = "([^,]+),?%s*"
CHANNEL_KEY_NO_MATCH = "SomethingThatWontMatchHopefully"
CHANNEL_REGEX = "(.*)[.]([a-zA-Z]+)"

METADATA_KEY_FILENAME = "Filename"
METADATA_KEY_MANIF_FILE = "manif_file"
METADATA_KEY_MANIFEST = "manifest"
METADATA_KEY_NAME = "name"

-- ===========================================================================
-- third party modules
-- ===========================================================================
function prefered_load_json(c_module, lua_module)
    -- try to load cjson first, it's the fastest one (10x faster than simplejson)
    -- if cjson cannot be loaded, load simplejson
    -- if simplejson cannot be loaded, lua will raise an error
    local status, mod = pcall(require, c_module)
    if not status then
        mod = require(lua_module)
    else
        CJSON_LOADED = true
    end
    return mod
end

local json = prefered_load_json("cjson", "simplejson")
local struct = require("struct")

-- ===========================================================================
-- utils
-- ===========================================================================
function string_starts_with(str, start)
    return string.sub(str, 1, string.len(start)) == start
end

function is_key_in_table(key, table)
    for k, v in pairs(table) do
        if key == k then
            return true
        end
    end
    return false
end

function is_item_in_array(item, arr)
    local item_present = false
    for i, value in ipairs(arr) do
        if value == item then
            item_present = true
            break
        end
    end
    return item_present
end

function resolve_manifest_path(exr_path, sidecar_path)
    local exr_dir = exr_path:match("(.*/)")
    return exr_dir .. sidecar_path
end

function generate_mattes_from_rank(y)
    local global_p = Pixel()
    for x = 0, In.Width - 1 do
        In:GetPixel(x, y, global_p)

        local r_in_array = id_float_values[global_p.R]
        local b_in_array = id_float_values[global_p.B]
        if r_in_array or b_in_array then
            local local_p = Pixel()
            if r_in_array then
                local_p.R = 0.0
                local_p.G = global_p.G
            end
            if b_in_array then
                local_p.B = 0.0
                local_p.A = global_p.A
            end
            local_p.V = global_p.V * 2.0
            Out:SetPixel(x, y, local_p)
        end
    end
end

function create_matte_images(crypto_images, id_float_values)
    local combined_matte = Image({{ IMG_Channel = "Alpha" }})
    combined_matte:Clear()

    for i, image in ipairs(crypto_images) do
        local rank_matte = Image({ IMG_Like = image })
        rank_matte:Clear()

        -- process pixels to retrieve the pixels matching the id float value
        self:DoMultiProcess(nil, { In = image, Out = rank_matte, id_float_values = id_float_values }, image.Height, generate_mattes_from_rank)

        -- create mono channel output to store iterative matte in
        local i_matte = Image({ IMG_Like = image, IMG_CopyChannels = false, { IMG_Channel = "Alpha" } })
        i_matte = i_matte:ChannelOpOf("Add", rank_matte, { A = "fg.G" })
        i_matte = i_matte:ChannelOpOf("Add", rank_matte, { A = "fg.A" })

        -- add mono result to main output
        combined_matte = combined_matte:ChannelOpOf("Add", i_matte, { A = "fg.A" })
        combined_matte = combined_matte:ChannelOpOf("Add", rank_matte, { V = "fg.V" })
    end

    -- add combined matte to keyed image
    return combined_matte
end

-- ===========================================================================
-- CryptomatteInfo object
-- ===========================================================================
local CryptomatteInfo = {}
CryptomatteInfo.__index = CryptomatteInfo
-- call new function at object creation
setmetatable(CryptomatteInfo, {
    __call = function(cls)
        return cls:new()
    end
})
-- new function constructs object and declares variables
function CryptomatteInfo:new()
    local self = setmetatable({}, CryptomatteInfo)
    
    -- members
    self.selection = nil
    self.exr_path = nil
    self.cryptomattes = nil
    
    return self
end

-- functions
function CryptomatteInfo:extract_cryptomatte_metadata(metadata, selected_layer_name)
    -- extracts cryptomatte data from the given exr metadata
    local exr_path = ""
    local cryptomattes = {}
    
    local default_selection = nil
    local fallback_selection = nil
    
    local index = 0
    local index_to_layer_name = {}
    local layer_name_to_index = {}

    for k, v in pairs(metadata) do
        if string_starts_with(k, METADATA_PREFIX) then
            -- e.g. cryptomatte/0/name/uCryptoObject
            local metadata_id, partial_key = string.match(k, METADATA_REGEX)
            
            -- store cryptomatte data by metadata layver id
            if not is_key_in_table(metadata_id, cryptomattes) then
                cryptomattes[metadata_id] = {}
            end
            cryptomattes[metadata_id][partial_key] = v
            
            if partial_key == METADATA_KEY_NAME then
                index = index + 1
                index_to_layer_name[index] = v
                layer_name_to_index[v] = index
            end

            -- if the given selected layer name was found inside the metadata, store the id to
            -- set as default selection, else store current metadata layer id as fallback selection
            fallback_selection = metadata_id
            if partial_key == METADATA_KEY_NAME and v == selected_layer_name then
                default_selection = metadata_id
            end
        elseif k == METADATA_KEY_FILENAME then
            -- ensure all path separators are converted to single forward slash
            exr_path = v:gsub("([\\])", "/")
        end
    end
    
    self.nr_of_metadata_layers = index
    self.cryptomattes = cryptomattes
    self.index_to_layer_name = index_to_layer_name
    self.layer_name_to_index = layer_name_to_index

    -- set layer selection
    if default_selection ~= nil then
        self.selection = default_selection
    else
        self.selection = fallback_selection
    end

    -- store normalized exr path if found, else empty string
    self.exr_path = exr_path
end

function CryptomatteInfo:parse_manifest()
    -- load the manifest and translate ids and names out of it
    local from_names = {}
    local from_ids = {}
    local manifest
    local manifest_str = ""
    local all_names = {}

    local sidecar_path = self.cryptomattes[self.selection][METADATA_KEY_MANIF_FILE]
    if sidecar_path ~= nil then
        -- open the sidecar file in read mode
        local path = resolve_manifest_path(self.exr_path, sidecar_path)
        local fp = io.open(path, "r")
        if fp == nil then
            print(string.format('ERROR: following path does not exist: %s', path))
        else
            -- read all lines from file into a string
            manifest_str = fp:read("*all")
            -- close the file
            fp:close()
        end
    else
        manifest_str = self.cryptomattes[self.selection][METADATA_KEY_MANIFEST]
    end

    -- call module dependant decode function
    if CJSON_LOADED then
        manifest = json.decode(manifest_str)
    else
        manifest = json:decode(manifest_str)
    end

    -- json decode function returns nil when an empty string is passed to decode
    -- assert type of manifest is table to ensure value if valid
    -- if value is not valid, raise error to exit the process function
    assert(type(manifest) == "table", "invalid manifest")

    -- decrypt the hashes by name and store data
    for name, hex in pairs(manifest) do
        local packed = struct.pack("I", tonumber(hex, 16))
        -- if the length of the packed value is not 4 chars long
        -- append with empty "/0" char until value is 4 chars long
        while string.len(packed) < 4 do
            packed = "/0" .. packed
        end
        local id_float = struct.unpack("f", packed)
        local name_str = tostring(name)

        from_names[name_str] = id_float
        from_ids[id_float] = name_str
        all_names[name_str] = true
    end

    -- create name to id from hexadecimal value of names
    self.cryptomattes[self.selection]["name_to_id"] = from_names
    self.cryptomattes[self.selection]["id_to_name"] = from_ids
    self.cryptomattes[self.selection]["names"] = all_names
end

-- ===========================================================================
-- module
-- ===========================================================================
function cryptomatte_utilities:get_input_loader(tool)
    -- check if given tool is a loader
    if tool.ID == "Loader" then
        return tool
    end
    -- if tool was no loader, get first main input to check for loader
    local input = tool:FindMainInput(1)
    if input == nil then
        input = tool.Input
    end
    local connected_output = input:GetConnectedOutput()
    if not connected_output then
        return
    end
    local input_tool = connected_output:GetTool()
    if input_tool.ID == "Loader" then
        -- if connected tool is a loader, return the connected tool
        return input_tool
    else
        -- call function recursively on the connected tool to parse it's input
        -- for a loader
        return cryptomatte_utilities:get_input_loader(input_tool)
    end
end

function cryptomatte_utilities:get_all_channels_from_loader(cInfo, loader)
    local valid_channels = {}
    local loader_channel = loader.Clip1.OpenEXRFormat.RedName:GetAttrs().INPIDT_ComboControl_ID
    for i, channel in ipairs(loader_channel) do
        -- only store the channels containg the cryptomatte name metadata value
        if string.find(channel, cInfo.cryptomattes[cInfo.selection]["name"]) then
            table.insert(valid_channels, channel)
        end
    end
    return valid_channels
end

function cryptomatte_utilities:get_all_ranks_from_channels(channels)
    -- extract all channel data from connected loader
    local ranks = {}
    for i, channel_slot_v in ipairs(channels) do
        local rank_name, channel = string.match(channel_slot_v, CHANNEL_REGEX)
        if not is_key_in_table(rank_name, ranks) then
            ranks[rank_name] = {}
        end
        local _channel = channel:lower()
        if _channel == "r" or _channel == "red" then
            ranks[rank_name]["r"] = channel
        elseif _channel == "g" or _channel == "green" then
            ranks[rank_name]["g"] = channel
        elseif _channel == "b" or _channel == "blue" then
            ranks[rank_name]["b"] = channel
        elseif _channel == "a" or _channel == "alpha" then
            ranks[rank_name]["a"] = channel
        end
    end
    return ranks
end

function cryptomatte_utilities:set_channel_slots(loader, ranks)
    for rank, channels in pairs(ranks) do
        local index = string.match(rank, "[0-9]+$")
        if not index then
            -- no index, meaning default RGB crypto layer
            loader.Clip1.OpenEXRFormat.RedName[0] = string.format("%s.%s", rank, channels["r"])
            loader.Clip1.OpenEXRFormat.GreenName[0] = string.format("%s.%s", rank, channels["g"])
            loader.Clip1.OpenEXRFormat.BlueName[0] = string.format("%s.%s", rank, channels["b"])
            loader.Clip1.OpenEXRFormat.AlphaName[0] = CHANNEL_KEY_NO_MATCH
        else
            index = tonumber(index)
            if index == 0 then
                loader.Clip1.OpenEXRFormat.ZName[0] = string.format("%s.%s", rank, channels["r"])
                loader.Clip1.OpenEXRFormat.CovName[0] = string.format("%s.%s", rank, channels["g"])
                loader.Clip1.OpenEXRFormat.ObjIDName[0] = CHANNEL_KEY_NO_MATCH
                loader.Clip1.OpenEXRFormat.MatIDName[0] = CHANNEL_KEY_NO_MATCH
                loader.Clip1.OpenEXRFormat.UName[0] = string.format("%s.%s", rank, channels["b"])
                loader.Clip1.OpenEXRFormat.VName[0] = string.format("%s.%s", rank, channels["a"])
            elseif index == 1 then
                loader.Clip1.OpenEXRFormat.XNormName[0] = string.format("%s.%s", rank, channels["r"])
                loader.Clip1.OpenEXRFormat.YNormName[0] = string.format("%s.%s", rank, channels["g"])
                loader.Clip1.OpenEXRFormat.ZNormName[0] = string.format("%s.%s", rank, channels["b"])
                loader.Clip1.OpenEXRFormat.XVelName[0] = string.format("%s.%s", rank, channels["a"])
            elseif index == 2 then
                loader.Clip1.OpenEXRFormat.YVelName[0] = string.format("%s.%s", rank, channels["r"])
                loader.Clip1.OpenEXRFormat.XRevVelName[0] = string.format("%s.%s", rank, channels["g"])
                loader.Clip1.OpenEXRFormat.YRevVelName[0] = string.format("%s.%s", rank, channels["b"])
                loader.Clip1.OpenEXRFormat.XPosName[0] = string.format("%s.%s", rank, channels["a"])
            elseif index == 3 then
                loader.Clip1.OpenEXRFormat.YPosName[0] = string.format("%s.%s", rank, channels["r"])
                loader.Clip1.OpenEXRFormat.ZPosName[0] = string.format("%s.%s", rank, channels["g"])
                loader.Clip1.OpenEXRFormat.XDispName[0] = string.format("%s.%s", rank, channels["b"])
                loader.Clip1.OpenEXRFormat.YDispName[0] = string.format("%s.%s", rank, channels["a"])
            else
                error("cryptomatte does not support EXR images with 4 or more ranks")
            end
        end
    end
end

function cryptomatte_utilities:create_cryptomatte_info(metadata, selected_layer_name)
    -- create cryptomatte info and populate cryptomattes data from given metadata 
    cInfo = CryptomatteInfo() 
    cInfo:extract_cryptomatte_metadata(metadata, selected_layer_name)
    return cInfo
end

function cryptomatte_utilities:rebuild_matte(cInfo, matte_names, crypto_images)
    -- build a set from the ids of the given matte names
    local ids = {}
    local name_to_id = cInfo.cryptomattes[cInfo.selection]["name_to_id"]
    for name, _ in pairs(matte_names) do
        local id = name_to_id[name]
        if id then
            ids[id] = true
        end
    end
    
    -- create the combined matte image
    local combined_matte = nil
    if ids then
        combined_matte = create_matte_images(crypto_images, ids)
    end
    return combined_matte
end

-- return module
return cryptomatte_utilities