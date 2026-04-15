<?php
/**
 * Entry point for Render PHP deployment.
 * Redirects directly to the payments page.
 */
header("Location: payments.php" . ($_SERVER['QUERY_STRING'] ? "?" . $_SERVER['QUERY_STRING'] : ""));
exit;
