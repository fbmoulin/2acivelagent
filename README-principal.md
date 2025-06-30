# Sistema de Automação Jurídica

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![LGPD](https://img.shields.io/badge/LGPD-compliant-green.svg)

Um sistema completo de automação para processos judiciais brasileiros, integrando n8n, inteligência artificial e APIs jurídicas nacionais.

## 🎯 Visão Geral

Este sistema automatiza todo o fluxo de análise processual judicial, desde a recepção de documentos PDF até a geração de minutas e decisões. Utiliza metodologia FIRAC, pesquisa jurisprudencial automática e análise de distinguish para garantir fundamentação jurídica sólida.

### ✨ Funcionalidades Principais

- **📄 Extração Automática de PDF**: Processamento de documentos judiciais
- **🧠 Análise FIRAC**: Estruturação automática de fatos, questões, regras, análise e conclusão
- **⚖️ Pesquisa Jurisprudencial**: Integração com API DATAJUD do CNJ
- **🔍 Análise de Distinguish**: Comparação automática entre precedentes e fatos
- **📝 Geração de Minutas**: Criação automática de sentenças e despachos
- **☁️ Integração Google**: Drive, Docs e Sheets para gestão de documentos
- **📊 Dashboard de Monitoramento**: Métricas e acompanhamento em tempo real
- **🔒 Compliance LGPD**: Proteção de dados pessoais e sigilosos

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Google Drive  │────│     N8N         │────│  Python APIs   │
│   (Documentos)  │    │  (Orquestração) │    │ (Processamento) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │    │   APIs Externas│
│  (Persistência) │    │    (Cache)      │    │ OpenAI/DATAJUD  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 🔧 Stack Tecnológico

- **Orquestração**: N8N (Workflow automation)
- **Backend**: Python Flask + PostgreSQL + Redis
- **IA**: OpenAI GPT-4, Google Document AI
- **APIs Legais**: DATAJUD (CNJ), JusBrasil
- **Armazenamento**: Google Drive, Google Docs, Google Sheets
- **Deployment**: Docker Compose
- **Monitoramento**: Prometheus + Grafana
- **Proxy**: Nginx com SSL

## 🚀 Instalação Rápida

### Pré-requisitos

- Docker e Docker Compose
- Git
- Domínio próprio (para SSL em produção)
- Contas nas APIs: OpenAI, Google Cloud, DATAJUD

### 1. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/judicial-automation-system.git
cd judicial-automation-system
```

### 2. Execute o Setup Automático

```bash
chmod +x scripts/shell/setup.sh
./scripts/shell/setup.sh
```

### 3. Configure as Variáveis de Ambiente

```bash
cp config/n8n/.env.template .env
nano .env  # Configure todas as variáveis
```

### 4. Inicie os Serviços

```bash
docker-compose up -d
```

### 5. Acesse o Sistema

- **N8N**: http://localhost:5678
- **Grafana**: http://localhost:3000
- **API Python**: http://localhost:5000/health

## ⚙️ Configuração

### Variáveis de Ambiente Essenciais

```bash
# N8N
N8N_HOST=seu-dominio.com
N8N_USER=admin
N8N_PASSWORD=senha_segura

# OpenAI
OPENAI_API_KEY=sk-sua_chave_aqui

# DATAJUD CNJ
DATAJUD_USERNAME=seu_usuario
DATAJUD_PASSWORD=sua_senha

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type": "service_account"...}

# Banco de Dados
POSTGRES_PASSWORD=senha_postgres_segura
```

### Credenciais no N8N

Após iniciar o N8N, configure as seguintes credenciais:

1. **Google OAuth2**: Para Drive, Docs e Sheets
2. **OpenAI**: Para geração de conteúdo
3. **DATAJUD**: Para pesquisa jurisprudencial
4. **SMTP**: Para notificações por email

## 📊 Workflows Disponíveis

### 1. Workflow Principal

**Arquivo**: `n8n-workflows/templates/main-workflow.json`

**Fluxo**:
1. Recepção de PDF via webhook
2. Extração de texto automática
3. Análise FIRAC
4. Pesquisa jurisprudencial no DATAJUD
5. Análise de distinguish
6. Geração de minuta com IA
7. Salvamento no Google Docs
8. Registro no Google Sheets
9. Notificação por email

### 2. Workflow de Pesquisa Jurisprudencial

**Arquivo**: `n8n-workflows/templates/jurisprudence-search.json`

Busca automatizada em todas as instâncias do Judiciário brasileiro via API DATAJUD.

### 3. Workflow de Análise de Distinguish

**Arquivo**: `n8n-workflows/templates/distinguish-analysis.json`

Compara precedentes com fatos do caso atual para determinar aplicabilidade.

## 🔌 APIs Disponíveis

### Extração de PDF
```bash
POST /extract-pdf
Content-Type: application/json

{
  "pdf_content": "base64_encoded_pdf"
}
```

### Análise FIRAC
```bash
POST /firac-analysis
Content-Type: application/json

{
  "text": "texto_do_processo_judicial"
}
```

### Pesquisa DATAJUD
```bash
POST /datajud-search
Content-Type: application/json

{
  "tribunal": "tjsp",
  "classe_codigo": 1116,
  "texto_livre": "execução fiscal"
}
```

### Análise Distinguish
```bash
POST /distinguish-analysis
Content-Type: application/json

{
  "current_facts": "fatos_do_caso_atual",
  "precedent_data": {...}
}
```

### Geração de Documentos
```bash
POST /generate-document
Content-Type: application/json

{
  "document_type": "sentenca",
  "case_data": {...}
}
```

## 🔒 Segurança e LGPD

### Medidas de Segurança Implementadas

- **Autenticação**: Básica no N8N + JWT nas APIs
- **Criptografia**: SSL/TLS para todas as comunicações
- **Isolamento**: Containers Docker em rede privada
- **Backup**: Automático com retenção configurável
- **Logs**: Auditoria completa de todas as operações

### Compliance LGPD

- **Minimização**: Coleta apenas dados necessários
- **Transparência**: Logs detalhados de processamento
- **Retenção**: Configurável via `EXECUTIONS_DATA_MAX_AGE`
- **Exclusão**: Scripts automáticos de limpeza
- **Pseudonimização**: Dados sensíveis são mascarados

## 📈 Monitoramento

### Grafana Dashboards

- **Sistema**: CPU, Memória, Disco
- **N8N**: Execuções, Erros, Performance
- **APIs**: Latência, Taxa de Erro, Throughput
- **Banco**: Queries, Conexões, Tamanho

### Alertas Configurados

- **Falhas de Workflow**: Email/Slack
- **Alto Uso de Recursos**: Telegram
- **Erros de API**: WhatsApp
- **Backup Failures**: Email

## 🔧 Desenvolvimento

### Estrutura do Projeto

```
judicial-automation-system/
├── docs/                    # Documentação
├── infrastructure/          # Docker, Terraform, Nginx
├── n8n-workflows/          # Templates de workflows
├── scripts/                # Python, Shell, SQL
├── config/                 # Configurações
├── data/                   # Dados e templates
├── monitoring/             # Prometheus, Grafana
├── security/               # SSL, Backups, LGPD
└── tests/                  # Testes unitários e E2E
```

### Adicionando Novos Workflows

1. Crie o workflow no N8N
2. Exporte como JSON
3. Salve em `n8n-workflows/templates/`
4. Documente no README
5. Adicione testes se necessário

### Contribuindo

1. Fork o projeto
2. Crie uma branch feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 🆘 Solução de Problemas

### Problemas Comuns

#### N8N não inicia
```bash
# Verificar logs
docker-compose logs n8n

# Verificar banco de dados
docker-compose logs postgres
```

#### API Python não responde
```bash
# Verificar health check
curl http://localhost:5000/health

# Verificar logs
docker-compose logs python-services
```

#### Falha na integração Google
1. Verifique as credenciais OAuth2
2. Confirme as permissões de API
3. Teste manualmente a conectividade

#### Erro na API DATAJUD
1. Confirme usuário/senha
2. Verifique rate limiting
3. Teste endpoint manualmente

### Logs e Debug

```bash
# Logs em tempo real
docker-compose logs -f

# Logs específicos
docker-compose logs n8n
docker-compose logs python-services
docker-compose logs postgres

# Debug mode
docker-compose up --no-daemon
```

## 📚 Documentação Adicional

- [Guia de Deploy](docs/DEPLOYMENT_GUIDE.md)
- [Documentação da API](docs/API_DOCUMENTATION.md)
- [Guia de Segurança](docs/SECURITY_GUIDE.md)
- [Tutorial N8N](docs/N8N_TUTORIAL.md)

## 📋 Roadmap

### Versão 1.1
- [ ] Interface web dashboard
- [ ] Integração WhatsApp Business
- [ ] OCR avançado com Google Vision
- [ ] Template marketplace

### Versão 1.2
- [ ] Machine Learning para classificação
- [ ] Integração com PJe
- [ ] API GraphQL
- [ ] Mobile app

### Versão 2.0
- [ ] Multi-tenant
- [ ] Kubernetes deployment
- [ ] Blockchain para auditoria
- [ ] IA local com Ollama

## 📝 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🤝 Suporte

### Comunidade

- **GitHub Issues**: Reportar bugs e sugestões
- **Discussions**: Perguntas e discussões
- **Wiki**: Documentação colaborativa

### Comercial

Para suporte comercial, consultoria ou customizações:
- Email: contato@seudominio.com
- WhatsApp: +55 (XX) XXXXX-XXXX

## 👥 Autores

- **Seu Nome** - *Desenvolvimento Inicial* - [@seuusuario](https://github.com/seuusuario)

## 🙏 Agradecimentos

- CNJ pela API DATAJUD
- Comunidade N8N
- OpenAI pela API
- Contribuidores do projeto

---

**⚠️ Aviso Legal**: Este sistema é uma ferramenta de apoio. Decisões judiciais devem sempre ser validadas por profissionais qualificados. O sistema não substitui o conhecimento jurídico e a responsabilidade do magistrado.