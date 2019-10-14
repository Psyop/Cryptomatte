--[[
Requires   : Fusion 9.0.2+
Optional   : cjson
Created by : Cédric Duriau         [duriau.cedric@live.be]
             Kristof Indeherberge  [xmnr0x23@gmail.com]
             Andrew Hazelden       [andrew@andrewhazelden.com]
Version    : 1.2.4
--]]

-- module table
cryptomatte_utilities = {}

-- =============================================================================
-- constants
-- =============================================================================
REGEX_METADATA = "%a+/([a-z0-9]+)/(.+)"
REGEX_MATTE_LIST = "([^,]+),?%s*"
REGEX_LAYER_CHANNEL = "(.+)[.](.+)"
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
    --[[
    Loads first module, if that fails, loads second module.

    :param first: name of preferred module to load first, if loading this module
                  fails, the second one will be loaded
    :type first: string

    :param second: name of second module to load if the first module could not
                   be loaded. If this fails, the default error when loading a
                   non-existing module will be raised
    :type second: string

    :return: table of module that could be loaded
    :rtype: table
    -- ]]
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
    --[[
    Checks if the given string starts with the given substring.

    :param str: string to check if start matches with given start string
    :type str: string

    :param start: part to check if the given string starts with
    :type start: string

    :return: whether the given string starts with the given start string
    :rtype: boolean
    -- ]]
    return string.sub(str, 1, string.len(start)) == start
end

function split_string(str, pattern)
    --[[
    Splits the given string to an array of strings using given pattern.

    :param str: string to split/convert to an array
    :type str: string

    :param pattern: pattern to split string with
    :type pattern: string

    :return: given string split to an array of strings using given pattern
    :rtype: string
    -- ]]
    local matte_names = {}
    for matte in string.gmatch(str, pattern) do
        -- strip the leading and trailing double quotes
        matte = string.sub(matte, 2, matte:len() - 1)
        table.insert(matte_names, matte)
    end
    return matte_names
end

function is_key_in_table(key, t)
    --[[
    Checks whether the given key exists in given table.

    :param key: key to check if it exists given table
    :type key: string

    :param t: table to check for key
    :type: t: table

    :return: whether the given key exists in given table
    :rtype: boolean
    -- ]]
    for k, v in pairs(t) do
        if key == k then
            return true
        end
    end
    return false
end

function build_sidecar_manifest_path(exr_path, sidecar_path)
    --[[
    Builds the absolute sidecar manifest file path.

    :param exr_path: path of the exr frame to get relative sidecar manifest from
    :type exr_path: string

    :param sidecar_path: path of sidecar manifest file relative to exr frame
    :type sidecar_path: string

    :return: absolute sidecar manifest file path
    :rtype: string
    -- ]]
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
    -- ]]
    local pixel = Pixel()
    image:GetPixel(x, y, pixel)
    return pixel
end

function create_matte_image_init()
    --[[
    Initializer function for scanline function "create_matte_image_scanline".

    This function initializes pixel objects and pointers to re-use in scanline
    function. This avoids the creation of these objects at every X or Y pass,
    improving the overall performance.

    ! FOLLOWING PARAMTERS ARE PASSED INDIRECTLY, SEE `DoMultiProcess` USAGE !

    :param dod: domain of definition passed to restrict the scanline process
                to this rectangle
    :type dod: FuRectInt

    :param layer_image: cryptomatte image of a layer, containing the source image
                       "{LAYER}.{RGBA}" channel information in respective RBGA
                       channels.
                       Example: - CryptoAsset00.R -> layer_image.R
                                - CryptoAsset00.G -> layer_image.G
                                - CryptoAsset00.B -> layer_image.B
                                - CryptoAsset00.A -> layer_image.A
    :type layer_image: Image

    :param layer_intermediate_image: intermediate image containing all filtered
                                    G and A channel information needed to build
                                    a matte for the layer
    :type layer_intermediate_image: string

    :param id_float_values: table of id float values built as a set, containing
                            all float id values of name hashes used to filter
                            G and A channel information to build a layer matte
                            Example: manifest = {"bunny": 13851a76}
                                     (hash) 13851a76 = (float) 3.3600012625093e-27
                                     If R or B match this float value, G or A
                                     will be stored respectively.
    :type id_float_values: table
    -- ]]
    global_p = Pixel()
    local_p = Pixel()
    pixptr_in = PixPtr(layer_image, global_p)
    pixptr_out = PixPtr(layer_intermediate_image, local_p)
