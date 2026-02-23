-- seed_data.sql — Demo data for PriceScout
-- Loaded as /docker-entrypoint-initdb.d/02-seed-data.sql

USE `capstone`;

-- --------------------------------------------------------
-- Demo user (username: demo_user / password: demo123)
-- --------------------------------------------------------

INSERT INTO `users` (`username`, `name`, `email`, `number`, `password`) VALUES
('demo_user', 'Demo User', 'demo@pricescout.dev', '9999999999',
 'pbkdf2:sha256:1000000$9pTF7StnpZLGqrsT$899dc0291dda768a51122eebb5c7e2d65b20874eac2e9a95ee9799aec4087eab');

-- --------------------------------------------------------
-- Vehicle listings (~20)
-- --------------------------------------------------------

INSERT INTO `vehicle` (`user_email`, `brand`, `name_model`, `location`, `vehicle_type`, `model_year`, `color`, `km_driven`, `mileage`, `fuel_type`, `transmission`, `owner_type`, `engine_capacity`, `power`, `seats`, `description`) VALUES
('demo@pricescout.dev', 'Maruti', 'Swift VXi', 'Mumbai', 'Hatchback', 2019, 'White', 35000, 22, 'Petrol', 'Manual', '1', '1197 cc', '83', 5, 'Well maintained, single owner, all service records available.'),
('demo@pricescout.dev', 'Maruti', 'Baleno Alpha', 'Delhi', 'Hatchback', 2020, 'Silver', 22000, 21, 'Petrol', 'Manual', '1', '1197 cc', '83', 5, 'Premium hatchback with projector headlamps and touchscreen.'),
('demo@pricescout.dev', 'Maruti', 'Dzire ZXi', 'Bangalore', 'Sedan', 2018, 'Grey', 48000, 23, 'Petrol', 'Automatic', '1', '1197 cc', '83', 5, 'Compact sedan, AGS transmission, excellent fuel economy.'),
('demo@pricescout.dev', 'Honda', 'City ZX CVT', 'Pune', 'Sedan', 2021, 'Red', 15000, 18, 'Petrol', 'Automatic', '1', '1498 cc', '121', 5, 'Latest gen City with Honda Sensing, lane watch camera.'),
('demo@pricescout.dev', 'Honda', 'Amaze S MT', 'Chennai', 'Sedan', 2019, 'White', 40000, 25, 'Diesel', 'Manual', '1', '1498 cc', '99', 5, 'Diesel variant, great mileage, ideal for long commutes.'),
('demo@pricescout.dev', 'Honda', 'WR-V SV', 'Hyderabad', 'SUV', 2020, 'Blue', 28000, 17, 'Petrol', 'Manual', '1', '1199 cc', '90', 5, 'Crossover SUV with high ground clearance and sunroof.'),
('demo@pricescout.dev', 'Hyundai', 'Creta SX', 'Mumbai', 'SUV', 2021, 'Black', 18000, 17, 'Petrol', 'Automatic', '1', '1497 cc', '115', 5, 'Top variant with panoramic sunroof, ventilated seats.'),
('demo@pricescout.dev', 'Hyundai', 'i20 Asta', 'Delhi', 'Hatchback', 2020, 'Red', 25000, 20, 'Petrol', 'Manual', '1', '1197 cc', '83', 5, 'Premium hatchback with BlueLink connected features.'),
('demo@pricescout.dev', 'Hyundai', 'Venue S', 'Kolkata', 'SUV', 2019, 'Orange', 32000, 18, 'Petrol', 'Manual', '1', '1197 cc', '83', 5, 'Compact SUV, great city car, wireless charging.'),
('demo@pricescout.dev', 'Hyundai', 'Verna SX', 'Bangalore', 'Sedan', 2020, 'Silver', 21000, 17, 'Petrol', 'Automatic', '1', '1497 cc', '115', 5, 'Feature-rich sedan with ventilated seats and sunroof.'),
('demo@pricescout.dev', 'Tata', 'Nexon XZ Plus', 'Pune', 'SUV', 2021, 'White', 12000, 17, 'Petrol', 'Manual', '1', '1199 cc', '120', 5, '5-star safety rated SUV with connected car tech.'),
('demo@pricescout.dev', 'Tata', 'Altroz XZ', 'Chennai', 'Hatchback', 2020, 'Blue', 20000, 20, 'Petrol', 'Manual', '1', '1199 cc', '86', 5, '5-star GNCAP rated premium hatchback.'),
('demo@pricescout.dev', 'Tata', 'Harrier XZA', 'Hyderabad', 'SUV', 2021, 'Grey', 15000, 14, 'Diesel', 'Automatic', '1', '1956 cc', '170', 5, 'Flagship SUV with panoramic sunroof, JBL audio.'),
('demo@pricescout.dev', 'Toyota', 'Fortuner 4x4 AT', 'Mumbai', 'SUV', 2020, 'White', 30000, 10, 'Diesel', 'Automatic', '1', '2755 cc', '177', 7, 'Full-size SUV, 4WD, cruise control, premium interior.'),
('demo@pricescout.dev', 'Toyota', 'Innova Crysta GX', 'Delhi', 'MPV', 2019, 'Silver', 55000, 12, 'Diesel', 'Manual', '1', '2393 cc', '150', 7, 'Reliable MPV, captain seats, perfect for families.'),
('demo@pricescout.dev', 'Toyota', 'Glanza G', 'Bangalore', 'Hatchback', 2021, 'Blue', 10000, 22, 'Petrol', 'Manual', '1', '1197 cc', '90', 5, 'Rebadged Baleno with Toyota reliability and warranty.'),
('demo@pricescout.dev', 'Maruti', 'Ertiga VXi', 'Pune', 'MPV', 2020, 'White', 38000, 19, 'Petrol', 'Manual', '1', '1462 cc', '105', 7, '7-seater MPV with spacious cabin and good mileage.'),
('demo@pricescout.dev', 'Honda', 'Jazz V CVT', 'Chennai', 'Hatchback', 2018, 'Red', 42000, 18, 'Petrol', 'Automatic', '1', '1199 cc', '90', 5, 'Magic seats, CVT gearbox, versatile cargo space.'),
('demo@pricescout.dev', 'Hyundai', 'Grand i10 Nios Sportz', 'Kolkata', 'Hatchback', 2020, 'Red', 19000, 20, 'Petrol', 'Manual', '1', '1197 cc', '83', 5, 'Affordable hatchback with wireless Apple CarPlay.'),
('demo@pricescout.dev', 'Tata', 'Punch Adventure', 'Hyderabad', 'SUV', 2022, 'Orange', 8000, 18, 'Petrol', 'Manual', '1', '1199 cc', '86', 5, 'Micro-SUV with 5-star safety, rain-sensing wipers.');

