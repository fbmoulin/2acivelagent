# Criando script de setup completo
setup_script = '''#!/bin/bash
# Setup Script para Sistema de Automação Jurídica
# Autor: Sistema de IA Jurídica
# Data: 2025-06-30

set -e  # Parar em qualquer erro

echo "🚀 INICIANDO SETUP DO SISTEMA DE AUTOMAÇÃO JURÍDICA"
echo "=================================================="

# Cores para output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

# Função para logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se está rodando como root
if [[ $EUID -eq 0 ]]; then
   log_error "Este script não deve ser executado como root"
   exit 1
fi

# Verificar dependências
check_dependencies() {
    log_info "Verificando dependências..."
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker não está instalado. Instale o Docker primeiro."
        exit 1
    fi
    
    # Verificar Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose não está instalado. Instale o Docker Compose primeiro."
        exit 1
    fi
    
    # Verificar Git
    if ! command -v git &> /dev/null; then
        log_error "Git não está instalado. Instale o Git primeiro."
        exit 1
    fi
    
    log_success "Todas as dependências estão instaladas"
}

# Criar estrutura de diretórios
create_directories() {
    log_info "Criando estrutura de diretórios..."
    
    # Diretórios principais
    mkdir -p docs
    mkdir -p infrastructure/{docker,terraform,nginx}
    mkdir -p n8n-workflows/{templates,credentials,exports}
    mkdir -p scripts/{python,shell,sql}
    mkdir -p config/{n8n,database,security}
    mkdir -p data/{templates/{legal_documents,email_templates,report_templates},samples,exports,n8n,postgres}
    mkdir -p monitoring/{prometheus,grafana,logs/{nginx,n8n,python}}
    mkdir -p security/{ssl_certificates,backup_policies}
    mkdir -p tests/{unit,integration,e2e}
    
    log_success "Estrutura de diretórios criada"
}

# Configurar arquivo .env
setup_environment() {
    log_info "Configurando arquivo de ambiente..."
    
    if [ ! -f .env ]; then
        cp config/n8n/.env.template .env
        log_warning "Arquivo .env criado a partir do template"
        log_warning "IMPORTANTE: Configure as variáveis de ambiente em .env antes de continuar"
    else
        log_info "Arquivo .env já existe"
    fi
}

# Configurar permissões
setup_permissions() {
    log_info "Configurando permissões..."
    
    # Permissões para dados
    chmod -R 755 data/
    chmod -R 755 monitoring/logs/
    
    # Permissões para scripts
    chmod +x scripts/shell/*.sh
    
    # Permissões para certificados SSL
    if [ -d security/ssl_certificates ]; then
        chmod 600 security/ssl_certificates/*
    fi
    
    log_success "Permissões configuradas"
}

# Configurar Docker
setup_docker() {
    log_info "Configurando Docker..."
    
    # Verificar se o usuário está no grupo docker
    if ! groups $USER | grep &>/dev/null '\\bdocker\\b'; then
        log_warning "Usuário não está no grupo docker. Adicionando..."
        sudo usermod -aG docker $USER
        log_warning "Faça logout e login novamente para que as alterações tenham efeito"
    fi
    
    # Criar network se não existir
    if ! docker network ls | grep judicial_network &>/dev/null; then
        docker network create judicial_network
        log_success "Network Docker criada"
    fi
    
    log_success "Docker configurado"
}

# Configurar SSL (Let's Encrypt)
setup_ssl() {
    log_info "Configurando SSL..."
    
    read -p "Deseja configurar SSL com Let's Encrypt? (y/n): " setup_ssl
    
    if [[ $setup_ssl == "y" || $setup_ssl == "Y" ]]; then
        read -p "Digite seu domínio (ex: meusite.com): " domain
        
        if [ ! -z "$domain" ]; then
            # Instalar certbot se não estiver instalado
            if ! command -v certbot &> /dev/null; then
                log_info "Instalando certbot..."
                sudo apt-get update
                sudo apt-get install -y certbot python3-certbot-nginx
            fi
            
            # Gerar certificado
            sudo certbot certonly --standalone -d $domain
            
            # Copiar certificados para o projeto
            sudo cp /etc/letsencrypt/live/$domain/fullchain.pem security/ssl_certificates/
            sudo cp /etc/letsencrypt/live/$domain/privkey.pem security/ssl_certificates/
            sudo chown $USER:$USER security/ssl_certificates/*
            
            log_success "SSL configurado para $domain"
        fi
    fi
}

# Inicializar banco de dados
init_database() {
    log_info "Inicializando banco de dados..."
    
    # Subir apenas o PostgreSQL primeiro
    docker-compose up -d postgres
    
    # Aguardar PostgreSQL ficar pronto
    log_info "Aguardando PostgreSQL ficar pronto..."
    sleep 10
    
    # Executar scripts de inicialização
    if [ -f scripts/sql/init_database.sql ]; then
        docker-compose exec postgres psql -U n8n_user -d n8n -f /docker-entrypoint-initdb.d/init.sql
        log_success "Scripts de inicialização executados"
    fi
}

# Configurar monitoramento
setup_monitoring() {
    log_info "Configurando monitoramento..."
    
    # Criar configuração do Prometheus
    cat > monitoring/prometheus/prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'n8n'
    static_configs:
      - targets: ['n8n:5678']
  
  - job_name: 'python-services'
    static_configs:
      - targets: ['python-services:5000']
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
EOF
    
    log_success "Monitoramento configurado"
}

# Fazer backup da configuração
backup_config() {
    log_info "Criando backup da configuração..."
    
    backup_dir="backups/config_$(date +%Y%m%d_%H%M%S)"
    mkdir -p $backup_dir
    
    cp -r config/ $backup_dir/
    cp .env $backup_dir/ 2>/dev/null || true
    cp docker-compose.yml $backup_dir/
    
    log_success "Backup criado em $backup_dir"
}

# Testar instalação
test_installation() {
    log_info "Testando instalação..."
    
    # Subir todos os serviços
    docker-compose up -d
    
    # Aguardar serviços ficarem prontos
    sleep 30
    
    # Testar API Python
    if curl -f http://localhost:5000/health &>/dev/null; then
        log_success "API Python está funcionando"
    else
        log_error "API Python não está respondendo"
    fi
    
    # Testar N8N
    if curl -f http://localhost:5678 &>/dev/null; then
        log_success "N8N está funcionando"
    else
        log_error "N8N não está respondendo"
    fi
    
    log_info "Verificando logs..."
    docker-compose logs --tail=10
}

# Função principal
main() {
    log_info "Iniciando setup do Sistema de Automação Jurídica..."
    
    check_dependencies
    create_directories
    setup_environment
    setup_permissions
    setup_docker
    setup_ssl
    setup_monitoring
    backup_config
    init_database
    test_installation
    
    echo ""
    log_success "Setup concluído com sucesso!"
    echo ""
    echo "📋 PRÓXIMOS PASSOS:"
    echo "1. Configure as variáveis no arquivo .env"
    echo "2. Execute: docker-compose up -d"
    echo "3. Acesse N8N em: http://localhost:5678"
    echo "4. Configure suas credenciais APIs"
    echo "5. Importe os workflows do diretório n8n-workflows/templates/"
    echo ""
    echo "📚 DOCUMENTAÇÃO: docs/README.md"
    echo "🔧 MONITORAMENTO: http://localhost:3000 (Grafana)"
    echo "📊 MÉTRICAS: http://localhost:9090 (Prometheus)"
    echo ""
    log_warning "IMPORTANTE: Configure SSL e firewall antes de usar em produção!"
}

# Executar função principal
main "$@"
'''

