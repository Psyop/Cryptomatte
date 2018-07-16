--[[
Requires   : Fusion 9.0.1+
Optional   : cjson
Created by : Cédric Duriau         [duriau.cedric@live.be]
             Kristof Indeherberge  [xmnr0x23@gmail.com]
             Andrew Hazelden       [andrew@andrewhazelden.com]
Version    : 1.2.1
--]]

-- module table
cryptomatte_utilities = {}

-- ===========================================================================
-- constants
-- ===========================================================================
REGEX_METADATA = "%a+/([a-z0-9]+)/(.+)"
REGEX_MATTE_LIST = "([^,]+),?%s*"
REGEX_RANK_CHANNEL = "(.+)[.](.+)"
METADATA_PREFIX = "cryptomatte/"
METADATA_KEY_NAME = "name"
METADATA_KEY_MANIFEST = "manifest"
METADATA_KEY_FILENAME = "Filename"
METADATA_KEY_MANIF_FILE = "manif_file"

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
    end
    return mod
end

local json = prefered_load_json("cjson", "dkjson")

-- ===========================================================================
-- ffi C utils
-- ===========================================================================
-- int / float representation of hash
ffi.cdef[[ union int_flt { uint32_t i; float f; }; ]]
local int_flt = ffi.new("union int_flt")

-- ===========================================================================
-- utils
-- ===========================================================================
function string_starts_with(str, start)
    -- check if the given string stars with the given start substring
    return string.sub(str, 1, string.len(start)) == start
end

function convert_str_to_array(str, pattern)
    -- convert matte selection list in str format to set
    local matte_names = {}
    for matte in string.gmatch(str, pattern) do
        -- strip the leading and trailing double quote
        matte = string.sub(matte, 2, matte:len() - 1)
        table.insert(matte_names, matte)
    end
    return matte_names
end

function is_key_in_table(key, table)
    -- checks if the given key is in the given table
    for k, v in pairs(table) do
        if key == k then
            return true
        end
    end
    return false
end

function is_item_in_array(item, arr)
    -- checks if the given item is in the given array
    local item_present = false
    for i, value in ipairs(arr) do
        if value == item then
            item_present = true
            break
        end
    end
    return item_present
end

function build_manifest_path(exr_path, sidecar_path)
    -- builds the manifest path from the directory of the given exr path
    -- and joins it with the given relative sidecar path
    local exr_dir = exr_path:match("(.*/)")
    return exr_dir .. sidecar_path
end

function get_screen_pixel(img, x, y)
    -- get the pixel at given location of given image
    local p = Pixel()
    local pixel_x = math.floor(img.Width / (1 / x))
    local pixel_y = math.floor(img.Height / (1 / y))
    img:GetPixel(pixel_x, pixel_y, p)
    return p
end

function generate_mattes_from_rank_init()
    -- init function used to run before the scanline function "generate_mattes_from_rank"
    -- creates pixel pointer objects instead of creating pixel object for every coordinat to improve peformance
    global_p = Pixel()
    local_p = Pixel()

    pixptr_in = PixPtr(In, global_p)
    pixptr_out = PixPtr(Out, local_p)
end

function generate_mattes_from_rank(y)
    -- scanline function used to generates matte from every cryptomatte rank
    -- goto position X=0,Y=y pixel location
    pixptr_in:GotoXY(0, y)
    pixptr_out:GotoXY(0, y)

    for x = 0, In.Width - 1 do
        -- goto correct X pos
        pixptr_in:GetNextPixel(global_p)
        
        -- reset pixel RGBA values
        local_p.R = 0.0
        local_p.G = 0.0
        local_p.B = 0.0
        local_p.A = 0.0

        -- check if id float value occurs in R or B channel value
        local r_in_array = id_float_values[global_p.R]
        local b_in_array = id_float_values[global_p.B]
        if r_in_array or b_in_array then
            -- rank pair match R counterpart is G
            if r_in_array then
                local_p.G = global_p.G
            end
            -- rank pair match B counterpart is A
            if b_in_array then
                local_p.A = global_p.A
            end
            -- set output pixel pointer to match
            pixptr_out:SetNextPixel(local_p)
        else
            -- continue if no match was found
            pixptr_out:NextPixel()
        end
    end
end

