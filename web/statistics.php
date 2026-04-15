<?php
/**
 * Statistics page for Sport Event Bot (PostgreSQL version)
 * Shows aggregated participation metrics over a selected period.
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

// Get filter parameters
$start_date = $_GET['start'] ?? date('Y-m-d', strtotime('-30 days'));
$end_date = $_GET['end'] ?? date('Y-m-d');
$chat_id = isset($_GET['chat']) && is_numeric($_GET['chat']) ? (int)$_GET['chat'] : null;

// Get available chats for filter
$stmt = $pdo->query("SELECT chat_id, extra1 FROM Chats ORDER BY chat_id");
$chats = $stmt->fetchAll(PDO::FETCH_ASSOC);

// Primary query for statistics
$query = "
WITH date_range_events AS (
    SELECT event_id FROM Events 
    WHERE datetime >= :start_date AND datetime <= :end_date
    " . ($chat_id ? "AND chat_id = :chat_id" : "") . "
),
attended_stats AS (
    SELECT user_id, COUNT(*) as count FROM Participants 
    WHERE event_id IN (SELECT event_id FROM date_range_events)
    GROUP BY user_id
),
revoked_stats AS (
    SELECT user_id, COUNT(*) as count FROM Revoked 
    WHERE event_id IN (SELECT event_id FROM date_range_events)
    GROUP BY user_id
),
thinking_stats AS (
    SELECT user_id, COUNT(*) as count FROM Thinking 
    WHERE event_id IN (SELECT event_id FROM date_range_events)
    GROUP BY user_id
),
legioneer_stats AS (
    SELECT invited_by as user_id, COUNT(*) as count FROM Participants 
    WHERE event_id IN (SELECT event_id FROM date_range_events) AND invited_by IS NOT NULL
    GROUP BY invited_by
),
penalty_stats AS (
    SELECT user_id, COUNT(*) as count FROM Penalties 
    WHERE operation_datetime >= :start_date::timestamp AND operation_datetime <= :end_date::timestamp
    " . ($chat_id ? "AND chat_id = :chat_id" : "") . "
    GROUP BY user_id
)
SELECT 
    u.user_id, u.first_name, u.last_name, u.username,
    COALESCE(a.count, 0) as attended,
    COALESCE(r.count, 0) as skipped,
    COALESCE(t.count, 0) as thinking,
    COALESCE(l.count, 0) as invited_legioneers,
    COALESCE(p.count, 0) as yellow_cards
FROM Users u
LEFT JOIN attended_stats a ON u.user_id = a.user_id
LEFT JOIN revoked_stats r ON u.user_id = r.user_id
LEFT JOIN thinking_stats t ON u.user_id = t.user_id
LEFT JOIN legioneer_stats l ON u.user_id = l.user_id
LEFT JOIN penalty_stats p ON u.user_id = p.user_id
WHERE COALESCE(a.count, 0) + COALESCE(r.count, 0) + COALESCE(t.count, 0) + COALESCE(p.count, 0) > 0
ORDER BY attended DESC, yellow_cards ASC, skipped ASC;
";

$stmt = $pdo->prepare($query);
$params = [
    ':start_date' => $start_date . ' 00:00:00',
    ':end_date' => $end_date . ' 23:59:59'
];
if ($chat_id) $params[':chat_id'] = $chat_id;
$stmt->execute($params);
$stats = $stmt->fetchAll(PDO::FETCH_ASSOC);

// Fetch active penalties for the right-side container
$active_penalties_query = "
    SELECT u.user_id, u.first_name, u.last_name, u.username, p.expires_at 
    FROM Penalties p
    JOIN Users u ON p.user_id = u.user_id AND p.platform = u.platform
    WHERE (p.expires_at IS NULL OR p.expires_at > NOW())
    " . ($chat_id ? "AND p.chat_id = :chat_id" : "") . "
    ORDER BY p.expires_at ASC;
";
$stmt_p = $pdo->prepare($active_penalties_query);
if ($chat_id) $stmt_p->execute([':chat_id' => $chat_id]);
else $stmt_p->execute();
$active_penalties = $stmt_p->fetchAll(PDO::FETCH_ASSOC);

function formatName($row) {
    if ($row['user_id'] >= 10 && $row['user_id'] < 30) return "Legioneer " . $row['user_id'];
    $name = trim(($row['first_name'] ?? '') . ' ' . ($row['last_name'] ?? ''));
    $username = $row['username'] ?? '';
    if ($name && $username) return "$name ($username)";
    return $name ?: $username ?: ('ID: ' . $row['user_id']);
}
?>
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Статистика игр</title>
    <style>
        :root {
            --primary: #2563eb;
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #1e293b;
            --border: #e2e8f0;
        }
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 20px;
            line-height: 1.5;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        header {
            margin-bottom: 30px;
            text-align: center;
        }
        h1 { font-size: 2rem; margin: 0; color: #0f172a; }
        
        .filters {
            background: var(--card);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: flex-end;
        }
        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        label { font-size: 0.875rem; font-weight: 600; color: #64748b; }
        input, select {
            padding: 8px 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
        }
        input:focus, select:focus { border-color: var(--primary); }
        button {
            background: var(--primary);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        button:hover { opacity: 0.9; }

        .stats-table-wrapper {
            background: var(--card);
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }
        th {
            background: #f1f5f9;
            padding: 12px 15px;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.025em;
            color: #475569;
        }
        td {
            padding: 12px 15px;
            border-bottom: 1px solid var(--border);
        }
        tr:last-child td { border-bottom: none; }
        tr:hover { background: #f8fafc; }
        
        .name-cell { font-weight: 500; color: #0f172a; }
        .num-cell { text-align: center; font-variant-numeric: tabular-nums; }
        
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        .badge-green { background: #dcfce7; color: #166534; }
        .badge-red { background: #fee2e2; color: #991b1b; }
        .badge-yellow { background: #fef9c3; color: #854d0e; }
        .badge-blue { background: #dbeafe; color: #1e40af; }

        .main-content {
            display: flex;
            gap: 30px;
            align-items: flex-start;
        }
        .stats-main {
            flex: 2;
        }
        .stats-sidebar {
            flex: 1;
            background: var(--card);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            position: sticky;
            top: 20px;
        }
        .sidebar-title {
            font-size: 1.125rem;
            font-weight: 700;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
            color: #0f172a;
        }
        .penalty-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .penalty-item {
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }
        .penalty-item:last-child { border-bottom: none; }
        .penalty-name { font-weight: 600; display: block; }
        .penalty-expiry { font-size: 0.8125rem; color: #64748b; }

        @media (max-width: 900px) {
            .main-content { flex-direction: column; }
            .stats-sidebar { width: 100%; position: static; box-sizing: border-box; }
        }

        @media (max-width: 600px) {
            .filters { flex-direction: column; align-items: stretch; }
            table { font-size: 0.875rem; }
            th, td { padding: 8px 10px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Статистика участия</h1>
        </header>

        <form class="filters" method="GET">
            <div class="filter-group">
                <label>От</label>
                <input type="date" name="start" value="<?= htmlspecialchars($start_date) ?>">
            </div>
            <div class="filter-group">
                <label>До</label>
                <input type="date" name="end" value="<?= htmlspecialchars($end_date) ?>">
            </div>
            <?php if (count($chats) > 1): ?>
            <div class="filter-group">
                <label>Чат</label>
                <select name="chat">
                    <option value="">Все чаты</option>
                    <?php foreach ($chats as $c): ?>
                        <option value="<?= $c['chat_id'] ?>" <?= $chat_id == $c['chat_id'] ? 'selected' : '' ?>>
                            <?= htmlspecialchars($c['chat_id']) ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>
            <?php endif; ?>
            <button type="submit">Применить</button>
        </form>

        <div class="main-content">
            <div class="stats-main">
                <div class="stats-table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>Игрок</th>
                                <th class="num-cell">Игр</th>
                                <th class="num-cell">Скип</th>
                                <th class="num-cell">Думал</th>
                                <th class="num-cell">Леги</th>
                                <th class="num-cell">🟨</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php if (empty($stats)): ?>
                                <tr>
                                    <td colspan="6" style="text-align: center; padding: 40px; color: #64748b;">
                                        Нет данных за этот период
                                    </td>
                                </tr>
                            <?php else: ?>
                                <?php foreach ($stats as $s): ?>
                                    <tr>
                                        <td class="name-cell"><?= htmlspecialchars(formatName($s)) ?></td>
                                        <td class="num-cell">
                                            <span class="badge badge-green"><?= $s['attended'] ?></span>
                                        </td>
                                        <td class="num-cell">
                                            <span class="badge badge-red"><?= $s['skipped'] ?></span>
                                        </td>
                                        <td class="num-cell">
                                            <span class="badge badge-blue"><?= $s['thinking'] ?></span>
                                        </td>
                                        <td class="num-cell">
                                            <span class="badge badge-blue"><?= $s['invited_legioneers'] ?></span>
                                        </td>
                                        <td class="num-cell">
                                            <span class="badge badge-yellow"><?= $s['yellow_cards'] ?></span>
                                        </td>
                                    </tr>
                                <?php endforeach; ?>
                            <?php endif; ?>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="stats-sidebar">
                <div class="sidebar-title">
                    <span>🟨 Активные карточки</span>
                </div>
                <ul class="penalty-list">
                    <?php if (empty($active_penalties)): ?>
                        <li style="color: #64748b; font-size: 0.875rem;">Нет активных карточек</li>
                    <?php else: ?>
                        <?php foreach ($active_penalties as $p): ?>
                            <li class="penalty-item">
                                <span class="penalty-name"><?= htmlspecialchars(formatName($p)) ?></span>
                                <?php if ($p['expires_at']): ?>
                                    <?php 
                                        $diff = strtotime($p['expires_at']) - time();
                                        $days = max(0, ceil($diff / 86400));
                                    ?>
                                    <span class="penalty-expiry">Истекает через <?= $days ?> дн.</span>
                                <?php endif; ?>
                            </li>
                        <?php endforeach; ?>
                    <?php endif; ?>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>
