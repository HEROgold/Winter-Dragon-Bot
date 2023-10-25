CREATE TABLE IF NOT EXISTS
    guilds (id BIGINT PRIMARY KEY);

CREATE TABLE IF NOT EXISTS
    channel_types (name VARCHAR(15) PRIMARY KEY);

CREATE TABLE IF NOT EXISTS
    channels (
        id BIGINT PRIMARY KEY,
        name VARCHAR(50),
        type VARCHAR(15),
        guild_id BIGINT REFERENCES guilds (id)
    );

CREATE TABLE IF NOT EXISTS
    users (id BIGINT PRIMARY KEY);

CREATE TABLE IF NOT EXISTS
    messages (
        id BIGINT PRIMARY KEY,
        content VARCHAR(2000),
        user_id BIGINT REFERENCES users (id),
        channel_id BIGINT REFERENCES channels (id)
    );

CREATE TABLE IF NOT EXISTS
    reminders (
        id INTEGER PRIMARY KEY,
        content VARCHAR(2000),
        user_id BIGINT REFERENCES users (id),
        timestamp TIMESTAMP
    );

CREATE TABLE IF NOT EXISTS
    welcome (
        guild_id BIGINT PRIMARY KEY REFERENCES guilds (id),
        channel_id BIGINT REFERENCES channels (id),
        message VARCHAR(2048),
        enabled BOOLEAN
    );

CREATE TABLE IF NOT EXISTS
    nhie_questions (id INTEGER PRIMARY KEY, value VARCHAR);

CREATE TABLE IF NOT EXISTS
    wyr_questions (id INTEGER PRIMARY KEY, value VARCHAR);

CREATE TABLE IF NOT EXISTS
    games (name VARCHAR(15) PRIMARY KEY);

CREATE TABLE IF NOT EXISTS
    lobby_status (status VARCHAR(10) PRIMARY KEY);

CREATE TABLE IF NOT EXISTS
    lobbies (
        id BIGINT PRIMARY KEY REFERENCES messages (id) ON DELETE CASCADE,
        game VARCHAR(15) REFERENCES games (name),
        status VARCHAR(10) REFERENCES lobby_status (status)
    );

CREATE TABLE IF NOT EXISTS
    association_users_lobbies (
        lobby_id BIGINT REFERENCES lobbies (id) ON DELETE CASCADE,
        user_id BIGINT,
        PRIMARY KEY (lobby_id, user_id)
    );

CREATE TABLE IF NOT EXISTS
    results_mp (
        id INTEGER PRIMARY KEY,
        game VARCHAR(15) REFERENCES games (name),
        user_id BIGINT REFERENCES users (id),
        placement INTEGER
    );

CREATE TABLE IF NOT EXISTS
    results_1v1 (
        id INTEGER PRIMARY KEY,
        game VARCHAR(15) REFERENCES games (name),
        player_1 BIGINT REFERENCES users (id),
        player_2 BIGINT REFERENCES users (id),
        winner BIGINT REFERENCES users (id),
        loser BIGINT REFERENCES users (id)
    );

CREATE TABLE IF NOT EXISTS
    steam_users (id BIGINT PRIMARY KEY REFERENCES users (id));

CREATE TABLE IF NOT EXISTS
    steam_sales (
        id INTEGER PRIMARY KEY,
        title VARCHAR(50),
        url VARCHAR(200),
        sale_percent INTEGER,
        final_price FLOAT,
        is_dlc BOOLEAN,
        is_bundle BOOLEAN,
        update_datetime TIMESTAMP
    );

CREATE TABLE IF NOT EXISTS
    suggestions (
        id INTEGER PRIMARY KEY,
        type VARCHAR(50),
        is_verified BOOLEAN,
        content VARCHAR(2048)
    );

CREATE TABLE IF NOT EXISTS
    polls (
        id INTEGER PRIMARY KEY,
        channel_id BIGINT REFERENCES channels (id),
        message_id BIGINT REFERENCES messages (id),
        content TEXT,
        end_date TIMESTAMP
    );

CREATE TABLE IF NOT EXISTS
    association_users_polls (
        id INTEGER PRIMARY KEY,
        poll_id INTEGER REFERENCES polls (id),
        user_id BIGINT REFERENCES users (id),
        voted_value INTEGER
    );

