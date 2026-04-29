<?php
/**
 * Events Index Page for Sport Event Bot
 * Shows a list of all events with links to payments and stats.
 */

// Load configuration from config.php or environment
$config_file = __DIR__ . '/config.php';
$env_file = __DIR__ . '/../.env';

if (file_exists($config_file)) {
    require_once $config_file;
} else {
    $dev_env = __DIR__ . '/../.env.development';
    if (file_exists($dev_env)) $env_file = $dev_env;

    if (file_exists($env_file)) {
        $lines = file($env_file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        foreach ($lines as $line) {
            $line = trim($line);
            if (empty($line) or strpos($line, '#') === 0) continue;
            if (strpos($line, '=') !== false) {
                list($name, $value) = explode('=', $line, 2);
                $name = trim($name); $value = trim($value, " \"'");
                putenv("$name=$value");
                $_ENV[$name] = $value;
            }
        }
    }
    define('DB_TYPE', getenv('DB_HOST') ? (getenv('DB_TYPE') ?: 'pgsql') : 'pgsql');
    define('DB_HOST', getenv('DB_HOST') ?: 'localhost');
    define('DB_PORT', getenv('DB_PORT') ?: '5432');
    define('DB_NAME', getenv('DB_NAME') ?: '');
    define('DB_USER', getenv('DB_USER') ?: '');
    define('DB_PASS', getenv('DB_PASS') ?: '');
    define('DB_SSLMODE', getenv('DB_SSLMODE') ?: 'require');
}

// Database connection
try {
    $dsn = DB_TYPE . ":host=" . DB_HOST . ";port=" . DB_PORT . ";dbname=" . DB_NAME;
    if (DB_TYPE === 'pgsql' && defined('DB_SSLMODE')) $dsn .= ";sslmode=" . DB_SSLMODE;
    $pdo = new PDO($dsn, DB_USER, DB_PASS, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
} catch (PDOException $e) {
    die('Database connection failed: ' . $e->getMessage());
}

// Cache settings
$cache_file = '/tmp/sport_event_bot_cache.json';
$cache_time = 60; // seconds

$events = [];
$from_cache = false;

if (file_exists($cache_file) && (time() - filemtime($cache_file) < $cache_time)) {
    $events = json_decode(file_get_contents($cache_file), true);
    if ($events !== null) {
        $from_cache = true;
    }
}

if (!$from_cache) {
    // Fetch events with participant counts using optimized JOIN
    $query = "
        SELECT e.*, 
               COALESCE(p_stats.participant_count, 0) as participant_count,
               COALESCE(p_stats.paid_count, 0) as paid_count
        FROM (
            SELECT * FROM Events ORDER BY event_id DESC LIMIT 50
        ) e
        LEFT JOIN (
            SELECT event_id, 
                   COUNT(*) as participant_count,
                   SUM(CASE WHEN paid = TRUE THEN 1 ELSE 0 END) as paid_count
            FROM Participants
            WHERE event_id IN (SELECT event_id FROM Events ORDER BY event_id DESC LIMIT 50)
            GROUP BY event_id
        ) p_stats ON e.event_id = p_stats.event_id
        ORDER BY e.event_id DESC
    ";
    
    try {
        $stmt = $pdo->query($query);
        $events = $stmt->fetchAll(PDO::FETCH_ASSOC);
        // Save to cache
        file_put_contents($cache_file, json_encode($events));
    } catch (PDOException $e) {
        // Fallback or error handling
        if (empty($events)) {
            die('Database error: ' . $e->getMessage());
        }
    }
}

?>

<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Спортивные События</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --glass: rgba(255, 255, 255, 0.05);
        }

        * { box-sizing: border-box; }
        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }

        .container {
            width: 100%;
            max-width: 800px;
        }

        header {
            text-align: center;
            margin-bottom: 40px;
        }

        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            color: var(--text-dim);
            font-size: 1.1rem;
        }

        .event-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
        }

        @media (min-width: 640px) {
            .event-grid { grid-template-columns: 1fr; }
        }

        .event-card {
            background: var(--card-bg);
            border-radius: 16px;
            padding: 24px;
            text-decoration: none;
            color: inherit;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }

        .event-card:hover {
            transform: translateY(-4px);
            border-color: var(--primary);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }

        .event-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; width: 4px; height: 100%;
            background: var(--primary);
            opacity: 0;
            transition: opacity 0.3s;
        }
        .event-card:hover::before { opacity: 1; }

        .event-main { flex: 1; }

        .event-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 8px;
            display: block;
        }

        .event-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            font-size: 0.9rem;
            color: var(--text-dim);
        }

        .meta-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .event-status {
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .status-open { background: rgba(16, 185, 129, 0.1); color: var(--accent-green); }
        .status-closed { background: rgba(239, 68, 68, 0.1); color: var(--accent-red); }

        .event-stats {
            text-align: right;
            margin-left: 20px;
        }

        .players-count {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-main);
        }

        .players-label {
            font-size: 0.75rem;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .empty-state {
            text-align: center;
            padding: 60px;
            background: var(--card-bg);
            border-radius: 16px;
            color: var(--text-dim);
        }

        .footer {
            margin-top: 60px;
            text-align: center;
            color: var(--text-dim);
            font-size: 0.875rem;
        }

        /* Micro-animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .event-card {
            animation: fadeIn 0.5s ease-out forwards;
        }

        .no-location { font-style: italic; opacity: 0.6; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div style="display: flex; justify-content: center; align-items: center; gap: 20px; margin-bottom: 20px;">
                <a href="statistics.php" style="text-decoration: none; display: flex; align-items: center; gap: 8px; font-weight: 600; color: var(--text-dim); background: var(--glass); padding: 8px 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); transition: all 0.3s;" onmouseover="this.style.borderColor= 'var(--primary)'; this.style.color='var(--text-main)'" onmouseout="this.style.borderColor='rgba(255,255,255,0.1)'; this.style.color='var(--text-dim)'">
                    📊 Statistics
                </a>
            </div>
            <h1>Sport Event Dashboard</h1>
            <p class="subtitle">Управляйте своими играми и платежами</p>
        </header>

        <div class="event-grid">
            <?php if (empty($events)): ?>
                <div class="empty-state">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🏟️</div>
                    <p>Событий пока нет. Создайте первое событие в боте!</p>
                </div>
            <?php else: ?>
                <?php foreach ($events as $index => $event): ?>
                    <a href="event.php?event=<?= $event['event_id'] ?>" class="event-card" style="animation-delay: <?= $index * 0.1 ?>s">
                        <div class="event-main">
                            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                                <span class="event-title"><?= htmlspecialchars($event['description'] ?: 'Событие #' . $event['event_id']) ?></span>
                                <span class="event-status <?= strtolower($event['status']) === 'open' ? 'status-open' : 'status-closed' ?>">
                                    <?= strtolower($event['status']) === 'open' ? 'Открыто' : 'Закрыто' ?>
                                </span>
                            </div>
                            
                            <div class="event-meta">
                                <div class="meta-item">
                                    <span>📅</span>
                                    <span><?= htmlspecialchars($event['datetime'] ?: 'Дата не указана') ?></span>
                                </div>
                                <div class="meta-item">
                                    <span>📍</span>
                                    <span class="<?= (empty($event['location']) || $event['location'] === 'null') ? 'no-location' : '' ?>">
                                        <?= htmlspecialchars(($event['location'] ?? '') ?: 'Место не указано') ?>
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div class="event-stats">
                            <div class="players-count">
                                <?= (int)$event['participant_count'] ?><span style="color: var(--text-dim); font-size: 1rem; font-weight: 400;">/<?= (int)$event['players_limit'] ?: '∞' ?></span>
                            </div>
                            <div class="players-label">Участников</div>
                            <?php if ((int)$event['paid_count'] > 0): ?>
                                <div style="font-size: 0.7rem; color: var(--accent-green); margin-top: 4px; font-weight: 600;">
                                    💰 <?= (int)$event['paid_count'] ?> оплачено
                                </div>
                            <?php endif; ?>
                        </div>
                    </a>
                <?php endforeach; ?>
            <?php endif; ?>
        </div>

        <div class="footer">
            Generated at <?= date('Y-m-d H:i:s') ?> • Sport Event Bot
        </div>
    </div>
</body>
</html>
