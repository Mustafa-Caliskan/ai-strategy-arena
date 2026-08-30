-- 2p_AI_Benchmark.lua
-- Battle for Wesnoth <-> Python OpenAI vs DeepSeek Bridge

local on_event = wesnoth.require("on_event")

local PIPE_PATHS = {
    "C:/Users/Mustafa/OneDrive/Masaüstü/oyun_projesi/ai_strategy_arena/wesnoth_bridge/pipe/state.json",
    "pipe/state.json",
    "../ai_strategy_arena/wesnoth_bridge/pipe/state.json"
}

local ORDERS_PATHS = {
    "C:/Users/Mustafa/OneDrive/Masaüstü/oyun_projesi/ai_strategy_arena/wesnoth_bridge/pipe/orders.json",
    "pipe/orders.json",
    "../ai_strategy_arena/wesnoth_bridge/pipe/orders.json"
}

local function write_json(tbl)
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

local function execute_ai_turn(side_number)
    local current_turn = wesnoth.current.turn
    local side_data = wesnoth.sides.get(side_number)
    local side_name = (side_number == 1) and "OpenAI (GPT-4o)" or "DeepSeek"
    local leader_id = (side_number == 1) and "OpenAI_Leader" or "DeepSeek_Leader"

    -- 1. Dost Birlikleri Topla
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

    -- 2. Düşman Birliklerini Topla
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

    -- 3. Game State Verisi
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

    local json_str = write_json(game_state)

    -- 4. State JSON Dosyasına Yaz
    for _, path in ipairs(PIPE_PATHS) do
        local f_out = io.open(path, "w")
        if f_out then
            f_out:write(json_str)
            f_out:close()
        end
    end

    -- 5. Python Sunucusundan Orders Gelmesini Bekle (Polling)
    local orders_content = nil
    local wait_start = os.clock()
    while not orders_content and (os.clock() - wait_start < 12.0) do
        for _, path in ipairs(ORDERS_PATHS) do
            local f_in = io.open(path, "r")
            if f_in then
                orders_content = f_in:read("*all")
                f_in:close()
                if orders_content and #orders_content > 5 then
                    os.remove(path)
                    break
                else
                    orders_content = nil
                end
            end
        end
        local t0 = os.clock()
        while os.clock() - t0 < 0.2 do end
    end

    -- 6. Düşünceyi Ayıkla ve Ekranda Diyalog Göster
    local thought = "Stratejik mevziler korunuyor."
    local order_desc = ""

    if orders_content then
        local t_match = string.match(orders_content, '"thought"%s*:%s*"([^"]+)"')
        if t_match then
            thought = t_match
        end
        local r_match = string.match(orders_content, '"recruits"%s*:%s*%[([^%]]*)%]')
        if r_match and #r_match > 0 then
            order_desc = "Asker: " .. r_match:gsub('"', '')
        end
    end

    -- Wesnoth Chat'e Canlı Strateji Mesajı
    wesnoth.interface.add_chat_message(side_name, string.format("🧠 Strateji: \"%s\"", thought))

    -- Generalin Başında Büyük Diyalog Kutusu Aç (Okuyup tıklandığında devam eder)
    local banner_msg = string.format("👑 %s (Tur %d):\n\n\"%s\"\n\n⚔️ %s", side_name, current_turn, thought, order_desc)
    pcall(function()
        wesnoth.wml.actions.message({
            speaker = leader_id,
            message = banner_msg,
        })
    end)
end

-- Turn Event Hooks
on_event("turn 1", function()
    execute_ai_turn(1)
end)

on_event("side 1 turn", function()
    execute_ai_turn(1)
end)

on_event("side 2 turn", function()
    execute_ai_turn(2)
end)