end

function create_matte_image_scanline(n)
    --[[
    Scanline function that creates a matte.

    :param n: absolute Y coordinate to execute scanline (left to right) pass
    :type n: int

    ! FOLLOWING PARAMTERS ARE PASSED INDIRECTLY, SEE `DoMultiProcess` USAGE !

    :param dod: domain of definition passed to restrict the scanline process
                to this rectangle
    :type dod: FuRectInt

    :param layer_image: cryptomatte image of a layer, containing the source image
                        "{LAYER}.{RGBA}" channel information in respective RBGA channels.
                        Example: - CryptoAsset00.R -> layer_image.R
                                 - CryptoAsset00.G -> layer_image.G
                                 - CryptoAsset00.B -> layer_image.B
                                 - CryptoAsset00.A -> layer_image.A
    :type layer_image: Image

    :param layer_intermediate_image: intermediate image containing all filtered
                                    G and A channel information needed to build
                                    a matte for the layer
    :type layer_intermediate_image: string

    :param id_float_values: table of id float values built as a set, containing
                            all float id values of name hashes used to filter
                            G and A channel information to build a layer matte
                            Example: manifest = {"bunny": 13851a76}
                                     (hash) 13851a76 = (float) 3.3600012625093e-27
                                     If R or B match this float value, G or A
                                     will be stored respectively.
    :type id_float_values: table
    -- ]]

    -- calculate real scanline y position relative to dod
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
            -- rank match in R, counterpart is G
            if r_in_array then
                local_p.G = global_p.G
            end
            -- rank match in B, counterpart is A
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
    --[[
    Initializer function for the scanline function "create_preview_image".

    This function initializes pixel objects and pointers to re-use in scanline
    function. This avoids the creation of these objects at every X or Y pass,
    improving the overall performance.

    ! FOLLOWING PARAMTERS ARE PASSED INDIRECTLY, SEE `DoMultiProcess` USAGE !

    :param preview_image: preview image to write pixel information to
    :type preview_image: Image

    :param layer_0_image: image for the layer 0
    :type layer_0_image: Image

    :param layer_1_image: image for the layer 1
    :type layer_1_image: Image
    -- ]]
    global_p_c00 = Pixel()
    global_p_c01 = Pixel()
    local_p = Pixel()

    pixptr_00 = PixPtr(layer_0_image, global_p_c00)
    pixptr_01 = PixPtr(layer_1_image, global_p_c01)
    pixptr_out = PixPtr(preview_image, local_p)
end

function create_preview_image_scanline(n)
    --[[
    Scanline function that creates the keyable surface preview image.

    This function builds the keyable surface preview image. The algorithm used
    to calculate the pixel information was provided by Jonah Friedman in a Nuke
    sample which I translated to Lua.

    :param n: absolute Y coordinate to execute scanline (left to right) pass
    :type n: int

    ! FOLLOWING PARAMTERS ARE PASSED INDIRECTLY, SEE `DoMultiProcess` USAGE !

    :param preview_image: preview image to write pixel information to
    :type preview_image: Image

    :param layer_0_image: image for the layer 0
    :type layer_0_image: Image

    :param layer_1_image: image for the layer 1
    :type layer_1_image: Image
    -- ]]
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

        -- get mantissa of R and B channels of both layer 0 and 1
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

