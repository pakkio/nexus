# Deployment Guide

## Production Deployment

### Server Requirements

- **Python**: 3.8 or higher
- **Memory**: Minimum 2GB RAM, recommended 4GB+
- **Storage**: 10GB+ for databases and logs
- **Network**: Stable internet connection for OpenRouter API

### Environment Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   # or using Poetry
   poetry install
   ```

2. **Environment Configuration**
   Create `.env` file:
   ```bash
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   OPENROUTER_DEFAULT_MODEL=google/gemma-2-9b-it:free
   PROFILE_ANALYSIS_MODEL=mistralai/mistral-7b-instruct:free
   
   # Optional: Database configuration
   MYSQL_HOST=localhost
   MYSQL_USER=nexus_user
   MYSQL_PASSWORD=secure_password
   MYSQL_DATABASE=nexus_eldoria
   ```

3. **Database Setup (Optional)**
   ```bash
   # For MySQL (recommended for production)
   mysql -u root -p
   CREATE DATABASE nexus_eldoria;
   CREATE USER 'nexus_user'@'localhost' IDENTIFIED BY 'secure_password';
   GRANT ALL PRIVILEGES ON nexus_eldoria.* TO 'nexus_user'@'localhost';
   
   # For file-based (development)
   # No setup required - uses automatic mockup system
   ```

### Production Server

1. **Start Server**
   ```bash
   # Development
   python app.py
   
   # Production with Gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   
   # With process manager
   pm2 start ecosystem.config.js
   ```

2. **Reverse Proxy (Nginx)**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **SSL Certificate (Let's Encrypt)**
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

### Second Life/OpenSim Deployment

1. **LSL Script Configuration**
   ```lsl
   string NEXUS_SERVER_URL = "https://your-domain.com";
   string NPC_NAME = "mara";  // or your NPC
   string AREA_NAME = "Village";  // or your area
   ```

2. **Security Considerations**
   - Use HTTPS in production
   - Implement rate limiting
   - Configure CORS appropriately
   - Monitor API usage

### Monitoring

1. **Health Checks**
   ```bash
   # Basic health check
   curl http://localhost:5000/health
   
   # Performance monitoring
   curl http://localhost:5000/api/stats
   ```

2. **Log Management**
   ```bash
   # Server logs
   tail -f nexus_server.log
   
   # Error tracking
   grep ERROR nexus_server.log | tail -20
   ```

3. **Performance Metrics**
   - Response time monitoring
   - Memory usage tracking
   - Database connection health
   - OpenRouter API quota usage

## Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  nexus:
    build: .
    ports:
      - "5000:5000"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    volumes:
      - ./database:/app/database
      - ./logs:/app/logs
    restart: unless-stopped
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    depends_on:
      - nexus
```

### Deployment Commands
```bash
# Build and start
docker-compose up -d

# Scale application
docker-compose up -d --scale nexus=3

# View logs
docker-compose logs -f nexus

# Update deployment
docker-compose pull && docker-compose up -d
```

## Scaling

### Horizontal Scaling

1. **Load Balancer Configuration**
   ```nginx
   upstream nexus_backend {
       server 127.0.0.1:5000;
       server 127.0.0.1:5001;
       server 127.0.0.1:5002;
   }
   
   server {
       location / {
           proxy_pass http://nexus_backend;
       }
   }
   ```

2. **Session Persistence**
   - Use shared database for game states
   - Implement Redis for session caching
   - Configure sticky sessions if needed

### Database Scaling

1. **MySQL Optimization**
   ```sql
   -- Index optimization
   CREATE INDEX idx_player_conversations 
   ON conversations(player_id, npc_code);
   
   CREATE INDEX idx_player_profiles 
   ON player_profiles(player_id);
   ```

2. **Connection Pooling**
   ```python
   # In production configuration
   MYSQL_POOL_SIZE = 20
   MYSQL_MAX_OVERFLOW = 30
   MYSQL_POOL_TIMEOUT = 30
   ```

## Security

### API Security

1. **Rate Limiting**
   ```python
   from flask_limiter import Limiter
   
   limiter = Limiter(
       app,
       key_func=get_remote_address,
       default_limits=["100 per hour"]
   )
   
   @app.route('/api/chat')
   @limiter.limit("10 per minute")
   def chat_endpoint():
       # ... implementation
   ```

2. **Input Validation**
   ```python
   # Validate all user inputs
   def validate_player_name(name):
       if not name or len(name) > 50:
           raise ValueError("Invalid player name")
       return name.strip()
   ```

3. **CORS Configuration**
   ```python
   CORS(app, origins=[
       "https://your-sl-region.com",
       "https://your-opensim-grid.com"
   ])
   ```

### Infrastructure Security

