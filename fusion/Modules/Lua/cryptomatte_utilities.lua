--[[
Requires   : Fusion 9.0.2+
Optional   : cjson
Created by : Cédric Duriau         [duriau.cedric@live.be]
             Kristof Indeherberge  [xmnr0x23@gmail.com]
             Andrew Hazelden       [andrew@andrewhazelden.com]
Version    : 1.2.1
--]]

-- module table
cryptomatte_utilities = {}

-- =============================================================================
-- constants
-- =============================================================================
REGEX_METADATA = "%a+/([a-z0-9]+)/(.+)"
REGEX_MATTE_LIST = "([^,]+),?%s*"
REGEX_RANK_CHANNEL = "(.+)[.](.+)"
METADATA_PREFIX = "cryptomatte/"
METADATA_KEY_NAME = "name"
METADATA_KEY_MANIFEST = "manifest"
METADATA_KEY_FILENAME = "Filename"
METADATA_KEY_MANIF_FILE = "manif_file"

-- =============================================================================
-- ffi C utils
-- =============================================================================
-- int / float representation of hash
ffi.cdef [[ union int_flt { uint32_t i; float f; }; ]]
local int_flt = ffi.new("union int_flt")

-- =============================================================================
-- third party modules
-- =============================================================================
function prefered_load(first, second)
    -- Loads first module, if that fails, loads second module.
    local status, module = pcall(require, first)
    if not status then
        module = require(second)
    end
    return module
end

-- load cjson module if present, if not, load Fusion stdlib dkjson module
local json = prefered_load("cjson", "dkjson")

-- =============================================================================
-- utils
-- =============================================================================
function string_starts_with(str, start)
    -- Checks if the given string starts with the given substring.
    return string.sub(str, 1, string.len(start)) == start
end

function convert_str_to_array(str, pattern)
    -- Converts the given string to an array based on given pattern.
    local matte_names = {}
    for matte in string.gmatch(str, pattern) do
        -- strip the leading and trailing double quote
        matte = string.sub(matte, 2, matte:len() - 1)
        table.insert(matte_names, matte)
    end
    return matte_names
end

function is_key_in_table(key, table)
    -- Checks if the given key is present in given table.
    for k, v in pairs(table) do
        if key == k then
            return true
        end
    end
    return false
end

function build_manifest_path(exr_path, sidecar_path)
    -- Builds the path of the manifest based on given EXR file path.
    local exr_dir = exr_path:match("(.*/)")
    return exr_dir .. sidecar_path
end

function get_screen_pixel(image, x, y)
    --[[
    Get the pixel object from given image at given coordinates.

    :param x: absolute x position in pixel unit
    :type x: int

    :param y: absolute y position in pixel unit
    :type y: int

    :return: pixel object from given image at given coordinates
    :rtype: Pixel
    ]]
    local pixel = Pixel()
    image:GetPixel(x, y, pixel)
    return pixel
end

function create_matte_image_init()
    -- Initializer function for scanline function "create_matte_image_scanline".
    -- Create placeholder pixel objects to avoid creating them for each scanline pass.
    global_p = Pixel()
    local_p = Pixel()
    pixptr_in = PixPtr(rank_image, global_p)
    pixptr_out = PixPtr(rank_intermediate_image, local_p)
end

function create_matte_image_scanline(n)
    -- Scanline function that creates a matte.

    -- calculate real scanline y position
    local y = n + dod.bottom

    -- set start X position for scanline pass
    pixptr_in:GotoXY(dod.left, y)
    pixptr_out:GotoXY(dod.left, y)

    for x = dod.left, dod.right - 1 do
        -- go to correct X position
        pixptr_in:GetNextPixel(global_p)

        -- reset placeholder pixel RGBA values
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

function create_preview_image_init()
    -- Initializer function for the scanline function "create_preview_image".
    -- Create placeholder pixel objects to avoid creating them for each scanline pass.
    global_p_c00 = Pixel()
    global_p_c01 = Pixel()
    local_p = Pixel()

    pixptr_00 = PixPtr(rank_0_image, global_p_c00)
    pixptr_01 = PixPtr(rank_1_image, global_p_c01)
    pixptr_out = PixPtr(preview_image, local_p)
end

function create_preview_image_scanline(n)
    -- Scanline function that creates the keyable surface preview image.
    
    -- calculate real scanline y position
    local y = n + preview_image.DataWindow.bottom

    -- set start X position for scanline pass
    pixptr_00:GotoXY(preview_image.DataWindow.left, y)
    pixptr_01:GotoXY(preview_image.DataWindow.left, y)
    pixptr_out:GotoXY(preview_image.DataWindow.left, y)

    for x = preview_image.DataWindow.left, preview_image.DataWindow.right - 1 do
        -- go to correct X position
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

