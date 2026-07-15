# Docker Local Demo - Mayz Monitoring

Konsep Docker Local Demo Mode untuk development dan testing tanpa VPS.

## Arsitektur

```
┌─────────────────────────────────────────┐
│            Laptop Windows                │
│                                         │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │Backend │ │Frontend │ │  Worker  │  │
│  │  :8000 │ │  :8080  │ │  loop    │  │
│  └────┬───┘ └────┬────┘ └────┬─────┘  │
│       └──────────┴───────────┘         │
│              │                         │
│         Docker Network                 │
│              │                         │
│    host.docker.internal:3306           │
│              │                         │
│  ┌──────────┴──────────┐             │
│  │    XAMPP MySQL      │             │
│  │   (Database Lokal)  │             │
│  └─────────────────────┘             │
└─────────────────────────────────────┘
```

## Prasyarat

- Docker Desktop running
- XAMPP MySQL running
- Port 8080, 8000 available

## Setup

### 1. Copy Env Template

```bash
copy deployment\docker-local\deployment/docker-local/.env.docker.local.example deployment\docker-local\deployment/docker-local/.env.docker.local
```

### 2. Edit deployment/docker-local/.env.docker.local

Isi value untuk credential XAMPP MySQL.

### 3. XAMPP MySQL Config

Pastikan MySQL XAMPP bisa diakses dari container.

Edit `xampp/mysql/bin/my.ini`:
```ini
[mysqld]
bind-address=0.0.0.0
```

Restart MySQL dari XAMPP Control Panel.

## Build & Run

### Build Semua Service

```bash
docker compose -f deployment/docker-local/docker-compose.yml --env-file deployment/docker-local/.env.docker.local build
```

### Up Backend

```bash
docker compose -f deployment/docker-local/docker-compose.yml --env-file deployment/docker-local/.env.docker.local up -d backend
```

Cek health:
```bash
curl http://localhost:8000/health
```

### Up Frontend

```bash
docker compose -f deployment/docker-local/docker-compose.yml --env-file deployment/docker-local/.env.docker.local up -d frontend
```

### Up Worker

```bash
docker compose -f deployment/docker-local/docker-compose.yml --env-file deployment/docker-local/.env.docker.local up -d worker
```

## Monitoring

### Cek Worker Logs

```bash
docker compose -f deployment/docker-local/docker-compose.yml --env-file deployment/docker-local/.env.docker.local logs -f worker
```

### Cek Backend Logs

```bash
docker compose -f deployment/docker-local/docker-compose.yml --env-file deployment/docker-local/.env.docker.local logs backend
```

### Cek Semua Logs

```bash
docker compose -f deployment/docker-local/docker-compose.yml --env-file deployment/docker-local/.env.docker.local logs -f
```

## Akses

- Dashboard: http://localhost:8080
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Stop

```bash
docker compose -f deployment/docker-local/docker-compose.yml --env-file deployment/docker-local/.env.docker.local down
```

## Troubleshooting

### host.docker.internal Not Working

Jika container tidak bisa connect ke MySQL XAMPP:

1. Cek MySQL XAMPP running
2. Cek bind-address=0.0.0.0
3. Cek firewall
4. Alternative: buat user MySQL khusus

```sql
CREATE USER 'docker'@'%' IDENTIFIED BY 'password';
GRANT ALL ON mayz_monitoring.* TO 'docker'@'%';
FLUSH PRIVILEGES;
```

### Port Conflict

Port 8080 used:
```bash
netstat -ano | findstr :8080
```

Port 8000 used:
```bash
netstat -ano | findstr :8000
```

Stop service yang pakai port tersebut.

### Worker Idle

Worker normal idle jika tidak ada job:
```
[INFO] No queued job. Worker idle.
```

Worker pickup job jika job dibuat dari dashboard.

## Batasan

### Hanya 1 Worker

Tidak boleh running 2 worker container. Job akan duplicate.

### Laptop Mati = Sistem Mati

Worker tidak jalan jika laptop sleep/shutdown. Tidak ada auto-restart di local mode.

### Data Persistent

- Logs: `logs/worker.log` (di-mount)
- Staging: `data/staging/` (di-mount)
- Database: XAMPP MySQL lokal

## Production

Untuk production, pertimbangkan:
- VPS dengan Docker Compose
- MariaDB container
- Auto-restart via systemd
- Backup rutin