function create_matte_image(layer_images, id_float_values, output_image)
    --[[
    Creates an image containing all mattes built from given id float values.

    :param layer_images: cryptomatte layer images by layer index as string
                        Example: layer_images["1"] = (Image)CrytpoAsset01(RGBA)
    :type layer_images: table[string, Image]

    :param id_float_values: table of id float values built as a set, containing
                            all float id values of name hashes used to filter
                            G and A channel information to build a layer matte
                            Example: manifest = {"bunny": 13851a76}
                                     (hash) 13851a76 = (float) 3.3600012625093e-27
                                     id_float_values = {3.3600012625093e-27 = true}
    :type id_float_values: table[float, boolean]

    :param output_image: image used to build output combined matte image to
                         match resolution and dod
    :type output_image: Image

    :return: mono channel image containing all mattes built from id float values
    :rtype: Image
    -- ]]
    -- create monochannel combined matte image from all layer matte images and
    -- keep the input resolution and DoD
    local combined_matte_image = Image({IMG_Like = output_image,
                                        IMG_CopyChannels = false,
                                        {IMG_Channel = "Alpha"}})
    combined_matte_image:Clear()
    local dod = output_image.DataWindow

    for _, layer_image in pairs(layer_images) do
        -- create an intermediate image from the layer image holding the data
        -- to build a layer matte
        local layer_intermediate_image = Image({IMG_Like = layer_image})
        layer_intermediate_image:Clear()

        -- process pixels to retrieve the pixels matching the id float value
        local args = {dod = dod,
                      layer_image = layer_image,
                      layer_intermediate_image = layer_intermediate_image,
                      id_float_values = id_float_values}
        self:DoMultiProcess(create_matte_image_init,
                            args,
                            dod.top - dod.bottom,
                            create_matte_image_scanline)

        -- create mono channel matte image for current layer
        local layer_matte_image = Image({IMG_Like = layer_image,
                                        IMG_CopyChannels = false,
                                        {IMG_Channel = "Alpha"}})
        layer_matte_image = layer_matte_image:ChannelOpOf("Add", layer_intermediate_image, {A = "fg.G"})
        layer_matte_image = layer_matte_image:ChannelOpOf("Add", layer_intermediate_image, {A = "fg.A"})

        -- add layer matte image to combined matte image
        combined_matte_image = combined_matte_image:ChannelOpOf("Add", layer_matte_image, {A = "fg.A"})
    end

    return combined_matte_image
end

function create_preview_image(layer_0_image, layer_1_image, input_image)
    --[[
    Creates the keyable surface preview image.

    :param layer_0_image: image for the cryptomatte layer 0
    :type layer_0_image: Image

    :param layer_1_image: image for the cryptomatte layer 1
    :type layer_1_image: Image

    :param input_image: image used to build output preview image to match
                        resolution and dod
    :type input_image: Image

    :return: keyable surface preview image
    :rtype: Image
    -- ]]
    local preview_image = input_image:CopyOf()
    preview_image:Clear()
    local args = {preview_image = preview_image,
                  layer_0_image = layer_0_image,
                  layer_1_image = layer_1_image}
    self:DoMultiProcess(create_preview_image_init,
                        args,
                        preview_image.DataWindow.top - preview_image.DataWindow.bottom,
                        create_preview_image_scanline)
    return preview_image
end

function exr_get_channels(exr, partnum, type_name)
    --[[
    Gets the channels matching given type name.

    :param exr: EXRIO module
    :type exr: table

    :param partnum: part of the exr to read data from
    :type partnum: int

    :param type_name: name of the layer to get channels from (channel prefix)
                         Example: type_name = "CryptoAsset"
                                              "CryptoAsset00.R",  -- rank 0
                                              "CryptoAsset00.G",
                                              "CryptoAsset00.B",  -- rank 1
                                              "CryptoAsset00.A"
                                              "CryptoAsset01.R",  -- rank 2
                                              "CryptoAsset01.G",
                                              "CryptoAsset01.B",  -- rank 3
                                              "CryptoAsset01.A"
                                              "CryptoAsset02.R",  -- rank 4
                                              "CryptoAsset02.G",
                                              "CryptoAsset02.B",  -- rank 5
                                              "CryptoAsset02.A"}
    :type type_name: string

    :return: channels for the given crytomatte layer
    :rtype: table[string]
    --]]
    local channel_names = {}
    -- get all channels
    local channels = exr:GetChannels(partnum)
    for i, channel in ipairs(channels) do
        local channel_name = channel["Name"]
        -- store channels matching type name prefix
        if string.find(channel_name, type_name) then
            table.insert(channel_names, channel_name)
        end
    end
    return channel_names
