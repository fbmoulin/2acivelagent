# Guia Completo de Deploy - Sistema de Automação Jurídica

## 🎯 Opções de Implantação

### 1. Ambiente Local (Desenvolvimento)
- **CPU**: 4 cores
- **RAM**: 8GB mínimo
- **Disco**: 50GB SSD
- **SO**: Ubuntu 20.04+, macOS, Windows 10+

### 2. VPS Cloud (Produção Pequena)
- **CPU**: 4-8 cores
- **RAM**: 16-32GB
- **Disco**: 100GB SSD
- **Banda**: 100Mbps
- **Custo**: R$ 200-500/mês

### 3. Cloud Empresarial (Produção Grande)
- **CPU**: 8-16 cores
- **RAM**: 32-64GB
- **Disco**: 200GB SSD + Backup
- **Banda**: 1Gbps
- **Custo**: R$ 800-2000/mês

## 🏗️ Provedores Recomendados

### VPS Brasil
1. **Hostinger VPS**
   - 4 vCPU, 16GB RAM, 100GB SSD
   - R$ 130/mês
   - Datacenter no Brasil
   
2. **Brasil Cloud**
   - Especializado em N8N
   - Configuração automática
   - R$ 200-400/mês

3. **Digital Ocean**
   - 4 vCPU, 16GB RAM, 100GB SSD
   - US$ 80/mês
   - Região São Paulo

4. **AWS EC2 (Brasil)**
   - t3.xlarge (4 vCPU, 16GB)
   - R$ 400-600/mês
   - Escalabilidade automática

5. **Google Cloud (Brasil)**
   - e2-standard-4 (4 vCPU, 16GB)
   - R$ 350-500/mês
   - Créditos iniciais

### Cloud Especializado
6. **Vultr**
   - High Frequency Compute
   - R$ 250-400/mês
   - Boa performance

7. **Linode**
   - Dedicated CPU
   - R$ 300-500/mês
   - Suporte 24/7

## 🗄️ Opções de Database

### 1. PostgreSQL (Recomendado)
**Prós**: 
- Suporte nativo do N8N
- ACID compliant
- Backup/restore fácil
- Indexação avançada

**Configuração**:
```yaml
postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_DB: n8n
    POSTGRES_USER: n8n_user
    POSTGRES_PASSWORD: senha_forte
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

### 2. MySQL (Alternativa)
**Prós**:
- Amplamente conhecido
- Performance boa
- Replicação fácil

**Limitações**:
- Menos recursos avançados
- JSON handling inferior

### 3. SQLite (Apenas Desenvolvimento)
**Prós**:
- Simples configuração
- Arquivo único

**Limitações**:
- Não recomendado para produção
- Sem concorrência

### 4. Database Gerenciado (Cloud)

**AWS RDS PostgreSQL**:
```yaml
# Configurar via variáveis de ambiente
DB_TYPE: postgresdb
DB_POSTGRESDB_HOST: sua-instancia.rds.amazonaws.com
DB_POSTGRESDB_PORT: 5432
DB_POSTGRESDB_DATABASE: n8n
DB_POSTGRESDB_USER: n8n_user
DB_POSTGRESDB_PASSWORD: sua_senha
```

**Google Cloud SQL**:
- Backup automático
- Alta disponibilidade
- Escalabilidade automática

## 🚀 Procedimento de Deploy

### Passo 1: Preparar Servidor

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Configurar usuário
sudo usermod -aG docker $USER
```

### Passo 2: Configurar Domínio e SSL

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado SSL
sudo certbot certonly --standalone -d seu-dominio.com

# Configurar renovação automática
sudo crontab -e
# Adicionar: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Passo 3: Clonar e Configurar Projeto

```bash
# Clonar repositório
git clone https://github.com/seu-usuario/judicial-automation-system.git
cd judicial-automation-system

# Executar setup
chmod +x scripts/shell/setup.sh
./scripts/shell/setup.sh

# Configurar variáveis
cp .env.template .env
nano .env  # Configurar todas as variáveis
```

### Passo 4: Configurar Nginx (Produção)

```nginx
# /etc/nginx/sites-available/judicial-automation
server {
    listen 80;
    server_name seu-dominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name seu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/seu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.com/privkey.pem;

    # N8N
    location / {
        proxy_pass http://localhost:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # API Python
    location /api/ {
        proxy_pass http://localhost:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Grafana
    location /monitoring/ {
        proxy_pass http://localhost:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Passo 5: Deploy dos Containers

```bash
# Criar network
docker network create judicial_network

# Subir banco primeiro
docker-compose up -d postgres redis

# Aguardar inicialização
sleep 30

# Subir aplicação
docker-compose up -d n8n python-services

# Aguardar estabilização
sleep 60

# Subir monitoramento
docker-compose up -d prometheus grafana

# Verificar status
docker-compose ps
```

### Passo 6: Configurar Monitoramento

```bash
# Configurar Grafana
# Acesse: https://seu-dominio.com/monitoring
# Login: admin / sua_senha_grafana

# Importar dashboards
# ID 1860 - Node Exporter Full
# ID 3662 - PostgreSQL Database
# ID 7362 - Docker and system monitoring
```

### Passo 7: Configurar Backup

```bash
# Configurar backup automático
sudo crontab -e

