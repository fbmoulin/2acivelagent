# Tutorial Passo a Passo - Configuração N8N para Automação Jurídica

## 📋 Índice

1. [Acesso Inicial ao N8N](#1-acesso-inicial-ao-n8n)
2. [Configuração de Credenciais](#2-configuração-de-credenciais)
3. [Importação de Workflows](#3-importação-de-workflows)
4. [Configuração do Workflow Principal](#4-configuração-do-workflow-principal)
5. [Teste e Validação](#5-teste-e-validação)
6. [Monitoramento e Logs](#6-monitoramento-e-logs)
7. [Solução de Problemas](#7-solução-de-problemas)

## 1. Acesso Inicial ao N8N

### 1.1 Acessar o N8N
```
URL: http://localhost:5678
Usuário: admin (ou conforme configurado em .env)
Senha: sua_senha_configurada
```

### 1.2 Primeira Configuração
1. Faça login com as credenciais configuradas
2. Aceite os termos de uso
3. Configure seu perfil de usuário
4. Defina o timezone para `America/Sao_Paulo`

## 2. Configuração de Credenciais

### 2.1 Google OAuth2 API

**Passos**:
1. Vá em **Credentials** → **Create New**
2. Selecione **Google OAuth2 API**
3. Preencha os campos:

```
Name: Google-Judicial-System
Client ID: seu_client_id_do_google
Client Secret: seu_client_secret_do_google
Scope: https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/documents,https://www.googleapis.com/auth/spreadsheets
```

4. Clique em **Connect my account**
5. Autorize as permissões no Google
6. **Save** a credencial

### 2.2 OpenAI Credentials

**Passos**:
1. **Credentials** → **Create New**
2. Selecione **OpenAI**
3. Preencha:

```
Name: OpenAI-Legal-Analysis
API Key: sk-sua_chave_openai_aqui
```

4. **Test connection** e **Save**

### 2.3 HTTP Basic Auth (DATAJUD)

**Passos**:
1. **Credentials** → **Create New**
2. Selecione **HTTP Basic Auth**
3. Configure:

```
Name: DATAJUD-CNJ-API
User: seu_usuario_datajud
Password: sua_senha_datajud
```

4. **Save**

### 2.4 SMTP Email

**Passos**:
1. **Credentials** → **Create New**
2. Selecione **SMTP**
3. Configure:

```
Name: Email-Notifications
Host: smtp.gmail.com
Port: 587
Security: STARTTLS
User: seu_email@gmail.com
Password: sua_senha_app_gmail
```

4. **Test** e **Save**

## 3. Importação de Workflows

### 3.1 Importar Workflow Principal

1. Vá em **Workflows**
2. Clique em **Import from File**
3. Selecione o arquivo `main-workflow-n8n.json`
4. Clique em **Import**
5. Renomeie para "Sistema Automação Jurídica - Principal"

### 3.2 Configurar Webhook

1. Abra o workflow importado
2. Clique no nó **Webhook - Receber PDF**
3. Configure:

```
HTTP Method: POST
Path: judicial-automation
Authentication: None
Response: Immediately
```

4. **Execute Node** para ativar o webhook
5. Copie a URL do webhook gerada

### 3.3 Vincular Credenciais aos Nós

Para cada nó que requer credenciais:

**Google Drive**:
- Credential: `Google-Judicial-System`

**HTTP Request (Python Services)**:
- Não requer credencial (localhost)

**HTTP Request (DATAJUD)**:
- Authentication: `Basic Auth`
- Credential: `DATAJUD-CNJ-API`

**Email Send**:
- Credential: `Email-Notifications`

## 4. Configuração do Workflow Principal

### 4.1 Configurar Google Drive Node

```javascript
Operation: Download
File ID: ={{$json["file_id"]}}
Options:
  - Binary Property: data
```

### 4.2 Configurar Python PDF Extraction

```javascript
URL: http://python-services:5000/extract-pdf
Method: POST
Body:
{
  "pdf_content": "={{$binary.data.toString('base64')}}"
}
```

### 4.3 Configurar FIRAC Analysis

```javascript
URL: http://python-services:5000/firac-analysis
Method: POST
Body:
{
  "text": "={{$json['text']}}",
  "case_number": "={{$json['case_number'] || 'AUTO'}}"
}
```

### 4.4 Configurar Switch Node

```javascript
Condition Type: String
Value 1: ={{$json["requires_jurisprudence"]}}
Operation: equal
Value 2: true
```

### 4.5 Configurar DATAJUD Search

```javascript
URL: http://python-services:5000/datajud-search
Method: POST
Body:
{
  "tribunal": "={{$json['tribunal'] || 'tjsp'}}",
  "texto_livre": "={{$json['search_terms']}}",
  "size": 10
}
```

### 4.6 Configurar Document Generation

```javascript
URL: http://python-services:5000/generate-document
Method: POST
Body:
{
  "document_type": "sentenca",
  "case_data": "={{$json}}",
  "precedents": "={{$json['jurisprudence_results']}}"
}
```

### 4.7 Configurar Google Docs Save

```javascript
Resource: Document
Operation: Create
Title: Minuta - {{$json["case_number"]}} - {{$now.format('DD/MM/YYYY')}}
Content: ={{$json["generated_text"]}}
```

### 4.8 Configurar Google Sheets Log

```javascript
Operation: Append or Update
Document ID: YOUR_GOOGLE_SHEET_ID
Sheet Name: Processos
Values to Send: Define Fields Manually

Campos:
- processo: ={{$json["case_number"]}}
- data_processamento: ={{$now}}
- status: ={{$json["status"] || 'Concluído'}}
- minuta_url: ={{$json["document_url"]}}
- usuario: ={{$json["user_email"]}}
```

## 5. Teste e Validação

### 5.1 Teste Manual do Workflow

1. Clique em **Execute Workflow**
2. Use dados de teste:

```json
{
  "file_id": "ID_DO_ARQUIVO_GOOGLE_DRIVE",
  "case_number": "0001234-12.2024.8.26.0001",
  "user_email": "teste@exemplo.com",
  "tribunal": "tjsp",
  "requires_jurisprudence": true
}
```

3. Acompanhe a execução nó por nó
4. Verifique os outputs de cada etapa

### 5.2 Teste via Webhook

```bash
curl -X POST \
  'http://localhost:5678/webhook/judicial-automation' \
  -H 'Content-Type: application/json' \
  -d '{
    "file_id": "SEU_FILE_ID_AQUI",
    "case_number": "0001234-12.2024.8.26.0001",
    "user_email": "seu@email.com"
  }'
```

### 5.3 Validar Integração com Python Services

```bash
# Testar API diretamente
curl -X GET http://localhost:5000/health

# Deve retornar:
{
  "status": "healthy",
  "timestamp": "2025-06-30T...",
  "services": {
    "redis": true,
    "openai": true,
    "datajud": true
  }
}
```

## 6. Monitoramento e Logs

### 6.1 Acessar Executions

1. Vá em **Executions** no menu lateral
2. Visualize execuções recentes
3. Clique em uma execução para ver detalhes
4. Analise dados de entrada/saída de cada nó

### 6.2 Configurar Alertas

1. Vá em **Settings** → **Log streaming**
2. Configure webhook para erros:

```
Webhook URL: http://python-services:5000/webhook/n8n-error
Events: workflow.failed, node.failed
```

### 6.3 Logs do Sistema

```bash
# Logs do N8N
docker-compose logs -f n8n

# Logs dos Python Services
docker-compose logs -f python-services

# Logs do PostgreSQL
docker-compose logs -f postgres
```

## 7. Solução de Problemas

### 7.1 Workflow não executa

**Possíveis causas**:
- Credenciais incorretas
- Webhook inativo
- Serviços Python offline

**Soluções**:
```bash
# Verificar status dos serviços
docker-compose ps

# Restartar serviços
docker-compose restart n8n python-services

# Verificar logs
docker-compose logs n8n
```

### 7.2 Erro na API do Google

**Erro comum**: `Invalid credentials`

**Solução**:
1. Revalidar credencial Google OAuth2
2. Verificar scopes corretos
3. Renovar token se necessário

### 7.3 Falha na conexão DATAJUD

**Erro comum**: `Authentication failed`

**Soluções**:
1. Verificar usuário/senha DATAJUD
2. Testar credencial fora do N8N:

```bash
curl -u usuario:senha \
  'https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search' \
  -H 'Content-Type: application/json' \
  -d '{"query":{"match_all":{}},"size":1}'
```

### 7.4 Python Services não respondem

**Sintomas**:
- Timeout em nós HTTP Request
- Erro 500 ou connection refused

**Soluções**:
```bash
# Verificar saúde da API
curl http://localhost:5000/health

# Verificar logs Python
docker-compose logs python-services

# Restartar serviço
docker-compose restart python-services
```

### 7.5 Problemas de Performance

**Sintomas**:
- Workflow lento
- Timeouts frequentes

**Otimizações**:
1. Aumentar timeout nos nós HTTP:
   ```javascript
   Options > Timeout: 300000  // 5 minutos
   ```

2. Configurar retry automático:
   ```javascript
   Options > Retry: 3
   Options > Retry Wait: 10000
   ```

3. Otimizar queries DATAJUD:
   ```javascript
   Body: {
     "size": 10,  // Limitar resultados
     "timeout": "30s"
   }
   ```

## 8. Boas Práticas

### 8.1 Nomenclatura

- Use nomes descritivos para nós
- Prefixe com tipo: "HTTP - ", "Google - "
- Mantenha consistência

### 8.2 Tratamento de Erros

- Configure **Error Trigger** nodes
- Use **If** nodes para validação
- Implemente retry logic

### 8.3 Versionamento

- Salve workflow antes de mudanças
- Use tags para versões
- Mantenha backup dos JSONs

### 8.4 Segurança

- Não hardcode credenciais
- Use environment variables
- Configure timeouts adequados
- Limite payload size

## 9. Workflows Adicionais

### 9.1 Workflow de Backup

Crie workflow para backup automático:
1. **Schedule Trigger** (diário)
2. **Execute Command** → backup.sh
3. **Email** notification

### 9.2 Workflow de Monitoramento

Crie health check automático:
1. **Interval** trigger (5 min)
2. **HTTP Request** → /health
3. **If** node para verificar status
4. **Email/Slack** se unhealthy

### 9.3 Workflow de Limpeza

Para compliance LGPD:
1. **Schedule Trigger** (semanal)
2. **PostgreSQL** query para dados antigos
3. **Delete** executions antigas
4. **Log** ações de limpeza

---

## ✅ Checklist de Configuração

- [ ] N8N acessível e funcionando
- [ ] Todas as credenciais configuradas
- [ ] Workflow principal importado
- [ ] Webhook ativo e testado
- [ ] Python Services respondendo
- [ ] Teste end-to-end realizado
- [ ] Monitoramento configurado
- [ ] Backups funcionando
- [ ] Documentação atualizada

**🎉 Parabéns! Seu sistema de automação jurídica está pronto para uso!**