end

function sort_channels_by_layer_index(channels)
    --[[
    Sorts the array of channels in a table by layer index.

    Example: channels = {"CryptoAsset00.R",
                         "CryptoAsset00.G",
                         "CryptoAsset00.B",
                         "CryptoAsset00.A"
                         "CryptoAsset01.R",
                         "CryptoAsset01.G",
                         "CryptoAsset01.B",
                         "CryptoAsset01.A"
                         "CryptoAsset02.R",
                         "CryptoAsset02.G",
                         "CryptoAsset02.B",
                         "CryptoAsset02.A"}
             by_index = {"0" = {"r" = "CryptoAsset00.R"
                                "g" = "CryptoAsset00.G"
                                "b" = "CryptoAsset00.B"
                                "a" = "CryptoAsset00.A"},
                         "1" = {"r" = "CryptoAsset01.R"
                                "g" = "CryptoAsset01.G"
                                "b" = "CryptoAsset01.B"
                                "a" = "CryptoAsset01.A"},
                         "2" = {"r" = "CryptoAsset02.R"
                                "g" = "CryptoAsset02.G"
                                "b" = "CryptoAsset02.B"
                                "a" = "CryptoAsset02.A"}}

    :return: table with layer index string as key and RGBA channel name maping
             table as value
    :rtype: table[string, table[string, string]]
    --]]
    local layers_by_index = {}
    for i, channel in ipairs(channels) do
        -- get layer and channel name from channel
        local layer, name = string.match(channel, REGEX_LAYER_CHANNEL)

        if layer ~= nil and name ~= nil then
            -- get layer index
            local index = string.match(layer, "[0-9]+$")

            if index ~= nil then
                -- first tonumber to avoid leading numbers, then tostring again
                -- to ensure string keys
                index = tostring(tonumber(index))
                if not is_key_in_table(index, layers_by_index) then
                    layers_by_index[index] = {}
                end

                -- store the layer channels under respective lowercase short form
                local _channel = string.lower(name)
                if _channel == "r" or _channel == "red" then
                    layers_by_index[index]["r"] = channel
                elseif _channel == "g" or _channel == "green" then
                    layers_by_index[index]["g"] = channel
                elseif _channel == "b" or _channel == "blue" then
                    layers_by_index[index]["b"] = channel
                elseif _channel == "a" or _channel == "alpha" then
                    layers_by_index[index]["a"] = channel
                end
            end
        end
    end
    return layers_by_index
end

