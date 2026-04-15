# web/Dockerfile
FROM php:8.2-apache

# Install PostgreSQL client and PDO extension (required for Neon)
RUN apt-get update && apt-get install -y libpq-dev \
    && docker-php-ext-install pdo pdo_pgsql

# Copy your web files into the container
# Since the Docker Context will be '.', we copy from the current dir (web/)
COPY . /var/www/html/

# Ensure Apache can listen on the port Render provides
RUN sed -i 's/80/${PORT}/g' /etc/apache2/sites-available/000-default.conf /etc/apache2/ports.conf

# Start Apache
CMD ["apache2-foreground"]