# Adicionar linha:
0 2 * * * cd /home/user/judicial-automation-system && docker-compose run --rm backup

# Configurar backup para cloud (AWS S3)
aws configure  # Configurar credenciais AWS
# Editar backup.sh para incluir upload S3
```

## 🔧 APIs e Integrações

### APIs de IA Recomendadas

1. **OpenAI GPT-4** (Principal)
   - Preço: US$ 0.03/1K tokens
   - Limite: 10K RPM
   - Qualidade superior
   
2. **Claude 3.5 (Anthropic)**
   - Preço: US$ 0.025/1K tokens
   - Boa para análise jurídica
   - Alternativa ao OpenAI

3. **Gemini Pro (Google)**
   - Preço: US$ 0.002/1K tokens
   - Integração fácil
   - Custo-benefício

4. **Cohere Command**
   - Preço: US$ 0.015/1K tokens
   - Especializado em texto
   - Alternativa interessante

### APIs de OCR

1. **Google Document AI**
   - Melhor para documentos jurídicos
   - R$ 0.50 por página
   - Precisão alta

2. **Azure Form Recognizer**
   - Boa precisão
   - R$ 0.40 por página
   - Integração Microsoft

3. **AWS Textract**
   - Preço variável
   - Boa para tabelas
   - Infraestrutura robusta

4. **OCR.space (Gratuito)**
   - 25.000 requisições/mês grátis
   - Qualidade inferior
   - Para testes

### APIs Jurídicas Brasileiras

1. **DATAJUD (CNJ)** - Gratuito
   - API oficial do CNJ
   - Todos os tribunais
   - Obrigatório cadastro

2. **JusBrasil API**
   - Pago por consulta
   - Interface amigável
   - Dados estruturados

3. **API Consulta CNJ**
   - Gratuito
   - Limitações de rate
   - Básico mas funcional

## 🔒 Configurações de Segurança

### Firewall (UFW)

```bash
# Configurar firewall
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 5678/tcp   # N8N (apenas via proxy)
sudo ufw deny 5000/tcp   # API Python (apenas via proxy)
sudo ufw deny 5432/tcp   # PostgreSQL (apenas interno)
```

### Fail2ban

```bash
# Instalar fail2ban
sudo apt install fail2ban

# Configurar
sudo nano /etc/fail2ban/jail.local

[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
```

### Backup e Disaster Recovery

```bash
# Script de backup completo
#!/bin/bash
BACKUP_DIR="/opt/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup banco
docker-compose exec -T postgres pg_dump -U n8n_user n8n > $BACKUP_DIR/database.sql

# Backup workflows
curl -u $N8N_USER:$N8N_PASSWORD http://localhost:5678/api/v1/workflows > $BACKUP_DIR/workflows.json

# Backup configurações
tar -czf $BACKUP_DIR/configs.tar.gz ./config ./data

# Upload para S3
aws s3 cp $BACKUP_DIR s3://seu-bucket/backups/ --recursive

# Limpeza local (manter 7 dias)
find /opt/backups -type d -mtime +7 -exec rm -rf {} \;
```

## 📊 Estimativas de Custo

### Cenário Pequeno (1-10 usuários)
- **VPS**: R$ 200/mês
- **Domínio**: R$ 40/ano
- **OpenAI**: R$ 100/mês
- **Google APIs**: R$ 50/mês
- **Total**: ~R$ 350/mês

### Cenário Médio (10-50 usuários)
- **VPS**: R$ 500/mês
- **Database gerenciado**: R$ 300/mês
- **APIs**: R$ 300/mês
- **Monitoramento**: R$ 100/mês
- **Total**: ~R$ 1.200/mês

### Cenário Grande (50+ usuários)
- **Cloud premium**: R$ 1.500/mês
- **Database HA**: R$ 800/mês
- **APIs**: R$ 800/mês
- **CDN/Backup**: R$ 200/mês
- **Total**: ~R$ 3.300/mês

## ✅ Checklist Final de Deploy

### Pré-Deploy
- [ ] Servidor configurado
- [ ] Domínio apontado
- [ ] SSL configurado
- [ ] Variáveis de ambiente definidas
- [ ] Credenciais APIs obtidas

### Deploy
- [ ] Código clonado
- [ ] Docker instalado
- [ ] Containers iniciados
- [ ] Health checks passando
- [ ] Nginx configurado

### Pós-Deploy
- [ ] N8N acessível
- [ ] Workflows importados
- [ ] Credenciais configuradas
- [ ] Testes end-to-end
- [ ] Monitoramento ativo
- [ ] Backup funcionando
- [ ] Documentação atualizada

### Produção
- [ ] Firewall configurado
- [ ] Fail2ban ativo
- [ ] Logs centralizados
- [ ] Alertas configurados
- [ ] Equipe treinada
- [ ] Runbook documentado

---

## 🆘 Suporte e Manutenção

### Monitoramento 24/7
- Grafana dashboards
- Alertas email/SMS
- Health checks automáticos
- Log analysis

### Manutenção Preventiva
- Updates mensais
- Backup testing
- Performance tuning
- Security patches

### Plano de Contingência
- Rollback procedures
- Disaster recovery
- Backup restoration
- Emergency contacts

**🎉 Sistema pronto para produção!**