-- ai_arena_bridge.lua
-- Battle for Wesnoth <-> Python LLM Benchmark Arena Bridge (Enhanced HUD & Dialogue)

local bridge = {}

local PIPE_DIR = "C:/Users/Mustafa/OneDrive/Masaüstü/oyun_projesi/ai_strategy_arena/wesnoth_bridge/pipe"
local STATE_FILE = PIPE_DIR .. "/state.json"
local ORDERS_FILE = PIPE_DIR .. "/orders.json"

local function serialize_to_json(tbl)
    local function serialize_val(val)
        local t = type(val)
        if t == "number" or t == "boolean" then
            return tostring(val)
        elseif t == "string" then
            return string.format("%q", val)
        elseif t == "table" then
            local is_array = true
            local max_idx = 0
            for k, _ in pairs(val) do
                if type(k) ~= "number" then
                    is_array = false
                    break
                else
                    if k > max_idx then max_idx = k end
                end
            end
            if is_array and max_idx > 0 then
                local parts = {}
                for i = 1, max_idx do
                    table.insert(parts, serialize_val(val[i]))
                end
                return "[" .. table.concat(parts, ",") .. "]"
            else
                local parts = {}
                for k, v in pairs(val) do
                    table.insert(parts, string.format("%q:%s", tostring(k), serialize_val(v)))
                end
                return "{" .. table.concat(parts, ",") .. "}"
            end
        else
            return "null"
        end
    end
    return serialize_val(tbl)
end

function bridge.on_turn(side_number)
    local current_turn = wesnoth.current.turn
    local side_data = wesnoth.sides.get(side_number)
    local side_name = (side_number == 1) and "OpenAI (GPT-4o)" or "DeepSeek"
    local leader_id = (side_number == 1) and "OpenAI_Leader" or "DeepSeek_Leader"

    -- 1. Friendly Units
    local friendly_units = {}
    local all_units = wesnoth.units.find_on_map({ side = side_number })
    for _, u in ipairs(all_units) do
        table.insert(friendly_units, {
            id = u.id,
            name = u.name,
            type = u.type,
            x = u.x,
            y = u.y,
            hp = u.hitpoints,
            max_hp = u.max_hitpoints,
            moves = u.moves,
            can_attack = (u.attacks_left > 0),
        })
    end

    -- 2. Enemy Units
    local enemy_units = {}
    local enemy_side = (side_number == 1) and 2 or 1
    local enemies = wesnoth.units.find_on_map({ side = enemy_side })
    for _, e in ipairs(enemies) do
        table.insert(enemy_units, {
            id = e.id,
            name = e.name,
            type = e.type,
            x = e.x,
            y = e.y,
            hp = e.hitpoints,
            max_hp = e.max_hitpoints,
        })
    end

    -- 3. Game State
    local game_state = {
        turn = current_turn,
        side = side_number,
        side_name = side_name,
        gold = side_data.gold,
        villages = side_data.village_count,
        recruits = side_data.recruit,
        units = friendly_units,
        enemies = enemy_units,
    }

    -- 4. Write State JSON
    local json_str = serialize_to_json(game_state)
    local f_out = io.open(STATE_FILE, "w")
    if not f_out then
        f_out = io.open("pipe/state.json", "w")
    end
    if f_out then
        f_out:write(json_str)
        f_out:close()
    end

    -- 5. Poll for Orders from Python Server
    local orders_content = nil
    local wait_start = os.clock()
    while not orders_content and (os.clock() - wait_start < 15.0) do
        local f_in = io.open(ORDERS_FILE, "r")
        if not f_in then
            f_in = io.open("pipe/orders.json", "r")
        end
        if f_in then
            orders_content = f_in:read("*all")
            f_in:close()
            if orders_content and #orders_content > 5 then
                os.remove(ORDERS_FILE)
                os.remove("pipe/orders.json")
                break
            else
                orders_content = nil
            end
        end
        local t0 = os.clock()
        while os.clock() - t0 < 0.2 do end
    end

    -- 6. Düşünce ve Emirleri Ekranda Göster
    local thought = "Defending our strategic positions."
    local order_desc = ""

    if orders_content then
        -- Thought ve orders'ı ayıkla
        local t_match = string.match(orders_content, '"thought"%s*:%s*"([^"]+)"')
        if t_match then
            thought = t_match
        end
        local r_match = string.match(orders_content, '"recruits"%s*:%s*%[([^%]]*)%]')
        if r_match and #r_match > 0 then
            order_desc = order_desc .. "Recruits: " .. r_match:gsub('"', '') .. " | "
        end
    end

    -- Wesnoth Chat'e Canlı Emir Yazısı
    wesnoth.interface.add_chat_message(side_name, string.format("🧠 [STRATEGY]: \"%s\"", thought))
    if #order_desc > 0 then
        wesnoth.interface.add_chat_message(side_name, string.format("⚔️ [ORDERS]: %s", order_desc))
    end

    -- Generalin Başının Üzerinde Büyük Konuşma Penceresi Göster (Tıklayınca Geçer)
    if #friendly_units > 0 then
        local leader = friendly_units[1]
        local banner_msg = string.format("👑 %s (Tur %d):\n\n\"%s\"\n\n⚔️ %s", side_name, current_turn, thought, order_desc)
        pcall(function()
            wesnoth.wml.actions.message({
                speaker = leader_id,
                message = banner_msg,
            })
        end)
    end
end

return bridge