function exr_get_layer_images_by_index(exr, channels_by_index, partnum, input_image)
    --[[
    Gets the layer images by layer index.

    :param exr: EXRIO module
    :type exr: table

    :param channels_by_index: layer channels by layer index
    :type channels_by_index: table[string]

    :param partnum: part of the exr to read data from
    :type partnum: int

    :param input_image: input image to get resolution information from
    :type input_image: Image

    :return: layer image by layer index as string
    :rtype: table[string, Image]
    --]]
    local layer_images_by_index = {}
    local dispw = exr:DisplayWindow(partnum)
    local dataw = exr:DataWindow(partnum)
    local ox, oy = dispw.left, dispw.bottom
    local w, h = dispw.right - dispw.left, dispw.top - dispw.bottom
    local imgw = ImgRectI(dataw)
    imgw:Offset(-ox, -oy)
    local pixel_aspect_ratio = exr:PixelAspectRatio(partnum)

    -- read part with given index
    exr:Part(partnum)

    for index, channels in pairs(channels_by_index) do
        local image = Image({IMG_Width = w,
                             IMG_Height = h,
                             IMG_Depth = IMDP_128bitFloat,
                             IMG_DataWindow = imgw,
                             IMG_YScale = 1.0 / pixel_aspect_ratio})

        -- read layer RGBA channels
        exr:Channel(channels["r"], ANY_TYPE, 1, CHAN_RED)
        exr:Channel(channels["g"], ANY_TYPE, 1, CHAN_GREEN)
        exr:Channel(channels["b"], ANY_TYPE, 1, CHAN_BLUE)
        exr:Channel(channels["a"], ANY_TYPE, 1, CHAN_ALPHA)

        -- store the image as value to the layer index in string format as key
        exr:ReadPart(partnum, {image})

        -- if proxy mode is enabled, resize the EXR image to the affacted input
        -- image size, EXRIO does not take proxy into consideration
        local result = image
        if input_image.ProxyScale ~= 1 then
            local resized_image = Image({IMG_Like = image,
                                         IMG_Width = input_image.Width,
                                         IMG_Height = input_image.Height})
            image:Resize(resized_image, {RSZ_Filter = "Nearest",
                                         RSZ_Width = input_image.Width,
                                         RSZ_Height = input_image.Height})
            result = resized_image
        end
        layer_images_by_index[tostring(index)] = result
    end

    return layer_images_by_index
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
    --]]
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
    --]]
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
    --[[
    Constructor of the CryptomatteInfo class.

    :param metadata: metadata to get cryptomatte specific metadata from
    :type metadata: table

    :param layer_name: cryptomatte exr layer to get information for
    :type layer_name: string

    :return: CryptomatteInfo object
    :rtype: table
    --]]
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

function CryptomatteInfo:initialize(metadata, layer_name)
    --[[
    Initializes the object.

    :param metadata: metadata to get cryptomatte specific metadata from
    :type metadata: table

    :param layer_name: cryptomatte exr layer to get information for
    :type layer_name: string
    --]]
    self:get_cryptomatte_metadata(metadata, layer_name)
    local manifest_string = self:get_manifest_string()
    local manifest = self:load_manifest(manifest_string)
    self:parse_manifest(manifest)
end

-- functions
function CryptomatteInfo:get_cryptomatte_metadata(metadata, layer_name)
    --[[
    Gets the cryptomatte metadata from the given exr metadata for given layer.

    :param metadata: metadata of the input cryptomatte image
    :type metadata: table

    :param layer_name: name of the layer to get metadata of
    :type layer_name: string
    --]]
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
    --[[
    Gets the manifest as string from the metadata.

    :rtype: string
    --]]
    -- first check if the metadata contains a sidecar manifest key, if so, parse
    -- the file
    local sidecar_path = self.cryptomattes[self.selection][METADATA_KEY_MANIF_FILE]
    if sidecar_path ~= nil then
        -- get the absolute path of the sidecar manifest file
        local path = build_sidecar_manifest_path(self.exr_path, sidecar_path)

        -- read the manifest file
        local fp = io.open(path, "r")
        if fp == nil then
            error(string.format("ERROR: following sidecar file path does not exist: %s", path))
        else
            -- read all lines from file into a string
            manifest_str = fp:read("*all")
            -- close the file
            fp:close()
        end
    else
        -- get the string from the metadata
        manifest_str = self.cryptomattes[self.selection][METADATA_KEY_MANIFEST]
    end
    return manifest_str
end

function CryptomatteInfo:load_manifest(manifest_string)
    --[[
    Loads the given manifest json string as a table.

    :param manifest_string: manifest as json string
    :type manifest_string: string

    :raises error: if the manifest string is nil or empty
    :raises error: if the manifest string is not a string
    :raises error: if the loaded manifest is not a json table

    :return: manifest json table
    :rtype: table
    --]]
    -- raise error if the manifest string is nil or empty
    assert(manifest_string ~= nil or manifest_string == "", "manifest string is empty or nil")

    -- raise error if the manifest string is not a string
    assert(type(manifest_string) == "string", "manifest is metadata is not a json string")

    -- load the string using the json module (can be cjson or dkjson module)
    local manifest = json.decode(manifest_str)

    -- raise error if the loaded manifest is not a json table
    assert(type(manifest) == "table", string.format("invalid manifest string: %s", manifest_string))
    return manifest