function create_colors_image_init()
    -- initializer function that gets called before the scanline function "create_colors_image_init"
    -- creates pixel pointer objects instead of creating pixel object for every coordinat to improve peformance
    global_p_c00 = Pixel()
    global_p_c01 = Pixel()
    local_p = Pixel()

    -- rank 00
    pixptr_00 = PixPtr(rank_img_00, global_p_c00)
    -- rank 01
    pixptr_01 = PixPtr(rank_img_01, global_p_c01)
    pixptr_out = PixPtr(output, local_p)
end

function create_colors_image(y)
    -- scanline function used to generates matte from every cryptomatte rank
    -- goto position X=0,Y=y pixel location
    pixptr_00:GotoXY(0, y)
    pixptr_01:GotoXY(0, y)
    pixptr_out:GotoXY(0, y)

    for x = 0, output.Width - 1 do
         -- goto correct X pos
        pixptr_00:GetNextPixel(global_p_c00)
        pixptr_01:GetNextPixel(global_p_c01)

        -- get mantissa of R and B channels of both rank 0 and 1
        m00_rg, _ = math.frexp(math.abs(global_p_c00.R))
        m00_ba, _ = math.frexp(math.abs(global_p_c00.B))
        m01_rg, _ = math.frexp(math.abs(global_p_c01.R))
        m01_ba, _ = math.frexp(math.abs(global_p_c01.B))

        -- calculate RGB channel values for final id colored image
        -- red
        r_c00_rg = (m00_rg * 1 % 0.25) * global_p_c00.G
        r_c00_ba = (m00_ba * 1 % 0.25) * global_p_c00.A
        r_c01_rg = (m01_rg * 1 % 0.25) * global_p_c01.G
        r_c01_ba = (m01_ba * 1 % 0.25) * global_p_c01.A
        red = r_c00_rg + r_c00_ba + r_c01_rg + r_c01_ba

        -- green
        g_c00_rg = (m00_rg * 4 % 0.25) * global_p_c00.G
        g_c00_ba = (m00_ba * 4 % 0.25) * global_p_c00.A
        g_c01_rg = (m01_rg * 4 % 0.25) * global_p_c01.G
        g_c01_ba = (m01_ba * 4 % 0.25) * global_p_c01.A
        green = g_c00_rg + g_c00_ba + g_c01_rg + g_c01_ba

        -- blue
        b_c00_rg = (m00_rg * 16 % 0.25) * global_p_c00.G
        b_c00_ba = (m00_ba * 16 % 0.25) * global_p_c00.A
        b_c01_rg = (m01_rg * 16 % 0.25) * global_p_c01.G
        b_c01_ba = (m01_ba * 16 % 0.25) * global_p_c01.A
        blue = b_c00_rg + b_c00_ba + b_c01_rg + b_c01_ba

        -- store calculated R,G and B values
        local_p.R = red
        local_p.G = green
        local_p.B = blue

        -- set output pixel pointer
        pixptr_out:SetNextPixel(local_p)
    end
end

function create_mattes(crypto_images, id_float_values, output_image)
    local combined_matte = Image({ IMG_Like = output_image, IMG_CopyChannels = false, { IMG_Channel = "Alpha" } })
    combined_matte:Clear()

    for _, image in pairs(crypto_images) do
        local rank_matte = image:CopyOf()
        rank_matte:Clear()

        -- process pixels to retrieve the pixels matching the id float value
        self:DoMultiProcess(generate_mattes_from_rank_init, { In = image, Out = rank_matte, id_float_values = id_float_values }, image.Height, generate_mattes_from_rank)

        -- create mono channel output to store iterative matte in
        local i_matte = Image({ IMG_Like = image, IMG_CopyChannels = false, { IMG_Channel = "Alpha" } })
        i_matte = i_matte:ChannelOpOf("Add", rank_matte, { A = "fg.G" })
        i_matte = i_matte:ChannelOpOf("Add", rank_matte, { A = "fg.A" })

        -- add mono result to main output
        combined_matte = combined_matte:ChannelOpOf("Add", i_matte, { A = "fg.A" })
    end

    return combined_matte
end

function create_preview_image(input_image, rank_img_00, rank_img_01)
    -- creates the preview image from the first two ranks
    -- this function was at first attached to the module like functions at the end of this module
    -- this did not work due to the "self" then taking the role of the module, instead of the Fuse
    local output = input_image:CopyOf()
    output:Clear()
    self:DoMultiProcess(create_colors_image_init, { output = output, rank_img_00 = rank_img_00, rank_img_01 = rank_img_01 }, output.Height, create_colors_image)
    return output
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
    self.nr_of_metadata_layers = nil
    self.cryptomattes = nil
    self.index_to_layer_name = nil
    self.layer_name_to_index = nil
    self.selection = nil
    self.exr_path = nil

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
            local metadata_id, partial_key = string.match(k, REGEX_METADATA)

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

