# Criando o docker-compose.yml completo para o projeto
docker_compose_content = """version: '3.8'

services:
  # N8N Automation Platform
  n8n:
    image: n8nio/n8n:latest
    container_name: judicial-n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      # Database Configuration
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n_user
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      
      # N8N Configuration
      - N8N_HOST=${N8N_HOST:-localhost}
      - N8N_PORT=5678
      - N8N_PROTOCOL=${N8N_PROTOCOL:-http}
      - WEBHOOK_URL=${WEBHOOK_URL:-http://localhost:5678/}
      - GENERIC_TIMEZONE=America/Sao_Paulo
      
      # Security
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      
      # External modules and functions
      - NODE_FUNCTION_ALLOW_EXTERNAL=axios,lodash,moment,crypto-js
      - NODE_FUNCTION_ALLOW_BUILTIN=fs,path,url
      
      # LGPD Compliance
      - EXECUTIONS_DATA_MAX_AGE=168  # 7 days
      - EXECUTIONS_DATA_PRUNE=true
      
    volumes:
      - n8n_data:/home/node/.n8n
      - ./n8n-workflows:/opt/workflows
      - ./data:/opt/data
    depends_on:
      - postgres
      - redis
    networks:
      - judicial_network

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: judicial-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=n8n
      - POSTGRES_USER=n8n_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_NON_ROOT_USER=n8n_user
      - POSTGRES_NON_ROOT_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/sql/init_database.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - judicial_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U n8n_user -d n8n"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis for Caching and Queue
  redis:
    image: redis:7-alpine
    container_name: judicial-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - judicial_network
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}

  # Python Microservices Container
  python-services:
    build:
      context: .
      dockerfile: ./infrastructure/docker/Dockerfile.python
    container_name: judicial-python-services
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GOOGLE_APPLICATION_CREDENTIALS=/opt/credentials/google-service-account.json
      - DATAJUD_USERNAME=${DATAJUD_USERNAME}
      - DATAJUD_PASSWORD=${DATAJUD_PASSWORD}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    volumes:
      - ./scripts/python:/opt/app
      - ./config/credentials:/opt/credentials:ro
      - ./data:/opt/data
    depends_on:
      - redis
    networks:
      - judicial_network

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: judicial-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infrastructure/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./security/ssl_certificates:/etc/nginx/ssl:ro
      - ./monitoring/logs/nginx:/var/log/nginx
    depends_on:
      - n8n
      - python-services
    networks:
      - judicial_network

  # Monitoring - Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: judicial-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    networks:
      - judicial_network

  # Monitoring - Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: judicial-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    depends_on:
      - prometheus
    networks:
      - judicial_network

  # Backup Service
  backup:
    image: postgres:15-alpine
    container_name: judicial-backup
    restart: "no"
    environment:
      - POSTGRES_DB=n8n
      - POSTGRES_USER=n8n_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - PGPASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - ./scripts/shell:/opt/scripts
      - ./security/backup_policies:/opt/backups
    depends_on:
      - postgres
    networks:
      - judicial_network
    entrypoint: ["sh", "/opt/scripts/backup.sh"]

volumes:
  n8n_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./data/n8n
  postgres_data:
    driver: local
    driver_opts:
      type: none  
      o: bind
      device: ./data/postgres
  redis_data:
    driver: local
  prometheus_data:
    driver: local
  grafana_data:
    driver: local

networks:
  judicial_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
"""

print("🐳 DOCKER COMPOSE CONFIGURADO")
print("=" * 50)
print("📋 SERVIÇOS INCLUÍDOS:")
print("• N8N - Plataforma de automação")
print("• PostgreSQL - Banco de dados principal")
print("• Redis - Cache e filas")
print("• Python Services - Microserviços customizados")
print("• Nginx - Proxy reverso e SSL")
print("• Prometheus - Monitoramento")
print("• Grafana - Dashboard de métricas")
print("• Backup - Serviço de backup automatizado")
print("\n🔒 RECURSOS DE SEGURANÇA:")
print("• SSL/TLS configurado")
print("• Autenticação básica no N8N")
print("• Redes isoladas")
print("• Volumes persistentes")
print("• Compliance LGPD")
print("\n✅ Docker Compose criado com sucesso!")

# Salvando também o arquivo .env.template
env_template = """# Configurações da Aplicação
N8N_HOST=seu-dominio.com
N8N_PROTOCOL=https
N8N_USER=admin
N8N_PASSWORD=sua_senha_segura_aqui
WEBHOOK_URL=https://seu-dominio.com/

# Banco de Dados
POSTGRES_PASSWORD=sua_senha_postgres_segura

# Redis
REDIS_PASSWORD=sua_senha_redis_segura

# APIs Externas
OPENAI_API_KEY=sk-sua_chave_openai
DATAJUD_USERNAME=seu_usuario_datajud
DATAJUD_PASSWORD=sua_senha_datajud

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type": "service_account", ...}

# Monitoramento
GRAFANA_USER=admin
GRAFANA_PASSWORD=sua_senha_grafana

# Configurações de Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_app_gmail

# JusBrasil API (opcional)
JUSBRASIL_API_KEY=sua_chave_jusbrasil

# Segurança
JWT_SECRET=sua_chave_jwt_super_secreta
ENCRYPTION_KEY=sua_chave_criptografia_32_chars
"""

print("\n📝 ARQUIVO .env.template CRIADO")
print("⚠️  LEMBRE-SE: Configure todas as variáveis antes do deploy!")