end

function CryptomatteInfo:parse_manifest(manifest)
    --[[
    Parse the manifest to store matte id and name information for fast lookup.

    :param manifest: manifest to parse
    :type manifest: table
    --]]
    local from_names = {}
    local from_ids = {}
    local all_names = {}
    local all_ids = {}

    for name, hex in pairs(manifest) do
        -- decode hash to int
        int_flt.i = tonumber(hex, 16)
        -- decode int to float
        local id_float = int_flt.f
        local name_str = tostring(name)
        -- store name by id float
        from_names[name_str] = id_float
        -- store id float by name
        from_ids[id_float] = name_str
        -- store name in set
        all_names[name_str] = true
        -- store id float in set
        all_ids[id_float] = true
    end

    -- create name to id from hexadecimal value of names
    self.cryptomattes[self.selection]["name_to_id"] = from_names
    self.cryptomattes[self.selection]["id_to_name"] = from_ids
    self.cryptomattes[self.selection]["names"] = all_names
    self.cryptomattes[self.selection]["ids"] = all_ids
end

-- =============================================================================
-- cryptomatte_utilities module
-- =============================================================================
function cryptomatte_utilities:create_cryptomatte_info(metadata, layer_name)
    --[[
    Creates a CryptomatteInfo object.

    :param metadata: metadata to get cryptomatte specific metadata from
    :type metadata: table

    :param layer_name: cryptomatte exr layer to get information for
    :type layer_name: string

    :return: CryptomatteInfo object
    :rtype: table
    --]]
    -- create cryptomatte info and populate cryptomattes data from given metadata
    cinfo = CryptomatteInfo()
    cinfo:initialize(metadata, layer_name)
    return cinfo
end

function cryptomatte_utilities:get_id_float_value(cInfo, screen_pos, layer_images, input_image)
    --[[
    Gets the id float value for given relative screen position.

    :param cInfo: CryptomatteInfo object
    :type cInfo: table

    :param screen_pos: relative screen position to get id float value from
    :type screen_pos: Point

    :param layer_images: layer images by index to find id float value in
    :type layer_images: table[string, Image]

    :param input_image: image the screen position is relative to
    :type input_image: Image

    :return: id float value for given relative screen position
    :rtype: float || nil
    --]]
    -- get absolute pixel position from relative screen position
    local abs_x, abs_y = get_absolute_position(input_image, screen_pos.X, screen_pos.Y)

    -- validate if absolute pixel position is in dod or not
    local is_position_valid = is_position_in_rect(input_image.DataWindow, abs_x, abs_y)
    if not is_position_valid then
        return nil
    end
    local id_float_value = nil

    -- sort layer indices to loop over layer images with layer index ascending
    local keys = {}
    for k, _ in pairs(layer_images) do
        table.insert(keys, tonumber(k))
    end
    table.sort(keys)

    -- check for every layer image, index ascending, if the pixel at absolute
    -- position has RGBA channel information which is present in the set of id
    -- float values inside the manifest
    local known_id_float_values = cInfo.cryptomattes[cInfo.selection]["ids"]
    for _, index in ipairs(keys) do
        -- get layer image
        local layer_image = layer_images[tostring(index)]

        -- get pixel from layer image at absolute position
        local pixel = get_screen_pixel(layer_image, abs_x, abs_y)

        -- check if one of the RGBA pixel values are present inside the total
        -- list of ids found in the manifest
        for _, val in ipairs({pixel.R, pixel.G, pixel.B, pixel.A}) do
            if val ~= 0.0 and known_id_float_values[val] then
                id_float_value = val
                break
            end
        end
        -- stop searching at first match
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

