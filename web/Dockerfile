# web/Dockerfile
FROM php:8.2-apache

# Install PostgreSQL client and PDO extension (required for Neon)
RUN apt-get update && apt-get install -y libpq-dev \
    && docker-php-ext-install pdo pdo_pgsql

# Copy your web files into the container
# We copy specifically from the 'web' folder since context is project root
COPY web/ /var/www/html/

# Ensure Apache (www-data) owns the files to avoid 403 Forbidden errors
RUN chown -R www-data:www-data /var/www/html

# Ensure Apache can listen on the port Render provides
RUN sed -i 's/80/${PORT}/g' /etc/apache2/sites-available/000-default.conf /etc/apache2/ports.conf

# Start Apache
CMD ["apache2-foreground"]