function create_matte_image(rank_images, id_float_values, output_image)
    -- Creates a combined matte image holding all mattes of given id float values.

    -- create monochannel combined matte image from all rank matte images and
    -- keep the input resolution and DoD
    local combined_matte_image = Image({IMG_Like = output_image,
                                        IMG_CopyChannels = false,
                                        {IMG_Channel = "Alpha"}})
    combined_matte_image:Clear()
    local dod = output_image.DataWindow

    for _, rank_image in pairs(rank_images) do
        -- create an intermediate image from the rank image holding the data 
        -- to build a rank matte
        local rank_intermediate_image = Image({IMG_Like = rank_image})
        rank_intermediate_image:Clear()

        -- process pixels to retrieve the pixels matching the id float value
        local args = {dod = dod,
                      rank_image = rank_image,
                      rank_intermediate_image = rank_intermediate_image, 
                      id_float_values = id_float_values}
        self:DoMultiProcess(create_matte_image_init,
                            args,
                            dod.top - dod.bottom,
                            create_matte_image_scanline)

        -- create mono channel matte image for current rank
        local rank_matte_image = Image({IMG_Like = rank_image, 
                                        IMG_CopyChannels = false, 
                                        {IMG_Channel = "Alpha"}})
        rank_matte_image = rank_matte_image:ChannelOpOf("Add", rank_intermediate_image, {A = "fg.G"})
        rank_matte_image = rank_matte_image:ChannelOpOf("Add", rank_intermediate_image, {A = "fg.A"})

        -- add rank matte image to combined matte image
        combined_matte_image = combined_matte_image:ChannelOpOf("Add", rank_matte_image, {A = "fg.A"})
    end

    return combined_matte_image
end

function create_preview_image(rank_0_image, rank_1_image, input_image)
    -- Creates the keyable surface preview image from first two rank images.
    local preview_image = input_image:CopyOf()
    preview_image:Clear()
    local args = {preview_image = preview_image,
                  rank_0_image = rank_0_image,
                  rank_1_image = rank_1_image}
    self:DoMultiProcess(create_preview_image_init,
                        args, 
                        preview_image.DataWindow.top - preview_image.DataWindow.bottom,
                        create_preview_image_scanline)
    return preview_image
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
    -- gets all the cryptomatte required channels by rank index and short 
    -- channel name (r, g, b, a)
    local by_index = {}
    for i, channel in ipairs(exr_channels) do
        -- get rank and channel name from channel
        local rank, name = string.match(channel, REGEX_RANK_CHANNEL)

        if rank ~= nil and name ~= nil then
            -- get index from rank
            local index = string.match(rank, "[0-9]+$")

            if index ~= nil then
                -- first tonumber to avoid leading numbers, then tostring again 
                -- to ensure string keys
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

function exr_read_channel_part(exr, cryptomatte_channels, partnum)
    -- creates an image from the given cryptomatte channels by rank
    local cryptomatte_images = {}

    local dispw = exr:DisplayWindow(partnum)
    local dataw = exr:DataWindow(partnum)
    local ox, oy = dispw.left, dispw.bottom
    local w, h = dispw.right - dispw.left, dispw.top - dispw.bottom

    local imgw = ImgRectI(dataw)
    imgw:Offset(-ox, -oy)

    local pixel_aspect_ratio = exr:PixelAspectRatio(partnum)

    -- read part with given index
    exr:Part(partnum)

    for index, channels in pairs(cryptomatte_channels) do
        local image = Image({IMG_Width = w,
                             IMG_Height = h,
                             IMG_Depth = IMDP_128bitFloat,
                             IMG_DataWindow = imgw,
                             IMG_YScale = 1.0 / pixel_aspect_ratio})

        -- read rank RGBA channels
        exr:Channel(channels["r"], ANY_TYPE, image, CHAN_RED)
        exr:Channel(channels["g"], ANY_TYPE, image, CHAN_GREEN)
        exr:Channel(channels["b"], ANY_TYPE, image, CHAN_BLUE)
        exr:Channel(channels["a"], ANY_TYPE, image, CHAN_ALPHA)

        -- store the image as value to the rank index in string format as key
        exr:ReadPart(partnum, {image})
        cryptomatte_images[tostring(index)] = image
    end

    return cryptomatte_images
end

function is_position_in_rect(rect, x, y)
    --[[
    Validates if the given x and y coordinates are in the given rect bounds.
    
    :param rect: integer rectangle position to validate x and y position  with
    :type rect: FuRectInt
    
    :param x: x position to validate
    :type x: int
    
    :param y: y position to validate
    :type y: int
    
    :return: true if the given position is inside the given rect, false if not
    :rtype: bool
    ]]
    if x < rect.left or x > rect.right then
        return false
    end
    if y > rect.top or y < rect.bottom then
        return false
    end
    return true
end