function cryptomatte_utilities:create_matte_image(cInfo, matte_names, layer_images, output_image)
    --[[
    Creates an image containing all mattes of given matte names.

    :param cInfo: CryptomatteInfo object
    :type cInfo: table

    :param matte_names: matte name set to build combined matte image from
    :type matte_names: table[string, boolean]

    :param layer_images: cryptomatte layer images by layer index as string
                         Example: layer_images["1"] = (Image)CrytpoAsset01(RGBA)
    :type layer_images: table[string, Image]

    :param output_image: image used to build output combined matte image to
                         match resolution and dod
    :type output_image: Image

    :return: image containing all mattes of given matte names
    :rtype: Image
    --]]
    -- build set of ids from given set of matte names
    local ids = {}
    local name_to_id = cInfo.cryptomattes[cInfo.selection]["name_to_id"]

    for name, _ in pairs(matte_names) do
        local id = name_to_id[name]
        if id then
            ids[id] = true
        end
    end

    -- create the combined matte image
    if ids then
        return create_matte_image(layer_images, ids, output_image)
    end
    return nil
end

function cryptomatte_utilities:create_preview_image(layer_0_image, layer_1_image, input_image)
    --[[
    Creates the keyable surface preview image.

    There are two functions called "create_preview_image", this one which is
    inside the cryptomatte_utilities module and one standalone. The reason for
    this is that "self" in standalone context is the Fuse, and "self" in a
    module context is the module. Inside the standalone function we build the
    preview image using the Fuse scanline multi threaded function
    "DoMultiProcess". This function cannot be called from the current function
    due to the "self" being the module, does not have this function.

    Long story short, I wanted this function to be public, so I had to make two
    of them to avoid any clashes.

    :param layer_0_image: image for the cryptomatte layer 0
    :type layer_0_image: Image

    :param layer_1_image: image for the cryptomatte layer 1
    :type layer_1_image: Image

    :param input_image: image used to build output preview image to match
                        resolution and dod
    :type input_image: Image

    :return: keyable surface preview image
    :rtype: Image
    --]]
    return create_preview_image(layer_0_image, layer_1_image, input_image)
end

function cryptomatte_utilities:get_exr_layer_images(cInfo, type_name, input_image)
    --[[
    Gets the numbered exr layer images by index matching given type name.

    :param cInfo: CryptomatteInfo object
    :type cInfo: table

    :param type_name: prefix of the exr layer to get layer images for
    :type type_name: string

    :param input_image: input image to get resolution information from
    :type input_image: Image

    :raises error: if any error occured within the EXRIO module

    :return: numbered exr layer images by index matching given type name
    :rtype: table[string, Image]
    --]]
    local partnum = 1
    local layer_images = {}

    -- create EXRIO pointer
    local exr = EXRIO()

    -- read the input exr
    exr:ReadOpen(cInfo.exr_path, -1)

    if exr:ReadHeader() then
        -- get the channel names
        local channels = exr_get_channels(exr, partnum, type_name)
        -- sort channels by layer index
        local channels_by_layer_index = sort_channels_by_layer_index(channels)
        -- create image by layer index
        layer_images = exr_get_layer_images_by_index(exr, channels_by_layer_index, partnum, input_image)
    end

    -- close the context manager
    exr:Close()

    -- raise last EXRIO related error
    local exrio_error = exr:GetLastError()
    if exrio_error ~= "" then
        error(string.format("ERROR: could not read EXR data (EXRIO ERROR: %s)", exrio_error))
    end

    return layer_images
end

function cryptomatte_utilities:get_matte_names_from_selection(cInfo, matte_selection)
    --[[
    Gets the matte names from the given selection string.

    :param cInfo: CryptomatteInfo object
    :type cInfo: table

    :param matte_selection: selection string containing matte names to split
    :type matte_selection: string

    :return: matte names from the given selection string
    :rtype: table[string, boolean]
    --]]
    -- returns the a set of mattes from the matte list input string
    local mattes = {}
    local matte_name_array = split_string(matte_selection, REGEX_MATTE_LIST)
    -- convert array to set
    for _, matte in ipairs(matte_name_array) do
        mattes[matte] = true
    end
    return mattes
end

-- return module
return cryptomatte_utilities