-- --------------------------------------------------------
-- Mobile listings (~10)
-- --------------------------------------------------------

INSERT INTO `mobiles` (`email`, `brand`, `model_name`, `sim_slots`, `processor`, `ram`, `storage_size`, `battery_size`, `display`, `camera`, `description`) VALUES
('demo@pricescout.dev', 'Samsung', 'Galaxy S23', 2, 'Snapdragon 8 Gen 2', 8, 128, 3900, '6.1 Dynamic AMOLED', '50MP Triple', 'Flagship phone with excellent camera and One UI.'),
('demo@pricescout.dev', 'Samsung', 'Galaxy A54', 2, 'Exynos 1380', 8, 128, 5000, '6.4 Super AMOLED', '50MP Triple', 'Mid-range with flagship display, IP67 water resistance.'),
('demo@pricescout.dev', 'Apple', 'iPhone 14', 1, 'A15 Bionic', 6, 128, 3279, '6.1 Super Retina XDR', '12MP Dual', 'Satellite SOS, crash detection, cinematic mode.'),
('demo@pricescout.dev', 'Apple', 'iPhone 13 Mini', 1, 'A15 Bionic', 4, 128, 2438, '5.4 Super Retina XDR', '12MP Dual', 'Compact flagship with all-day battery life.'),
('demo@pricescout.dev', 'OnePlus', '11 5G', 2, 'Snapdragon 8 Gen 2', 8, 128, 5000, '6.7 AMOLED LTPO', '50MP Hasselblad', 'Hasselblad camera, 100W SUPERVOOC charging.'),
('demo@pricescout.dev', 'OnePlus', 'Nord CE 3', 2, 'Snapdragon 782G', 8, 128, 5000, '6.7 AMOLED', '50MP Triple', 'Mid-range 5G phone with 80W fast charging.'),
('demo@pricescout.dev', 'Xiaomi', 'Redmi Note 12 Pro', 2, 'MediaTek Dimensity 1080', 6, 128, 5000, '6.67 AMOLED', '50MP Triple OIS', 'Great value with 120Hz AMOLED and 67W charging.'),
('demo@pricescout.dev', 'Xiaomi', '13 Pro', 2, 'Snapdragon 8 Gen 2', 12, 256, 4820, '6.73 AMOLED LTPO', '50MP Leica Triple', 'Premium flagship with Leica optics, 120W HyperCharge.'),
('demo@pricescout.dev', 'Samsung', 'Galaxy M34 5G', 2, 'Exynos 1280', 6, 128, 6000, '6.5 Super AMOLED', '50MP Triple', 'Monster battery, 5G connectivity, Knox security.'),
('demo@pricescout.dev', 'Apple', 'iPhone 15 Pro', 1, 'A17 Pro', 8, 256, 3274, '6.1 Super Retina XDR', '48MP Triple', 'Titanium design, Action button, USB-C, ProRes video.');

