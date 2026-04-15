<?php
/**
 * Event Action Logs page for Sport Event Bot
 * Usage: event_logs.php?event=123
 */

// Load configuration
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
            if (empty($line) || strpos($line, '#') === 0) continue;
            if (strpos($line, '=') !== false) {
                list($name, $value) = explode('=', $line, 2);
                $name = trim($name);
                $value = trim($value);
                $value = trim($value, '"\'');
                putenv("$name=$value");
                $_ENV[$name] = $value;
            }
        }
    }

    define('DB_TYPE', getenv('DB_TYPE') ?: 'pgsql');
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
    if (DB_TYPE === 'pgsql' && defined('DB_SSLMODE')) {
        $dsn .= ";sslmode=" . DB_SSLMODE;
    }
    $pdo = new PDO($dsn, DB_USER, DB_PASS, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
} catch (PDOException $e) {
    die('Database connection failed: ' . $e->getMessage());
}

// Get event_id
$event_id = isset($_GET['event']) && is_numeric($_GET['event']) ? (int)$_GET['event'] : null;

if (!$event_id) {
    die('Event ID is required. Usage: event_logs.php?event=ID');
}

// Get event info
$stmt = $pdo->prepare('SELECT description FROM Events WHERE event_id = ?');
$stmt->execute([$event_id]);
$event = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$event) {
    die('Event not found');
}

// Get logs from DB
$stmt = $pdo->prepare('SELECT message, operation_datetime FROM EventLogs WHERE event_id = ? ORDER BY log_id DESC');
$stmt->execute([$event_id]);
$logs = $stmt->fetchAll(PDO::FETCH_ASSOC);

// Fallback to file logs if DB is empty or as additional info
$file_logs = [];
$log_file = __DIR__ . "/logs/event_{$event_id}.log";
if (file_exists($log_file)) {
    $file_content = file($log_file);
    foreach ($file_content as $line) {
        $file_logs[] = trim($line);
    }
    $file_logs = array_reverse($file_logs);
}

?>
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Журнал действий: <?= htmlspecialchars($event['description']) ?></title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f8fafc;
            color: #334155;
        }
        h1 { font-size: 1.5rem; color: #0f172a; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }
        .back-link { display: inline-block; margin-bottom: 20px; color: #3b82f6; text-decoration: none; font-size: 0.9rem; }
        .back-link:hover { text-decoration: underline; }
        
        .log-container {
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .log-item {
            padding: 12px 15px;
            border-bottom: 1px solid #f1f5f9;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .log-item:last-child { border-bottom: none; }
        .log-time { font-size: 0.75rem; color: #94a3b8; font-weight: 600; }
        .log-message { font-size: 0.95rem; line-height: 1.4; color: #1e293b; }
        
        .empty { padding: 40px; text-align: center; color: #94a3b8; font-style: italic; }
        
        .badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.7rem;
            text-transform: uppercase;
            font-weight: bold;
            margin-right: 5px;
        }
        .badge-db { background: #dbeafe; color: #1e40af; }
        .badge-file { background: #fef9c3; color: #854d0e; }
    </style>
</head>
<body>
    <a href="payments.php?event=<?= $event_id ?>" class="back-link">← К списку оплат</a>
    <h1>Журнал действий: <?= htmlspecialchars($event['description']) ?></h1>

    <div class="log-container">
        <?php if (empty($logs) && empty($file_logs)): ?>
            <div class="empty">Записей в журнале пока нет</div>
        <?php else: ?>
            <?php 
            // Merge or just show DB logs first
            if (!empty($logs)): 
                foreach ($logs as $l): ?>
                    <div class="log-item">
                        <span class="log-time"><?= date('Y-m-d H:i:s', strtotime($l['operation_datetime'])) ?> <span class="badge badge-db">DB</span></span>
                        <span class="log-message"><?= htmlspecialchars($l['message']) ?></span>
                    </div>
                <?php endforeach; 
            endif; 
            
            if (!empty($file_logs) && empty($logs)): // Show file logs if DB is empty (e.g. pruned)
                foreach ($file_logs as $fl): 
                    // File format was "[TIME] MESSAGE"
                    if (preg_match('/^\[(.*?)\] (.*)$/', $fl, $matches)): ?>
                        <div class="log-item">
                            <span class="log-time"><?= htmlspecialchars($matches[1]) ?> <span class="badge badge-file">FILE</span></span>
                            <span class="log-message"><?= htmlspecialchars($matches[2]) ?></span>
                        </div>
                    <?php else: ?>
                        <div class="log-item">
                            <span class="log-message"><?= htmlspecialchars($fl) ?></span>
                        </div>
                    <?php endif; ?>
                <?php endforeach; 
            endif;
            ?>
        <?php endif; ?>
    </div>

    <div style="margin-top: 30px; font-size: 0.8rem; color: #94a3b8; text-align: center;">
        Для экономии места в базе данных хранится до 100 последних записей.
    </div>
</body>
</html>
