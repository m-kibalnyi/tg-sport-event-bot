<?php
/**
 * Database configuration for payment page
 * Copy this file to config.php and fill in your credentials
 */

define('DB_TYPE', 'pgsql'); // 'mysql' or 'pgsql'
define('DB_HOST', 'localhost');
define('DB_PORT', '5432');
define('DB_NAME', 'neondb');
define('DB_USER', 'neondb_owner');
define('DB_PASS', 'your_password_here');
define('DB_SSLMODE', 'require');

// You can add default BLIK phone here if you want it to be global
// define('GLOBAL_BLIK_PHONE', '+48123456789');