-- --------------------------------------------------------
-- Laptop listings (~10)
-- --------------------------------------------------------

INSERT INTO `laptops` (`email`, `brandlap`, `model`, `processor`, `ram_size`, `memory_type`, `memory_size`, `display_size`, `refresh_rate`, `battery`, `laptop_type`, `description`) VALUES
('demo@pricescout.dev', 'Dell', 'Inspiron 15 3520', 'Intel i5-1235U', 8, 'SSD', 512, 15.6, 60, 54, 'Notebook', 'Everyday laptop with 12th gen Intel, good for productivity.'),
('demo@pricescout.dev', 'Dell', 'XPS 13 9315', 'Intel i7-1250U', 16, 'SSD', 512, 13.4, 60, 51, 'Ultrabook', 'Premium ultrabook, InfinityEdge display, thunderbolt 4.'),
('demo@pricescout.dev', 'HP', 'Pavilion 15-eg2025', 'Intel i5-1240P', 16, 'SSD', 512, 15.6, 60, 41, 'Notebook', 'Stylish design, B&O audio, fingerprint reader.'),
('demo@pricescout.dev', 'HP', 'Victus 15', 'AMD Ryzen 5 5600H', 8, 'SSD', 512, 15.6, 144, 70, 'Gaming', 'Entry gaming laptop with GTX 1650, 144Hz display.'),
('demo@pricescout.dev', 'Lenovo', 'ThinkPad E14 Gen 4', 'Intel i5-1235U', 16, 'SSD', 512, 14, 60, 45, 'Business', 'Business ultrabook, MIL-STD tested, spill-resistant keyboard.'),
('demo@pricescout.dev', 'Lenovo', 'IdeaPad Gaming 3', 'AMD Ryzen 5 6600H', 8, 'SSD', 512, 15.6, 120, 60, 'Gaming', 'Budget gaming with RTX 3050, Nahimic audio.'),
('demo@pricescout.dev', 'Apple', 'MacBook Air M2', 'Apple M2', 8, 'SSD', 256, 13.6, 60, 52, 'Ultrabook', 'Fanless design, Liquid Retina display, MagSafe charging.'),
('demo@pricescout.dev', 'Apple', 'MacBook Pro 14 M2 Pro', 'Apple M2 Pro', 16, 'SSD', 512, 14.2, 120, 70, 'Workstation', 'Pro-grade performance, ProMotion display, long battery life.'),
('demo@pricescout.dev', 'ASUS', 'VivoBook 15 X1502', 'Intel i5-1235U', 8, 'SSD', 512, 15.6, 60, 42, 'Notebook', 'Lightweight everyday laptop with NumberPad touchpad.'),
('demo@pricescout.dev', 'ASUS', 'ROG Strix G15', 'AMD Ryzen 7 6800H', 16, 'SSD', 1024, 15.6, 165, 90, 'Gaming', 'High-end gaming with RTX 3060, per-key RGB keyboard.');