# Script de backup
backup_script = '''#!/bin/bash
# Script de Backup Automatizado
# Sistema de Automação Jurídica

set -e

# Configurações
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Cores
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
RED='\\033[0;31m'
NC='\\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Criar diretório de backup
mkdir -p $BACKUP_DIR

# Backup do PostgreSQL
backup_database() {
    log "Iniciando backup do banco de dados..."
    
    PGPASSWORD=$POSTGRES_PASSWORD pg_dump \\
        -h postgres \\
        -U n8n_user \\
        -d n8n \\
        --no-password \\
        --verbose \\
        --format=custom \\
        --compress=9 \\
        > $BACKUP_DIR/database_$DATE.dump
    
    log "Backup do banco concluído: database_$DATE.dump"
}

# Backup dos workflows N8N
backup_workflows() {
    log "Iniciando backup dos workflows..."
    
    # Exportar workflows via API N8N
    curl -u $N8N_USER:$N8N_PASSWORD \\
        -X GET \\
        "http://n8n:5678/api/v1/workflows" \\
        -H "accept: application/json" \\
        > $BACKUP_DIR/workflows_$DATE.json
    
    log "Backup dos workflows concluído"
}

# Backup dos arquivos de configuração
backup_configs() {
    log "Iniciando backup das configurações..."
    
    tar -czf $BACKUP_DIR/configs_$DATE.tar.gz \\
        /opt/data/n8n \\
        /opt/config \\
        /opt/security 2>/dev/null || true
    
    log "Backup das configurações concluído"
}

# Backup dos dados de monitoramento
backup_monitoring() {
    log "Iniciando backup do monitoramento..."
    
    tar -czf $BACKUP_DIR/monitoring_$DATE.tar.gz \\
        /opt/monitoring/grafana \\
        /opt/monitoring/logs 2>/dev/null || true
    
    log "Backup do monitoramento concluído"
}

# Limpeza de backups antigos
cleanup_old_backups() {
    log "Limpando backups antigos (>$RETENTION_DAYS dias)..."
    
    find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete
    
    log "Limpeza concluída"
}

# Upload para cloud (opcional)
upload_to_cloud() {
    if [ ! -z "$AWS_S3_BUCKET" ]; then
        log "Enviando backup para S3..."
        
        aws s3 cp $BACKUP_DIR/ s3://$AWS_S3_BUCKET/backups/ --recursive
        
        log "Upload para S3 concluído"
    fi
}

# Função principal
main() {
    log "Iniciando backup automatizado..."
    
    backup_database
    backup_workflows
    backup_configs
    backup_monitoring
    cleanup_old_backups
    upload_to_cloud
    
    log "Backup automatizado concluído com sucesso!"
    
    # Estatísticas
    echo ""
    echo "📊 ESTATÍSTICAS DO BACKUP:"
    echo "📁 Diretório: $BACKUP_DIR"
    echo "📅 Data: $DATE"
    echo "💾 Arquivos criados:"
    ls -lh $BACKUP_DIR/*$DATE*
}

# Executar
main "$@"
'''

print("📜 SCRIPTS DE CONFIGURAÇÃO CRIADOS")
print("=" * 50)
print("🔧 SETUP.SH - Script de instalação completa")
print("• Verifica dependências")
print("• Cria estrutura de diretórios")
print("• Configura Docker e SSL")
print("• Inicializa banco de dados")
print("• Configura monitoramento")
print("• Testa instalação")
print("")
print("💾 BACKUP.SH - Script de backup automatizado")
print("• Backup PostgreSQL")
print("• Backup workflows N8N")
print("• Backup configurações")
print("• Limpeza automática")
print("• Upload para cloud (opcional)")
print("")
print("✅ Scripts prontos para uso!")
print("📋 Para executar: chmod +x scripts/shell/setup.sh && ./scripts/shell/setup.sh")