--[[
Requires   : Fusion 9.0.2+
Optional   : cjson
Created by : Cédric Duriau         [duriau.cedric@live.be]
             Kristof Indeherberge  [xmnr0x23@gmail.com]
             Andrew Hazelden       [andrew@andrewhazelden.com]
Version    : 1.2.8
--]]

-- ============================================================================
-- third party modules
-- ============================================================================
function prefered_load(first, second)
    --[[
    Loads first module, if that fails, loads second module.

    :param first: Name of preferred module to load first, if loading this module
                  fails, the second one will be loaded.
    :type first: string

    :param second: Name of second module to load if the first module could not
                   be loaded. If this fails, the default error when loading a
                   non-existing module will be raised.
    :type second: string

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

-- ============================================================================
-- constants
-- ============================================================================
ENV_VAR_LOG_LEVEL = "CRYPTOMATTE_LOG_LEVEL"
METADATA_PREFIX = "cryptomatte/"
REGEX_METADATA = "%a+/([a-z0-9]+)/(.+)"
METADATA_KEY_NAME = "name"
METADATA_KEY_FILENAME = "Filename"
REGEX_MATTE_LIST = "([^,]+),?%s*"
REGEX_LAYER_CHANNEL = "(.+)([0-9]+)[.](.+)"
CHANNEL_NAME_MAP = {r="r", red="r",
                    g="g", green="g",
                    b="b", blue="b",
                    a="a", alpha="a"}
BACKGROUND_MATTE_NAME = "Background (value RGBA=0000)"

-- ============================================================================
-- ffi C utils
-- ============================================================================
-- int / float representation of hash
ffi.cdef [[ union int_flt { uint32_t i; float f; }; ]]
local int_flt = ffi.new("union int_flt")

-- ============================================================================
-- fusion centric functions (EXRIO/scanline)
-- ============================================================================
function get_layer_images(input_image, layer_name, channel_hierarchy, exr, partnum)
    --[[
    Returns the images for all indices of layer.

    :param input_image: Source Cryptomatte image.
    :type input_image: Image

    :param layer_name: Name of the layer to get all index images for.
    :type layer_name: string

    :param channel_hierarchy: Channel datastructure by layer and index.
    :type channel_hierarchy: table

    :param exr: EXRIO module instance loaded with the input EXR image.
    :type exr: EXRIO

    :param partnum: EXR multipart index.
    :type partnum: number

    :rtype: table[string, Image]
    ]]
    -- calculate datawindow to keep/scan
    local dispw = exr:DisplayWindow(partnum)
    local ox = dispw.left
    local oy = dispw.bottom
    local w = dispw.right - dispw.left
    local h = dispw.top - dispw.bottom
    local dataw = exr:DataWindow(partnum)
    local imgw = ImgRectI(dataw)
    imgw:Offset(-ox, -oy)

    -- get pixel aspect ratio
    local pixel_aspect_ratio = exr:PixelAspectRatio(partnum)

    -- select EXR part to load
    exr:Part(partnum)

    local images = {}
    for index, channels in pairs(channel_hierarchy[layer_name]) do
        -- create image from scratch
        local image = Image({IMG_Width = w,
                             IMG_Height = h,
                             IMG_Depth = IMDP_128bitFloat,
                             IMG_DataWindow = imgw,
                             IMG_YScale = 1.0 / pixel_aspect_ratio})

        -- write out loaded EXR part image channels to layer image
        exr:Channel(channels["r"], ANY_TYPE, 1, CHAN_RED)
        exr:Channel(channels["g"], ANY_TYPE, 1, CHAN_GREEN)
        exr:Channel(channels["b"], ANY_TYPE, 1, CHAN_BLUE)
        exr:Channel(channels["a"], ANY_TYPE, 1, CHAN_ALPHA)
        exr:ReadPart(partnum, {image})

        -- handle proxy scaling
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
        images[tonumber(index)] = result
    end

    return images
end

function create_preview_image_colors_init()
    --[[
    Scanline initializer function for the "colors" preview image.

    This function initializes pixel objects and pointers to re-use in scanline
    function. This avoids the creation of these objects at every X or Y pass,
    improving the overall performance.

    ! FOLLOWING PARAMTERS ARE PASSED INDIRECTLY, SEE `DoMultiProcess` USAGE !

    :param output_image: Preview image to write pixel information to.
    :type output_image: Image

    :param layer_0_image: Image for the layer 0.
    :type layer_0_image: Image

    :param layer_1_image: Image for the layer 1.
    :type layer_1_image: Image
    -- ]]
    global_p_00 = Pixel()
    global_p_01 = Pixel()
    local_p = Pixel()

    pixptr_00 = PixPtr(layer_0_image, global_p_00)
    pixptr_01 = PixPtr(layer_1_image, global_p_01)
    pixptr_out = PixPtr(output_image, local_p)
end

function create_preview_image_colors_scanline(n)
    --[[
    Scanline function that creates the "colors" preview image.

    This function builds the keyable surface preview image. The algorithm used
    to calculate the pixel information was provided by Jonah Friedman in a Nuke
    sample which I translated to Lua.

    :param n: Absolute Y coordinate to execute scanline (left to right) pass.
    :type n: number

    ! FOLLOWING PARAMTERS ARE PASSED INDIRECTLY, SEE `DoMultiProcess` USAGE !

    :param output_image: Preview image to write pixel information to.
    :type output_image: Image

    :param layer_0_image: Image for the layer 0.
    :type layer_0_image: Image

    :param layer_1_image: Image for the layer 1.
    :type layer_1_image: Image
    -- ]]
    -- calculate real scanline y position
    local y = n + output_image.DataWindow.bottom

    -- set start X position for scanline pass
    pixptr_00:GotoXY(output_image.DataWindow.left, y)
    pixptr_01:GotoXY(output_image.DataWindow.left, y)
    pixptr_out:GotoXY(output_image.DataWindow.left, y)

    for x = output_image.DataWindow.left, output_image.DataWindow.right - 1 do
        -- go to correct X position
        pixptr_00:GetNextPixel(global_p_00)
        pixptr_01:GetNextPixel(global_p_01)

        -- get mantissa of R and B channels of both layer 0 and 1
        m00_rg, _ = math.frexp(math.abs(global_p_00.R))
        m00_ba, _ = math.frexp(math.abs(global_p_00.B))
        m01_rg, _ = math.frexp(math.abs(global_p_01.R))
        m01_ba, _ = math.frexp(math.abs(global_p_01.B))

        -- calculate RGB channel values for final id colored image
        -- red
        r_00_rg = (m00_rg * 1 % 0.25) * global_p_00.G
        r_00_ba = (m00_ba * 1 % 0.25) * global_p_00.A
        r_01_rg = (m01_rg * 1 % 0.25) * global_p_01.G
        r_01_ba = (m01_ba * 1 % 0.25) * global_p_01.A

        -- green
        g_00_rg = (m00_rg * 4 % 0.25) * global_p_00.G
        g_00_ba = (m00_ba * 4 % 0.25) * global_p_00.A
        g_01_rg = (m01_rg * 4 % 0.25) * global_p_01.G
        g_01_ba = (m01_ba * 4 % 0.25) * global_p_01.A

        -- blue
        b_00_rg = (m00_rg * 16 % 0.25) * global_p_00.G
        b_00_ba = (m00_ba * 16 % 0.25) * global_p_00.A
        b_01_rg = (m01_rg * 16 % 0.25) * global_p_01.G
        b_01_ba = (m01_ba * 16 % 0.25) * global_p_01.A

        -- store calculated R,G and B values
        local_p.R = (r_00_rg + r_00_ba + r_01_rg + r_01_ba)
        local_p.G = (g_00_rg + g_00_ba + g_01_rg + g_01_ba)
        local_p.B = (b_00_rg + b_00_ba + b_01_rg + b_01_ba)

        -- set output pixel pointer
        pixptr_out:SetNextPixel(local_p)
    end
end

function create_matte_image_init()
    --[[
    Scanline initializer function that creates the matte image.

    ! FOLLOWING PARAMTERS ARE PASSED INDIRECTLY, SEE `DoMultiProcess` USAGE !

    :param layer_image: Image of an isolated Cryptomatte layer.
    :type layer_image: Image

    :param matte_values: Matte ID float values to match.
    :type matte_values: table[number, boolean]

    :param dod: Datawindow to process pixels for.
    :type dod: FuRect

    :param output_image: Image to store mattes in.
    :type output_image: Image
    ]]
    input_p = Pixel()
    output_p = Pixel()
    pixptr_in = PixPtr(layer_image, input_p)
    pixptr_out = PixPtr(output_image, output_p)
end

function create_matte_image_scanline(n)
    --[[
    Scanline function that creates the matte image.

    :param n: Absolute Y coordinate to execute scanline (left to right) pass.
    :type n: number

    ! FOLLOWING PARAMTERS ARE PASSED INDIRECTLY, SEE `DoMultiProcess` USAGE !

    :param layer_image: Image of an isolated Cryptomatte layer.
    :type layer_image: Image

    :param matte_values: Known matte float ID values from manifest.
    :type matte_values: table[number, boolean]

    :param dod: Datawindow to process pixels for.
    :type dod: FuRect

    Algorithm:
    - matte_pixel.A += pixel.G if pixel.R in matte_float_id_values else 0
    - matte_pixel.A += pixel.A if pixel.B in matte_float_id_values else 0

    :param output_image: Image to store mattes in.
    :type output_image: Image
    ]]
    local y = n + dod.bottom

    -- set start X position for scanline pass
    pixptr_in:GotoXY(dod.left, y)
    pixptr_out:GotoXY(dod.left, y)

    local update = false
    for x = dod.left, dod.right - 1 do
        -- go to correct X position
        pixptr_in:GetNextPixel(input_p)
        pixptr_out:GetPixel(output_p)

        -- reset flag
        update = false

        -- detect rank 1 match (red match = add green)
        if matte_values[input_p.R] then
            output_p.A = output_p.A + input_p.G
            update = true
        end

        -- detect rank 2 match (blue match = add alpha)
        if matte_values[input_p.B] then
            output_p.A = output_p.A + input_p.A
            update = true
        end

        if update then
            pixptr_out:SetNextPixel(output_p)
        else
            pixptr_out:NextPixel()
        end
    end
end

function get_screen_pixel(image, x, y)
    --[[
    Gets the pixel object from given image at given coordinates.

    :param x: Absolute x position in pixel units.
    :type x: number

    :param y: Absolute y position in pixel units.
    :type y: number

    :rtype: Pixel
    -- ]]
    local pixel = Pixel()
    image:GetPixel(x, y, pixel)
    return pixel
end

-- ============================================================================
-- module
-- ============================================================================
module = {}

-- private
function module._log(level, msg)
    --[[
    Logs a message.

    :param level: Name of the log level.
    :type level: string

    :param msg: Message to log.
    :type msg: string
    ]]
    print(string.format("[Cryptomatte][%s] %s", level, msg))
end

function module._get_log_level()
    --[[
    Returns the log level.

    Log levels:
    - 0: no logging
    - 1: error (default)
    - 2: info

    Setting the log level to a high number than specified log levels will
    result in applying all lower log levels.

    :rtype: number 
    ]]
    local log_level = os.getenv(ENV_VAR_LOG_LEVEL)
    if log_level == nil then
        return 1
    end
    return tonumber(log_level)
end

function module._string_starts_with(str, substr)
    --[[
    Returns whether the given string starts with the given substring.

    :param str: Text to match with substring.
    :type str: string

    :param substr: Substring to match text with.
    :type substr: string

    :rtype: boolean
    ]]
    return string.sub(str, 1, string.len(substr)) == substr
end

function module._string_ends_with(str, substr)
    --[[
    Returns whether the given string ends with the given substring.

    :param str: Text to match with substring.
    :type str: string

    :param substr: Substring to match text with.
    :type substr: string

    :rtype: boolean
    ]]
    return string.sub(str, -string.len(substr), -1) == substr
end

function module._string_split(str, pattern)
    --[[
    Splits the given string to an array of strings using given pattern.

    :param str: String to split/convert to an array.
    :type str: string

    :param pattern: Pattern to split string with.
    :type pattern: string

    :rtype: table[string]
    -- ]]
    local parts = {}
    for part in string.gmatch(str, pattern) do
        table.insert(parts, part)
    end
    return parts
end

function module._solve_channel_name(name)
    --[[
    Returns the internal representation of a channel.

    :param name: Channel name to get internal representation of
    :type name: string

    :rtype: string
    ]]
    return CHANNEL_NAME_MAP[string.lower(name)]
end

function module._get_channel_hierarchy(layer_name, channels)
    --[[
    Returns the channels of all indices of a layer.

    :param layer_name: Name of the layer to get channels of.
    :type layer_name: string

    :param channels: All channel objects of an EXR file.
    :type channels: table[number, table]

    :rtype: table
    ]]
    local hierarchy = {}
    for i, channel in ipairs(channels) do
        full_channel_name = channel["Name"]
        if module._string_starts_with(full_channel_name, layer_name) then
            -- get layer name & index info from channel name
            local _layer_name, layer_index, channel_name = string.match(full_channel_name, REGEX_LAYER_CHANNEL)

            -- get internal channel name representation
            local internal_channel_name = nil
            if layer_index and channel_name then
                internal_channel_name = module._solve_channel_name(channel_name)

                -- skip error for matching layer without index (beauty layer)
                if layer_index and not internal_channel_name then
                    module.log_error(string.format("failed to get internal name for channel: %s", full_channel_name))
                end
            end

            if internal_channel_name ~= nil then
                if hierarchy[layer_name] == nil then
                    hierarchy[layer_name] = {}
                end

                if hierarchy[layer_name][layer_index] == nil then
                    hierarchy[layer_name][layer_index] = {}
                end

                if hierarchy[layer_name][layer_index][internal_channel_name] == nil then
                    hierarchy[layer_name][layer_index][internal_channel_name] = full_channel_name
                end
            end
        end
    end
    return hierarchy
end

function module._get_absolute_position(width, height, rel_x, rel_y)
    --[[
    Gets the absolute values for given relative coordinates.

    :param width: Reference width.
    :type width: number

    :param width: Reference height.
    :type width: number

    :param rel_x: Relative x coordinate.
    :type rel_x: number

    :param rel_y: Relative y coordinate.
    :type rel_y: number

    :rtype: number, number
    --]]
    return math.floor(width / (1 / rel_x)), math.floor(height / (1 / rel_y))
end

function module._is_position_in_rect(rect, x, y)
    --[[
    Validates if the given x and y coordinates are in the given rect bounds.
   
    :param rect: Integer rectangle position to validate x and y position with.
    :type rect: FuRectInt
   
    :param x: Y position to validate.
    :type x: number
   
    :param y: Y position to validate.
    :type y: number
   
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

function module._hex_to_float(hex)
    --[[
    Returns the float representation of a hexademical string.

    :param hex: Hexadecimal string.
    :type hex: string

    :rtype: number
    ]]
    int_flt.i = tonumber(hex, 16)
    return int_flt.f
end

-- public
function module.log_error(msg)
    --[[
    Logs an error message.

    :param msg: Message to log.
    ]]
    local log_level = module._get_log_level()
    if log_level > 0 then
        module._log("ERROR", msg)
    end
end

function module.log_info(msg)
    --[[
    Logs an information message.

    :param msg: Message to log.
    ]]
    local log_level = module._get_log_level()
    if log_level > 1 then
        module._log("INFO", msg)
    end
end

function module.get_cryptomatte_metadata(metadata)
    --[[
    Reads the Cryptomatte metadata of an EXR file.

    :param metadata: Source Cryptomatte EXR metadata.
    :type metadata: table

    :rtype: table
    ]]
    local exr_path = nil
    local layer_data_by_id = {}

    local id_to_name = {}
    local name_to_id = {}

    local index = 0
    local id_to_index = {}
    local index_to_id = {}

    for k, v in pairs(metadata) do
        if module._string_starts_with(k, METADATA_PREFIX) then
            -- get layer ID and cryptomatte metadata key
            local layer_id, partial_key = string.match(k, REGEX_METADATA)

            local layer_data = layer_data_by_id[layer_id]
            if layer_data == nil then
                layer_data = {}
                layer_data_by_id[layer_id] = layer_data
            end

            -- store cryptomatte layer metadata
            layer_data[partial_key] = v

            -- store mapping tables for easy lookups
            if partial_key == METADATA_KEY_NAME then
                id_to_name[layer_id] = v
                name_to_id[v] = layer_id

                index = index + 1
                id_to_index[layer_id] = index
                index_to_id[index] = layer_id
            end

        elseif k == METADATA_KEY_FILENAME then
            exr_path = v:gsub("([\\])", "/")
        end
    end

    local crypto_metadata = {}
    crypto_metadata["path"] = exr_path
    crypto_metadata["layer_count"] = index
    crypto_metadata["id_to_name"] = id_to_name
    crypto_metadata["name_to_id"] = name_to_id
    crypto_metadata["index_to_id"] = index_to_id
    crypto_metadata["id_to_index"] = id_to_index
    crypto_metadata["layers"] = layer_data_by_id
    return crypto_metadata
end

function module.read_manifest_file(exr_path, sidecar_file_path)
    --[[
    Reads the manifest of an EXR sidecar file.

    :param exr_path: Absolute path of an EXR file.
    :type exr_path: string

    :param sidecar_file_path: Path of a sidecar file relative to the EXR file.
    :type sidecar_file_path: string

    :rtype: string
    ]]
    -- build absolute sidecar file path
    local path = exr_path:match("(.*/)") .. sidecar_file_path

    local fp = io.open(path, "r")
    if fp == nil then
        module.log_error(string.format("unable to open manifest file: %s", path))
        return ""
    else
        local manifest_str = fp:read("*all")
        fp:close()
        return manifest_str
    end
end

function module.decode_manifest(raw_manifest)
    --[[
    Deserializes a manifest from JSON string to table.

    :param raw_manifest: Serialized manifest.
    :type raw_manifest: string

    :rtype: table[string, string]
    ]]
    if raw_manifest == nil or raw_manifest == "" then
        module.log_error("no manifest to decode")
        return {}
    end
    return json.decode(raw_manifest)
end

function module.get_matte_names(matte_str)
    --[[
    Returns the matte names from an input string.

    :param matte_str: Matte input string. Example: '"bunny", "flower"'
    :type matte_str: Matte input string.

    :rtype: table[string, bool]
    ]]
    -- get matte entries
    local name_array = module._string_split(matte_str, REGEX_MATTE_LIST)

    local name_set = {}
    for _, matte in ipairs(name_array) do
        -- detect double quote leading & trailing character
        if module._string_starts_with(matte, "\"") and module._string_ends_with(matte, "\"") then
            name = string.sub(matte, 2, matte:len() - 1)
            name_set[name] = true
        else
            module.log_error(string.format("invalid syntax for matte: %s", matte))
        end
    end
    return name_set
end

function module.get_layer_images(input_image, exr_path, layer_name, partnum)
    --[[
    Returns the images for all indices of layer.

    :param input_image: Source Cryptomatte image.
    :type input_image: Image

    :param exr_path: Absolite path to the EXR file.
    :type exr_path: string

    :param layer_name: Name of the layer to get all index images for.
    :type layer_name: string

    :param partnum: EXR multipart index.
    :type partnum: number

    :rtype: table[string, Image]
    ]]
    -- load EXR file for current time
    local exr = EXRIO()
    exr:ReadOpen(exr_path, -1)

    local layer_images = {}
    if exr:ReadHeader() then
        local channels = exr:GetChannels(partnum)
        local channel_hierarchy = module._get_channel_hierarchy(layer_name, channels)
        layer_images = get_layer_images(input_image, layer_name, channel_hierarchy, exr, partnum)
    end

    -- close EXR file pointer
    exr:Close()

    -- log EXRIO internal errors
    local exrio_error = exr:GetLastError()
    if exrio_error ~= "" then
        module.log_error(exrio_error)
    end

    return layer_images
end

function module.create_preview_image_colors(input_image, layer_images)
    --[[
    Creates the preview image of view mode "edges".

    :param input_image: Source Cryptomatte image.
    :type input_image: Image

    :param layer_images: Cryptomatte layer images.
    :type layer_images: table[number, Image]

    Algorithm:
    - see `create_preview_image_colors_scanline` function documentation

    :rtype: Image
    ]]
    local output_image = input_image:CopyOf()
    output_image:Clear()
    self:DoMultiProcess(create_preview_image_colors_init,
                        {output_image = output_image,
                         layer_0_image = layer_images[0],
                         layer_1_image = layer_images[1]},
                        output_image.DataWindow.top - output_image.DataWindow.bottom,
                        create_preview_image_colors_scanline)
    return output_image
end

function module.create_preview_image_edges(input_image, layer_images)
    --[[
    Creates the preview image of view mode "edges".

    :param input_image: Source Cryptomatte image.
    :type input_image: Image

    :param layer_images: Cryptomatte layer images.
    :type layer_images: table[number, Image]

    Algorithm:
    - output.r = input.r
    - output.g = input.g + (layer[0].a * 2)
    - output.b = input.b + (layer[0].a * 2)
    - output.a = input.a

    :rtype: Image
    ]]
    local coverage = layer_images[0]:CopyOf()
    coverage:Gain(1.0, 1.0, 1.0, 2.0)
    return input_image:ChannelOpOf("Add", coverage, {G="fg.A", B="fg.A"})
end

function module.create_matte_image(input_image, layer_images, manifest, matte_names)
    --[[
    Creates the monochannel matte images for selected names.

    :param input_image: Source Cryptomatte image
    :type input_image: Image

    :param layer_images: Cryptomatte layer images.
    :type layer_images: table[number, Image]

    :param manifest: Manifest storing matte id by name.
    :type manifest: table[string, string]

    :param matte_names: Selected mattes to isolate.
    :type matte_names: table[string, bool]

    Algorithm:
    - see `create_matte_image_scanline` function documentation

    :rtype: Image
    ]]
    local matte_values = {}
    for matte_name, _ in pairs(matte_names) do
        -- support background matte picking
        if matte_name == BACKGROUND_MATTE_NAME then
            matte_values[0.0] = true
        else
            local matte_id = manifest[matte_name]
            if matte_id == nil then
                module.log_error(string.format("matte not present in manifest: %s", matte_name))
            else
                local matte_value = module._hex_to_float(matte_id)
                matte_values[matte_value] = true
            end
        end
    end

    -- build monochannel matte image
    local output_image = Image({IMG_Like = input_image,
                                IMG_CopyChannels = false,
                                {IMG_Channel = "Alpha"}})
    output_image:Clear()
    local dod = input_image.DataWindow

    if matte_values then
        for _, layer_image in pairs(layer_images) do
            self:DoMultiProcess(create_matte_image_init,
                                {layer_image = layer_image,
                                 matte_values = matte_values,
                                 dod = dod,
                                 output_image = output_image},
                                dod.top - dod.bottom,
                                create_matte_image_scanline)
        end
    end

    return output_image
end

function module.get_screen_matte_name(input_image, layer_images, screen_pos, manifest)
    --[[
    Gets the name of a matte at given screen position.

    :param input_image: Source Cryptomatte image.
    :type input_image: Image

    :param layer_images: Cryptomatte layer images.
    :type layer_images: table[number, Image]

    :param screen_pos: Relative mouse position on canvas.
    :type screen_pos: Point

    :param manifest: Manifest storing matte id by name.
    :type manifest: table[string, string]

    :rtype: string or nil
    ]]
    -- get absolute screen position
    local x, y = module._get_absolute_position(input_image.Width, input_image.Height, screen_pos.X, screen_pos.Y)

    local dod = input_image.DataWindow
    if not module._is_position_in_rect(dod, x, y) then
        module.log_info(string.format("pixel (%s,%s) not present in data window (%s)", x, y, dod))
        return nil
    end

    -- get matte values from manifest to detect pixel matches from
    local matte_values = {}
    local matte_names_by_value = {}
    for matte_name, matte_id in pairs(manifest) do
        local matte_value = module._hex_to_float(matte_id)
        matte_values[matte_value] = true
        matte_names_by_value[matte_value] = matte_name
    end

    -- add background matte name/value
    matte_values[0.0] = true
    matte_names_by_value[0.0] = BACKGROUND_MATTE_NAME

    local matte_value = nil
    for layer_index, layer_image in pairs(layer_images) do
        -- get pixel at screen coordinates for current layer image
        local pixel = get_screen_pixel(layer_image, x, y)

        if pixel.R == 0.0 and pixel.G == 0.0 and pixel.B == 0.0 and pixel.A == 0.0 then
            -- background is being picked
            matte_value = 0.0
        else
            -- detect if any RGBA channel value matches a known matte float ID
            for _, value in ipairs({pixel.R, pixel.G, pixel.B, pixel.A}) do
                if value ~= 0.0 and matte_values[value] then
                    matte_value = value
                    break
                end
            end
        end

        if matte_value ~= nil then
            break
        end
    end

    if matte_value ~= nil then
        return matte_names_by_value[matte_value]
    end

    return nil
end

return module
