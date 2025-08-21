-- init.sql
-- Checkout Service Database Initialization
-- Version: 2.0 | Updated: 2024-06-20

BEGIN;

-- ======================
-- 1. TABLE DEFINITIONS
-- ======================

-- Products catalog
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    price INTEGER NOT NULL CHECK (price > 0),  -- Price in cents
    description TEXT,
    image_url VARCHAR(500) CHECK (image_url LIKE 'https://%'),
    origin_country VARCHAR(100),
    brand VARCHAR(100),
    material VARCHAR(100),
    category VARCHAR(100) NOT NULL,
    rating DECIMAL(3,2) CHECK (rating BETWEEN 0 AND 5),
    in_stock BOOLEAN DEFAULT true,
    release_date DATE,
    warranty_months INTEGER CHECK (warranty_months >= 0),
    weight_grams INTEGER CHECK (weight_grams >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Order transactions
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255) NOT NULL CHECK (customer_email LIKE '%@%.%'),
    total_price INTEGER NOT NULL CHECK (total_price > 0),
    status VARCHAR(50) DEFAULT 'pending' CHECK (
        status IN ('pending', 'processing', 'completed', 'failed', 'refunded')
    ),
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    zip VARCHAR(20),
    country VARCHAR(100) NOT NULL,
    stripe_charge_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Order line items
CREATE TABLE IF NOT EXISTS transaction_items (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    product_slug VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price_at_purchase INTEGER NOT NULL CHECK (price_at_purchase > 0),
    FOREIGN KEY (product_slug) REFERENCES products(slug)
);

-- ======================
-- 2. INDEXES
-- ======================

CREATE INDEX IF NOT EXISTS idx_products_slug ON products(slug);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_email ON transactions(customer_email);
CREATE INDEX IF NOT EXISTS idx_transactions_stripe ON transactions(stripe_charge_id);
CREATE INDEX IF NOT EXISTS idx_items_transaction ON transaction_items(transaction_id);

-- ======================
-- 3. SAMPLE DATA
-- ======================

-- Clear existing data (for development only)
DELETE FROM products;

INSERT INTO products (
    slug, name, price, description, image_url, 
    origin_country, brand, material, category, 
    rating, in_stock, release_date, warranty_months, weight_grams
) VALUES 
    ('espresso-machine', 'Espresso Machine', 19999, 
     'High-quality espresso machine with 15-bar pressure system.', 
     'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085', 
     'Italy', 'BrewMaster', 'Stainless Steel', 'Appliance', 
     4.8, true, '2024-01-15', 24, 4200),
    
    ('milk-frother', 'Milk Frother Pro', 3499, 
     'Automatic cold/hot milk frother with 3 settings.', 
     'https://images.unsplash.com/photo-1544787219-7f47ccb76574', 
     'Germany', 'CafeTech', 'Stainless Steel', 'Accessory', 
     4.6, true, '2024-03-10', 12, 650),
    
    -- Additional 8 products with similar structure...
    ('coffee-subscription', 'Premium Coffee Subscription', 2999,
     'Monthly delivery of specialty grade coffee beans.',
     'https://images.unsplash.com/photo-1505576399279-565b52d4ac71',
     'Multiple', 'BeanBox', 'N/A', 'Subscription',
     4.7, true, '2024-01-01', 0, 1);

-- ======================
-- 4. SECURITY SETUP
-- ======================

-- Create application roles (run separately with admin privileges)
/*
CREATE ROLE checkout_app LOGIN PASSWORD 'secure_password_123';
GRANT CONNECT ON DATABASE checkoutdb TO checkout_app;
GRANT USAGE ON SCHEMA public TO checkout_app;
GRANT SELECT ON products TO checkout_app;
GRANT SELECT, INSERT ON transactions, transaction_items TO checkout_app;
*/

COMMIT;

-- ======================
-- 5. MAINTENANCE SETUP
-- ======================

-- Recommended to run after initial setup:
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
-- CREATE EXTENSION IF NOT EXISTS pgcrypto;