-- --------------------------------------------------------
-- Price entries (with realistic pre-computed values)
-- --------------------------------------------------------

INSERT INTO `price` (`email`, `post_id`, `post_type`, `brand`, `model`, `description`, `price`) VALUES
-- Vehicles
('demo@pricescout.dev', 1, 'vehicle', 'Maruti', 'Swift VXi', 'Well maintained, single owner.', 485000),
('demo@pricescout.dev', 2, 'vehicle', 'Maruti', 'Baleno Alpha', 'Premium hatchback.', 625000),
('demo@pricescout.dev', 3, 'vehicle', 'Maruti', 'Dzire ZXi', 'Compact sedan, AGS.', 520000),
('demo@pricescout.dev', 4, 'vehicle', 'Honda', 'City ZX CVT', 'Latest gen City.', 1050000),
('demo@pricescout.dev', 5, 'vehicle', 'Honda', 'Amaze S MT', 'Diesel variant.', 580000),
('demo@pricescout.dev', 6, 'vehicle', 'Honda', 'WR-V SV', 'Crossover SUV.', 720000),
('demo@pricescout.dev', 7, 'vehicle', 'Hyundai', 'Creta SX', 'Top variant SUV.', 1350000),
('demo@pricescout.dev', 8, 'vehicle', 'Hyundai', 'i20 Asta', 'Premium hatchback.', 750000),
('demo@pricescout.dev', 9, 'vehicle', 'Hyundai', 'Venue S', 'Compact SUV.', 680000),
('demo@pricescout.dev', 10, 'vehicle', 'Hyundai', 'Verna SX', 'Feature-rich sedan.', 920000),
('demo@pricescout.dev', 11, 'vehicle', 'Tata', 'Nexon XZ Plus', '5-star safety SUV.', 980000),
('demo@pricescout.dev', 12, 'vehicle', 'Tata', 'Altroz XZ', '5-star GNCAP.', 620000),
('demo@pricescout.dev', 13, 'vehicle', 'Tata', 'Harrier XZA', 'Flagship SUV.', 1750000),
('demo@pricescout.dev', 14, 'vehicle', 'Toyota', 'Fortuner 4x4 AT', 'Full-size SUV.', 3200000),
('demo@pricescout.dev', 15, 'vehicle', 'Toyota', 'Innova Crysta GX', 'Reliable MPV.', 1800000),
('demo@pricescout.dev', 16, 'vehicle', 'Toyota', 'Glanza G', 'Rebadged Baleno.', 590000),
('demo@pricescout.dev', 17, 'vehicle', 'Maruti', 'Ertiga VXi', '7-seater MPV.', 780000),
('demo@pricescout.dev', 18, 'vehicle', 'Honda', 'Jazz V CVT', 'Magic seats.', 540000),
('demo@pricescout.dev', 19, 'vehicle', 'Hyundai', 'Grand i10 Nios Sportz', 'Affordable hatch.', 510000),
('demo@pricescout.dev', 20, 'vehicle', 'Tata', 'Punch Adventure', 'Micro-SUV.', 720000),
-- Mobiles
('demo@pricescout.dev', 1, 'mobiles', 'Samsung', 'Galaxy S23', 'Flagship phone.', 59999),
('demo@pricescout.dev', 2, 'mobiles', 'Samsung', 'Galaxy A54', 'Mid-range phone.', 32999),
('demo@pricescout.dev', 3, 'mobiles', 'Apple', 'iPhone 14', 'Satellite SOS.', 69900),
('demo@pricescout.dev', 4, 'mobiles', 'Apple', 'iPhone 13 Mini', 'Compact flagship.', 55900),
('demo@pricescout.dev', 5, 'mobiles', 'OnePlus', '11 5G', 'Hasselblad camera.', 56999),
('demo@pricescout.dev', 6, 'mobiles', 'OnePlus', 'Nord CE 3', 'Mid-range 5G.', 24999),
('demo@pricescout.dev', 7, 'mobiles', 'Xiaomi', 'Redmi Note 12 Pro', 'Great value.', 24999),
('demo@pricescout.dev', 8, 'mobiles', 'Xiaomi', '13 Pro', 'Premium flagship.', 79999),
('demo@pricescout.dev', 9, 'mobiles', 'Samsung', 'Galaxy M34 5G', 'Monster battery.', 18999),
('demo@pricescout.dev', 10, 'mobiles', 'Apple', 'iPhone 15 Pro', 'Titanium design.', 134900),
-- Laptops
('demo@pricescout.dev', 1, 'laptops', 'Dell', 'Inspiron 15 3520', 'Everyday laptop.', 52990),
('demo@pricescout.dev', 2, 'laptops', 'Dell', 'XPS 13 9315', 'Premium ultrabook.', 109990),
('demo@pricescout.dev', 3, 'laptops', 'HP', 'Pavilion 15-eg2025', 'Stylish design.', 64990),
('demo@pricescout.dev', 4, 'laptops', 'HP', 'Victus 15', 'Entry gaming.', 57990),
('demo@pricescout.dev', 5, 'laptops', 'Lenovo', 'ThinkPad E14 Gen 4', 'Business ultrabook.', 72990),
('demo@pricescout.dev', 6, 'laptops', 'Lenovo', 'IdeaPad Gaming 3', 'Budget gaming.', 62990),
('demo@pricescout.dev', 7, 'laptops', 'Apple', 'MacBook Air M2', 'Fanless design.', 99900),
('demo@pricescout.dev', 8, 'laptops', 'Apple', 'MacBook Pro 14 M2 Pro', 'Pro-grade.', 189900),
('demo@pricescout.dev', 9, 'laptops', 'ASUS', 'VivoBook 15 X1502', 'Lightweight.', 49990),
('demo@pricescout.dev', 10, 'laptops', 'ASUS', 'ROG Strix G15', 'High-end gaming.', 124990);

-- --------------------------------------------------------
-- Ingestion log entries (healthy system history)
-- --------------------------------------------------------

INSERT INTO `ingestion_log` (`run_type`, `started_at`, `finished_at`, `listings_processed`, `listings_inserted`, `listings_deduped`, `errors`, `duration_seconds`, `status`, `error_detail`) VALUES
('form_vehicle', '2025-12-01 09:15:00', '2025-12-01 09:15:02', 5, 5, 0, 0, 2.1, 'success', NULL),
('form_mobile', '2025-12-05 14:30:00', '2025-12-05 14:30:01', 3, 3, 0, 0, 1.3, 'success', NULL),
('form_laptop', '2025-12-10 11:00:00', '2025-12-10 11:00:01', 4, 4, 0, 0, 1.5, 'success', NULL),
('scrape', '2025-12-15 08:00:00', '2025-12-15 08:05:30', 20, 18, 2, 0, 330.0, 'success', NULL),
('form_vehicle', '2025-12-20 16:45:00', '2025-12-20 16:45:03', 8, 5, 3, 0, 2.8, 'success', NULL);