function CryptomatteInfo:get_manifest_string()
    local sidecar_path = self.cryptomattes[self.selection][METADATA_KEY_MANIF_FILE]
    if sidecar_path ~= nil then
        -- open the sidecar file in read mode
        local path = build_manifest_path(self.exr_path, sidecar_path)
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
    return manifest_str
end

function CryptomatteInfo:parse_manifest()
    -- load the manifest and translate ids and names out of it
    local from_names = {}
    local from_ids = {}
    local all_names = {}
    local all_ids = {}
    
    -- get manifest str
    local manifest_str = self:get_manifest_string()
    
    -- decode json str to table
    local manifest = json.decode(manifest_str)

    -- json decode function returns nil when an empty string is passed to decode
    -- assert type of manifest is table to ensure value if valid
    -- if value is not valid, raise error to exit the process function
    assert(type(manifest) == "table", "invalid manifest")

    -- decrypt the hashes by name and store data
    for name, hex in pairs(manifest) do
        int_flt.i = tonumber(hex, 16)
        local id_float = int_flt.f
        local name_str = tostring(name)
        
        from_names[name_str] = id_float
        from_ids[id_float] = name_str

        all_names[name_str] = true
        all_ids[id_float] = true
    end

    -- create name to id from hexadecimal value of names
    self.cryptomattes[self.selection]["name_to_id"] = from_names
    self.cryptomattes[self.selection]["id_to_name"] = from_ids
    self.cryptomattes[self.selection]["names"] = all_names
    self.cryptomattes[self.selection]["ids"] = all_ids
end

function exr_read_channels(exr, partnum, crypto_layer)
    -- retrieve all exr channels filtering on given layer name
    local channel_names = {}
    local channels = exr:GetChannels(partnum)
    for i, channel in ipairs(channels) do
        local channel_name = channel["Name"]
        if string.find(channel_name, crypto_layer) then
            table.insert(channel_names, channel_name)
        end
    end
    return channel_names
end

function get_channels_by_index(exr_channels)
    -- gets all the cryptomatte required channels by rank index and short channel name (r, g, b, a)
    local by_index = {}
    for i, channel in ipairs(exr_channels) do
        -- get rank and channel name from channel
        local rank, name = string.match(channel, REGEX_RANK_CHANNEL)

        if rank ~= nil and name ~= nil then
            -- get index from rank
            local index = string.match(rank, "[0-9]+$")

            if index ~= nil then
                -- first tonumber to avoid leading numbers, then tostring again to ensure string keys
                index = tostring(tonumber(index))

                if not is_key_in_table(index, by_index) then
                    by_index[index] = {}
                end

                -- store the rank channels under respective short form
                local _channel = string.lower(name)
                if _channel == "r" or _channel == "red" then
                    by_index[index]["r"] = channel
                elseif _channel == "g" or _channel == "green" then
                    by_index[index]["g"] = channel
                elseif _channel == "b" or _channel == "blue" then
                    by_index[index]["b"] = channel
                elseif _channel == "a" or _channel == "alpha" then
                    by_index[index]["a"] = channel
                end
            end
        end
    end
    return by_index
end

