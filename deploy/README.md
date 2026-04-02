# Deploy VPS - SGPS

Stack alvo: Nginx + Gunicorn + systemd + PostgreSQL em Ubuntu/Debian.

- Dominio: `sgps.sistema9.com.br`
- Diretorio sugerido: `/var/www/sgps`
- Servico systemd: `sgps-gunicorn`
- Porta interna do Gunicorn: `127.0.0.1:8071`
- Banco PostgreSQL sugerido: `sgps`
- Usuario PostgreSQL sugerido: `sgps`

## 1. Preparar o servidor

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx certbot python3-certbot-nginx \
    git curl
```

## 2. Criar o usuario do sistema e diretorio da app

```bash
sudo adduser --system --group --home /var/www/sgps sgps
sudo mkdir -p /var/www/sgps
sudo chown -R sgps:sgps /var/www/sgps
```

## 3. Criar banco e usuario no PostgreSQL

Troque a senha abaixo antes de rodar.

```bash
sudo -u postgres psql <<SQL
CREATE DATABASE sgps;
CREATE USER sgps WITH PASSWORD 'troque-por-uma-senha-forte';
ALTER ROLE sgps SET client_encoding TO 'utf8';
ALTER ROLE sgps SET default_transaction_isolation TO 'read committed';
ALTER ROLE sgps SET timezone TO 'America/Sao_Paulo';
GRANT ALL PRIVILEGES ON DATABASE sgps TO sgps;
\c sgps
GRANT ALL ON SCHEMA public TO sgps;
ALTER SCHEMA public OWNER TO sgps;
SQL
```

## 4. Subir o codigo da aplicacao

Se o repositorio ainda nao estiver na VPS:

```bash
sudo -u sgps git clone <URL_DO_REPOSITORIO> /var/www/sgps
```

Se ele ja estiver la, apenas entre no diretorio:

```bash
cd /var/www/sgps
```

## 5. Criar virtualenv e instalar dependencias

```bash
cd /var/www/sgps
sudo -u sgps python3 -m venv .venv
sudo -u sgps /var/www/sgps/.venv/bin/pip install --upgrade pip
sudo -u sgps /var/www/sgps/.venv/bin/pip install -r requirements-prod.txt
```

## 6. Configurar o .env

```bash
cd /var/www/sgps
sudo -u sgps cp deploy/env/projeto.env.example .env
sudo -u sgps nano .env
```

Ajustes minimos:

- `DJANGO_SECRET_KEY`
- `DB_PASSWORD`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

Gerar a `DJANGO_SECRET_KEY`:

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 7. Rodar migracoes e coletar estaticos

```bash
cd /var/www/sgps
sudo -u sgps /var/www/sgps/.venv/bin/python manage.py migrate
sudo -u sgps /var/www/sgps/.venv/bin/python manage.py collectstatic --noinput
sudo -u sgps /var/www/sgps/.venv/bin/python manage.py createsuperuser
```

## 8. Confirmar a porta 8071

```bash
sudo ss -ltnp | grep 8071
```

Se ja existir algo escutando na `8071`, troque a porta nos dois arquivos:

- `deploy/systemd/projeto.service`
- `deploy/nginx/dominio.conf`

## 9. Instalar o servico Gunicorn

```bash
sudo cp deploy/systemd/projeto.service /etc/systemd/system/sgps-gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable --now sgps-gunicorn
sudo systemctl status sgps-gunicorn
```

## 10. Configurar o Nginx

```bash
sudo cp deploy/nginx/dominio.conf /etc/nginx/sites-available/sgps.sistema9.com.br.conf
sudo ln -s /etc/nginx/sites-available/sgps.sistema9.com.br.conf /etc/nginx/sites-enabled/sgps.sistema9.com.br.conf
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

## 11. Configurar SSL

```bash
sudo certbot --nginx -d sgps.sistema9.com.br
```

## 12. Verificar tudo

```bash
sudo systemctl status sgps-gunicorn
sudo systemctl status nginx
sudo systemctl status postgresql
curl -I https://sgps.sistema9.com.br
```

## Atualizacao de codigo

```bash
cd /var/www/sgps
sudo -u sgps git pull
sudo -u sgps /var/www/sgps/.venv/bin/pip install -r requirements-prod.txt
sudo -u sgps /var/www/sgps/.venv/bin/python manage.py migrate
sudo -u sgps /var/www/sgps/.venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart sgps-gunicorn
```

## Logs uteis

```bash
sudo journalctl -u sgps-gunicorn -f
sudo tail -f /var/log/nginx/error.log
```

## Backup do banco

```bash
sudo -u postgres pg_dump sgps > backup_sgps_$(date +%Y%m%d).sql
```