1. **Firewall Rules**
   ```bash
   # Allow only necessary ports
   ufw allow 22/tcp      # SSH
   ufw allow 80/tcp      # HTTP
   ufw allow 443/tcp     # HTTPS
   ufw deny 5000/tcp     # Block direct API access
   ```

2. **SSL/TLS Configuration**
   ```nginx
   ssl_protocols TLSv1.2 TLSv1.3;
   ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
   ssl_prefer_server_ciphers off;
   add_header Strict-Transport-Security "max-age=63072000" always;
   ```

## Backup and Recovery

### Database Backup
```bash
# MySQL backup
mysqldump -u nexus_user -p nexus_eldoria > backup_$(date +%Y%m%d).sql

# File-based backup
tar -czf database_backup_$(date +%Y%m%d).tar.gz database/
```

### Automated Backups
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/nexus"

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
mysqldump -u nexus_user -p$MYSQL_PASSWORD nexus_eldoria > $BACKUP_DIR/db_$DATE.sql

# File backup
tar -czf $BACKUP_DIR/files_$DATE.tar.gz database/ logs/

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### Crontab Entry
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Monitor conversation history cleanup
   - Implement periodic cache clearing
   - Check for memory leaks in LLM processing

2. **Slow Response Times**
   - Monitor OpenRouter API latency
   - Optimize database queries
   - Implement response caching

3. **Database Connection Issues**
   - Check connection pool settings
   - Verify MySQL configuration
   - Monitor connection limits

### Log Analysis
```bash
# Error patterns
grep -E "(ERROR|CRITICAL)" logs/nexus.log

# Performance analysis
grep "Response time" logs/nexus.log | awk '{print $NF}' | sort -n

# Most active players
grep "chat completed" logs/nexus.log | grep -o "player_name:[^,]*" | sort | uniq -c | sort -nr
```

### Health Monitoring
```bash
#!/bin/bash
# health_check.sh
HEALTH_URL="http://localhost:5000/health"
RESPONSE=$(curl -s -w "%{http_code}" $HEALTH_URL)

if [ "$RESPONSE" != "200" ]; then
    echo "Health check failed: $RESPONSE"
    # Alert or restart service
    systemctl restart nexus
fi
```

## Performance Optimization

### Application Level

1. **Caching Strategies**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def get_npc_data(area, npc_name):
       # Cache NPC data
       return load_npc_from_file(area, npc_name)
   ```

2. **Database Optimization**
   ```python
   # Connection pooling
   engine = create_engine(
       database_url,
       pool_size=20,
       max_overflow=30,
       pool_timeout=30
   )
   ```

3. **Async Processing**
   ```python
   # Background profile analysis
   import asyncio
   
   async def update_player_profile(player_data):
       # Non-blocking profile update
       pass
   ```

### Server Level

1. **Gunicorn Configuration**
   ```python
   # gunicorn.conf.py
   bind = "0.0.0.0:5000"
   workers = 4
   worker_class = "sync"
   worker_connections = 1000
   max_requests = 1000
   max_requests_jitter = 100
   timeout = 30
   keepalive = 5
   ```

2. **System Optimization**
   ```bash
   # Increase file descriptor limits
   echo "* soft nofile 65536" >> /etc/security/limits.conf
   echo "* hard nofile 65536" >> /etc/security/limits.conf
   
   # Optimize TCP settings
   echo "net.core.somaxconn = 65536" >> /etc/sysctl.conf
   echo "net.ipv4.tcp_max_syn_backlog = 65536" >> /etc/sysctl.conf
   ```

## Maintenance

### Regular Tasks

1. **Database Cleanup**
   ```sql
   -- Remove old conversation history (older than 90 days)
   DELETE FROM conversations 
   WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
   
   -- Optimize tables
   OPTIMIZE TABLE conversations, player_profiles;
   ```

2. **Log Rotation**
   ```bash
   # logrotate configuration
   /var/log/nexus/*.log {
       daily
       missingok
       rotate 30
       compress
       notifempty
       create 644 www-data www-data
       postrotate
           systemctl reload nexus
       endscript
   }
   ```

3. **System Updates**
   ```bash
   # Update dependencies
   pip install -r requirements.txt --upgrade
   
   # Security updates
   apt update && apt upgrade -y
   
   # Restart services
   systemctl restart nexus nginx
   ```

### Monitoring Alerts

1. **Service Monitoring**
   ```bash
   # Check if service is running
   systemctl is-active nexus
   
   # Check port availability
   netstat -tlnp | grep :5000
   ```

2. **Resource Monitoring**
   ```bash
   # CPU and Memory usage
   top -p $(pgrep -f "gunicorn.*app:app")
   
   # Disk usage
   df -h
   du -sh database/ logs/
   ```

This deployment guide provides comprehensive instructions for production deployment, scaling, security, and maintenance of the Nexus/Eldoria RPG system.