function exr_read_channel_parts(exr, input_image, cryptomatte_channels, partnum)
    -- creates an image from the given cryptomatte channels by rank
    local cryptomatte_images = {}
    
    -- read part with given index
    exr:Part(partnum)

    for index, channels in pairs(cryptomatte_channels) do
        -- create placeholder image, set resolution to original input width & height
        local image = Image({
            IMG_Width = input_image.OriginalWidth,
            IMG_Height = input_image.OriginalHeight,
            IMG_ProxyScale = 1,  -- don't apply the proxy
            IMG_Depth = IMDP_128bitFloat  -- force image to 32bit float (4 channel 128bit float)
        })
        
        -- read rank RGBA channels
        exr:Channel(channels["r"], ANY_TYPE, image, CHAN_RED)
        exr:Channel(channels["g"], ANY_TYPE, image, CHAN_GREEN)
        exr:Channel(channels["b"], ANY_TYPE, image, CHAN_BLUE)
        exr:Channel(channels["a"], ANY_TYPE, image, CHAN_ALPHA)

        -- store the image as value to the rank index in string format as key
        cryptomatte_images[tostring(index)] = image
    end

    if cryptomatte_images ~= {} then
        -- fill the given image with previously read information
        exr:ReadPart(partnum, cryptomatte_images)
    end

    -- handle proxy scale
    if input_image.ProxyScale ~= 1 then
        local width = input_image.Width
        local height = input_image.Height

        for index, image in pairs(cryptomatte_images) do
            -- create placeholder result image correct by scale
            result = Image({
                IMG_Like = image,
                IMG_Width = width,
                IMG_Height = height
            })
            
            -- resize image to proxy scaled resolution (nearest neighbor filter algorithm)
            image:Resize(result, {
                RSZ_Filter = "Nearest",
                RSZ_Width = width,
                RSZ_Height = height
            })
            
            -- store result
            cryptomatte_images[index] = result
        end
    end

    return cryptomatte_images
end

-- ===========================================================================
-- module
-- ===========================================================================
function cryptomatte_utilities:create_cryptomatte_info(metadata, selected_layer_name)
    -- create cryptomatte info and populate cryptomattes data from given metadata
    cInfo = CryptomatteInfo()
    cInfo:extract_cryptomatte_metadata(metadata, selected_layer_name)
    return cInfo
end

function cryptomatte_utilities:get_id_float_value(cInfo, screen_pos, crypto_images, input_image)
    -- get the pixel at the given location for all the given crypto images (ranks)
    -- if an R, G, B or A channel value is different than zero, the id float value was found
    local id_float_value = nil
    
    -- sort keys
    local keys = {}
    for k in pairs(crypto_images) do 
        table.insert(keys, tonumber(k)) 
    end
    table.sort(keys)

    for _, index in ipairs(keys) do
        local image = crypto_images[tostring(index)]
        local pixel = get_screen_pixel(image, screen_pos.X, screen_pos.Y)

        -- matte value
        for _, val in ipairs({pixel.R, pixel.G, pixel.B, pixel.A}) do
            if val ~= 0.0 and cInfo.cryptomattes[cInfo.selection]["ids"][val] then
                id_float_value = val
                break
            end
        end
        if id_float_value ~= nil then break end
    end
    
    if id_float_value == nil then
        -- check if the background is being parsed (RGB=0,0,0)
        local pixel = get_screen_pixel(input_image, screen_pos.X, screen_pos.Y)
        if pixel.R == 0.0 and pixel.G == 0.0 and pixel.B == 0.0 then
            id_float_value = 0.0
        end
    end

    return id_float_value
end

function cryptomatte_utilities:create_matte_image(cInfo, matte_names, crypto_images, output_image)
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
        combined_matte = create_mattes(crypto_images, ids, output_image)
    end
    return combined_matte
end

function cryptomatte_utilities:create_preview_image(input_image, rank_img_00, rank_img_01)
    -- creates the preview image
    local output = create_preview_image(input_image, rank_img_00, rank_img_01)
    return output
end

function cryptomatte_utilities:get_all_rank_images(cInfo, layer_name, input_image)
    local partnum = 1
    local crypto_images = {}

    -- create EXRIO pointer
    local exr = EXRIO()

    -- read the input exr
    exr:ReadOpen(cInfo.exr_path, -1)

    if exr:ReadHeader() then
        -- get the channel names
        local exr_channel_names = exr_read_channels(exr, partnum, layer_name)
        -- filter channels and rearrange data by rank index
        local cryptomatte_channels = get_channels_by_index(exr_channel_names)
        -- create image by rank
        crypto_images = exr_read_channel_parts(exr, input_image, cryptomatte_channels, partnum)
    end

    -- close the context manager
    exr:Close()

    -- print last EXRIO related error
    local exrio_error = exr:GetLastError()
    if exrio_error ~= "" then
        print(string.format("ERROR: %s", exrio_error))
    end

    return crypto_images
end

function cryptomatte_utilities:get_mattes_from_string(cInfo, matte_selection_str)
    -- returns the a set of mattes from the matte list input string
    local mattes = {}
    local matte_name_array = convert_str_to_array(matte_selection_str, REGEX_MATTE_LIST)
    -- convert array to set
    for _, matte in ipairs(matte_name_array) do
        mattes[matte] = true
    end
    return mattes
end

-- return module
return cryptomatte_utilities