function get_absolute_position(image, relative_x, relative_y)
    --[[
    Gets the absolute values for given relative coordinates in given image.

    :param image: image to use as reference to calcuate absolute values from
    :type image: Image

    :param relative_x: relative x coordinate
    :type relative_x: float

    :param relative_y: relative y coordinate in image to get absolute value for
    :type relative_y: float

    :return: absolute values for given relative coordinates in given image
    :rtype: tuple(int, int)
    ]]
    local abs_x = math.floor(image.Width / (1 / relative_x))
    local abs_y = math.floor(image.Height / (1 / relative_y))
    return abs_x, abs_y
end

-- =============================================================================
-- CryptomatteInfo class
-- =============================================================================
local CryptomatteInfo = {}
CryptomatteInfo.__index = CryptomatteInfo
setmetatable(CryptomatteInfo, {__call = function(cls) return cls:new() end})
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
function CryptomatteInfo:get_cryptomatte_metadata(metadata, layer_name)
    -- Gets the cryptomatte metadata from the given exr metadata for given layer.
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

            -- store cryptomatte data by metadata layer id
            if not is_key_in_table(metadata_id, cryptomattes) then
                cryptomattes[metadata_id] = {}
            end
            cryptomattes[metadata_id][partial_key] = v

            -- store layer name by index and reverse for fast lookups
            if partial_key == METADATA_KEY_NAME then
                index = index + 1
                index_to_layer_name[index] = v
                layer_name_to_index[v] = index
            end

            -- if the given selected layer name was found inside the metadata, 
            -- store the id to set as default selection, else store current 
            -- metadata layer id as fallback selection
            fallback_selection = metadata_id
            if partial_key == METADATA_KEY_NAME and v == layer_name then
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
            print(string.format("ERROR: following path does not exist: %s", path))
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

-- =============================================================================
-- module
-- =============================================================================
function cryptomatte_utilities:create_cryptomatte_info(metadata, layer_name)
    -- create cryptomatte info and populate cryptomattes data from given metadata
    cInfo = CryptomatteInfo()
    cInfo:get_cryptomatte_metadata(metadata, layer_name)
    cInfo:parse_manifest()
    return cInfo
end

function cryptomatte_utilities:get_id_float_value(cInfo, screen_pos, rank_images, input_image)
    -- get the pixel at the given location for all the given rank images
    -- if an R, G, B or A channel value is different than zero, the id float value was found

    -- get absolute pixel position from relative screen position
    local abs_x, abs_y = get_absolute_position(input_image, screen_pos.X, screen_pos.Y)

    -- validate if absolute pixel position is in dod or not
    local is_position_valid = is_position_in_rect(input_image.DataWindow, abs_x, abs_y)
    if not is_position_valid then
        return nil
    end
    local id_float_value = nil

    -- sort keys
    local keys = {}
    for k in pairs(rank_images) do
        table.insert(keys, tonumber(k))
    end
    table.sort(keys)

    for _, index in ipairs(keys) do
        local rank_image = rank_images[tostring(index)]
        local pixel = get_screen_pixel(rank_image, abs_x, abs_y)

        -- matte value
        for _, val in ipairs({pixel.R, pixel.G, pixel.B, pixel.A}) do
            if val ~= 0.0 and cInfo.cryptomattes[cInfo.selection]["ids"][val] then
                id_float_value = val
                break
            end
        end
        if id_float_value ~= nil then
            break
        end
    end

    if id_float_value == nil then
        -- check if the background is being parsed (RGB=0,0,0)
        local pixel = get_screen_pixel(input_image, abs_x, abs_y)
        if pixel.R == 0.0 and pixel.G == 0.0 and pixel.B == 0.0 then
            id_float_value = 0.0
        end
    end

    return id_float_value
end

function cryptomatte_utilities:create_matte_image(cInfo, matte_names, rank_images, output_image)
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
        combined_matte = create_matte_image(rank_images, ids, output_image)
    end
    return combined_matte
end

function cryptomatte_utilities:create_preview_image(rank_0_image, rank_1_image, input_image)
    -- Creates the keyable surface preview image.
    
    -- There are two functions called "create_preview_image", this one which
    -- is inside the cryptomatte_utilities module and one standalone. The reason
    -- for this is that "self" in standalone context is the Fuse, and "self" in 
    -- a module context is the module. Inside the standalone function we build 
    -- the preview image using the Fuse scanline multi threaded function 
    -- "DoMultiProcess". This function cannot be called from the current 
    -- function due to the "self" being the module, does not have this function.
    -- Long story short, I wanted this function to be public, so I had to make 
    -- two of them to avoid any clashes.
    return create_preview_image(rank_0_image, rank_1_image, input_image)
end

function cryptomatte_utilities:get_all_rank_images(cInfo, layer_name)
    local partnum = 1
    local rank_images = {}

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
        rank_images = exr_read_channel_part(exr, cryptomatte_channels, partnum)
    end

    -- close the context manager
    exr:Close()

    -- print last EXRIO related error
    local exrio_error = exr:GetLastError()
    if exrio_error ~= "" then
        print(string.format("ERROR: %s", exrio_error))
    end

    return rank_images
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