CREATE TABLE IF NOT EXISTS
    servers (
        id INTEGER PRIMARY KEY,
        process_id INTEGER,
        name VARCHAR(50),
        status VARCHAR(15),
        run_path VARCHAR(255)
    );

CREATE TABLE IF NOT EXISTS
    hangman (
        id BIGINT PRIMARY KEY REFERENCES messages (id),
        word VARCHAR(24),
        letters VARCHAR(24)
    );

CREATE TABLE IF NOT EXISTS
    association_users_hangman (
        id INTEGER PRIMARY KEY,
        hangman_id BIGINT REFERENCES hangman (id),
        user_id BIGINT REFERENCES users (id),
        score INTEGER DEFAULT 0
    );

CREATE TABLE IF NOT EXISTS
    looking_for_groups (
        id INTEGER PRIMARY KEY,
        user_id BIGINT REFERENCES users (id),
        game_id VARCHAR(15) REFERENCES games (name)
    );

CREATE TABLE IF NOT EXISTS
    presence (
        id INTEGER PRIMARY KEY,
        user_id BIGINT REFERENCES users (id),
        status VARCHAR(15),
        date_time TIMESTAMP
    );

CREATE TABLE IF NOT EXISTS
    autochannels (
        id INTEGER PRIMARY KEY,
        channel_id BIGINT REFERENCES channels (id)
    );

CREATE TABLE IF NOT EXISTS
    autochannel_settings (
        id INTEGER PRIMARY KEY,
        channel_name TEXT,
        channel_limit INTEGER
    );

CREATE TABLE IF NOT EXISTS
    tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR,
        description VARCHAR,
        opened_at TIMESTAMP,
        closed_at TIMESTAMP,
        is_closed BOOLEAN,
        user_id BIGINT REFERENCES users (id),
        channel_id BIGINT REFERENCES channels (id)
    );

CREATE TABLE IF NOT EXISTS
    ticket_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP,
        action VARCHAR,
        details VARCHAR,
        ticket_id INTEGER REFERENCES tickets (id),
        responder_id BIGINT REFERENCES users (id)
    );

CREATE TABLE IF NOT EXISTS
    roles (id INTEGER PRIMARY KEY, name VARCHAR);

CREATE TABLE IF NOT EXISTS
    auto_assign (
        role_id INTEGER REFERENCES roles (id),
        guild_id BIGINT REFERENCES guilds (id),
        PRIMARY KEY (role_id, guild_id)
    );

CREATE TABLE IF NOT EXISTS
    incremental_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id BIGINT REFERENCES users (id),
        balance BIGINT,
        last_update TIMESTAMP
    );

CREATE TABLE IF NOT EXISTS
    incremental_gens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id BIGINT REFERENCES users (id),
        incremental_id INTEGER REFERENCES incremental_data (id),
        generator_id INTEGER,
        name VARCHAR(15),
        price INTEGER,
        generating FLOAT
    );

CREATE TABLE IF NOT EXISTS
    commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        qual_name VARCHAR(30),
        call_count INTEGER DEFAULT 0,
        parent_id INTEGER REFERENCES command_groups (id)
    );

CREATE TABLE IF NOT EXISTS
    command_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(30)
    );

CREATE TABLE IF NOT EXISTS
    association_user_command (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id BIGINT REFERENCES users (id),
        command_id INTEGER REFERENCES commands (id)
    );

CREATE TABLE IF NOT EXISTS
    synced_bans (user_id BIGINT PRIMARY KEY REFERENCES users (id));

CREATE TABLE IF NOT EXISTS
    sync_ban_guilds (
        guild_id BIGINT PRIMARY KEY REFERENCES guilds (id)
    );

CREATE TABLE IF NOT EXISTS
    guild_commands (
        guild_id BIGINT PRIMARY KEY REFERENCES guilds (id),
        command_id INTEGER REFERENCES commands (id)
    );

CREATE TABLE IF NOT EXISTS
    guild_roles (
        guild_id BIGINT PRIMARY KEY REFERENCES guilds (id),
        role_id INTEGER REFERENCES roles (id)
    );

CREATE TABLE IF NOT EXISTS
    infractions (id INTEGER PRIMARY KEY AUTOINCREMENT);