-- 1. Create the reusable trigger function (one-time setup)
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = current_timestamp;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. users table + trigger
create table users (
    user_id uuid primary key default gen_random_uuid(),
    first_name varchar(50) not null,
    last_name varchar(50) not null,
    email varchar(254) not null unique,
    password_hash varchar(255) not null,
    rf_token varchar(255) not null,
    created_at timestamp default current_timestamp,
    updated_at timestamp default current_timestamp
);

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- 3. objects table + trigger
CREATE TABLE objects (
    object_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid REFERENCES users(user_id) ON DELETE CASCADE,
    object_name varchar(100) NOT NULL,
    object_type varchar(50)  NOT NULL,
    object_url  text         NOT NULL,
    created_at  timestamp DEFAULT current_timestamp,
    updated_at  timestamp DEFAULT current_timestamp
);

CREATE TRIGGER trg_objects_updated_at
BEFORE UPDATE ON objects
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
