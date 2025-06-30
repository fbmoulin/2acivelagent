# Criando o workflow principal do N8N como template JSON
main_workflow = {
    "name": "Sistema Automação Jurídica - Workflow Principal",
    "nodes": [
        {
            "parameters": {},
            "id": "node-1",
            "name": "Webhook - Receber PDF",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 1,
            "position": [240, 300],
            "webhookId": "judicial-automation-webhook"
        },
        {
            "parameters": {
                "path": "={{$json[\"attachments\"][0][\"url\"]}}"
            },
            "id": "node-2",
            "name": "Google Drive - Buscar PDF",
            "type": "n8n-nodes-base.googleDrive",
            "typeVersion": 3,
            "position": [460, 300]
        },
        {
            "parameters": {
                "requestMethod": "POST",
                "url": "http://localhost:5000/extract-pdf",
                "options": {
                    "bodyContentType": "json"
                },
                "jsonParameters": True,
                "bodyParametersJson": "={{$json}}"
            },
            "id": "node-3",
            "name": "Python - Extrair Texto PDF",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [680, 300]
        },
        {
            "parameters": {
                "requestMethod": "POST", 
                "url": "http://localhost:5000/firac-analysis",
                "options": {
                    "bodyContentType": "json"
                },
                "jsonParameters": True,
                "bodyParametersJson": "={{$json}}"
            },
            "id": "node-4",
            "name": "Análise FIRAC",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [900, 300]
        },
        {
            "parameters": {
                "conditions": {
                    "string": [
                        {
                            "value1": "={{$json[\"analysis_type\"]}}",
                            "operation": "equal",
                            "value2": "jurisprudence"
                        }
                    ]
                }
            },
            "id": "node-5", 
            "name": "Switch - Tipo de Análise",
            "type": "n8n-nodes-base.switch",
            "typeVersion": 1,
            "position": [1120, 300]
        },
        {
            "parameters": {
                "requestMethod": "POST",
                "url": "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search",
                "authentication": "genericCredentialType",
                "genericAuthType": "httpBasicAuth",
                "options": {
                    "bodyContentType": "json"
                },
                "jsonParameters": True,
                "bodyParametersJson": "={{$json}}"
            },
            "id": "node-6",
            "name": "DATAJUD - Pesquisa Jurisprudência",
            "type": "n8n-nodes-base.httpRequest", 
            "typeVersion": 4,
            "position": [1340, 200]
        },
        {
            "parameters": {
                "requestMethod": "POST",
                "url": "http://localhost:5000/distinguish-analysis", 
                "options": {
                    "bodyContentType": "json"
                },
                "jsonParameters": True,
                "bodyParametersJson": "={{$json}}"
            },
            "id": "node-7",
            "name": "Análise Distinguish",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [1560, 200]
        },
        {
            "parameters": {
                "requestMethod": "POST",
                "url": "https://api.openai.com/v1/chat/completions",
                "authentication": "genericCredentialType",
                "genericAuthType": "httpHeaderAuth", 
                "options": {
                    "bodyContentType": "json"
                },
                "jsonParameters": True,
                "bodyParametersJson": "={{$json}}"
            },
            "id": "node-8",
            "name": "OpenAI - Gerar Minuta",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [1780, 300]
        },
        {
            "parameters": {
                "resource": "document",
                "operation": "create",
                "documentId": "={{$json[\"document_id\"]}}",
                "title": "Minuta - {{$json[\"case_number\"]}}"
            },
            "id": "node-9",
            "name": "Google Docs - Salvar Minuta",
            "type": "n8n-nodes-base.googleDocs",
            "typeVersion": 1,
            "position": [2000, 300]
        },
        {
            "parameters": {
                "operation": "appendOrUpdate",
                "documentId": "YOUR_SHEET_ID",
                "sheetName": "Processos",
                "columnMappings": {
                    "processo": "={{$json[\"case_number\"]}}",
                    "data": "={{$now}}",
                    "status": "={{$json[\"status\"]}}",
                    "minuta_link": "={{$json[\"document_url\"]}}"
                }
            },
            "id": "node-10",
            "name": "Google Sheets - Registrar",
            "type": "n8n-nodes-base.googleSheets",
            "typeVersion": 4,
            "position": [2220, 300]
        },
        {
            "parameters": {
                "fromEmail": "sistema@seudominio.com",
                "toEmail": "={{$json[\"user_email\"]}}",
                "subject": "Análise Processual Concluída - {{$json[\"case_number\"]}}",
                "message": "A análise do processo foi concluída com sucesso."
            },
            "id": "node-11",
            "name": "Email - Notificação",
            "type": "n8n-nodes-base.emailSend",
            "typeVersion": 2,
            "position": [2440, 300]
        }
    ],
    "connections": {
        "Webhook - Receber PDF": {
            "main": [
                [
                    {
                        "node": "Google Drive - Buscar PDF",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Google Drive - Buscar PDF": {
            "main": [
                [
                    {
                        "node": "Python - Extrair Texto PDF", 
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Python - Extrair Texto PDF": {
            "main": [
                [
                    {
                        "node": "Análise FIRAC",
                        "type": "main", 
                        "index": 0
                    }
                ]
            ]
        },
        "Análise FIRAC": {
            "main": [
                [
                    {
                        "node": "Switch - Tipo de Análise",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Switch - Tipo de Análise": {
            "main": [
                [
                    {
                        "node": "DATAJUD - Pesquisa Jurisprudência",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "DATAJUD - Pesquisa Jurisprudência": {
            "main": [
                [
                    {
                        "node": "Análise Distinguish",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Análise Distinguish": {
            "main": [
                [
                    {
                        "node": "OpenAI - Gerar Minuta",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "OpenAI - Gerar Minuta": {
            "main": [
                [
                    {
                        "node": "Google Docs - Salvar Minuta",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Google Docs - Salvar Minuta": {
            "main": [
                [
                    {
                        "node": "Google Sheets - Registrar",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Google Sheets - Registrar": {
            "main": [
                [
                    {
                        "node": "Email - Notificação",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        }
    },
    "pinData": {},
    "settings": {
        "saveManualExecutions": True,
        "saveDataSuccessExecution": "all",
        "saveDataErrorExecution": "all",
        "saveDataProgressExecution": True
    },
    "staticData": {},
    "tags": ["legal", "automation", "judiciary"],
    "triggerCount": 1,
    "updatedAt": "2025-06-30T11:54:45.441Z",
    "versionId": "1"
}

# Salvando o workflow como JSON
workflow_json = json.dumps(main_workflow, indent=2, ensure_ascii=False)

print("🚀 WORKFLOW PRINCIPAL N8N CRIADO")
print("=" * 50)
print("📋 COMPONENTES DO WORKFLOW:")
print("1. Webhook para receber PDFs")
print("2. Google Drive para buscar arquivos") 
print("3. Extração de texto com Python")
print("4. Análise FIRAC automática")
print("5. Switch para tipo de análise")
print("6. Pesquisa no DATAJUD")
print("7. Análise de Distinguish")
print("8. Geração de minuta com OpenAI")
print("9. Salvamento no Google Docs")
print("10. Registro no Google Sheets")
print("11. Notificação por email")
print("\n✅ Workflow JSON criado com sucesso!")
print(f"📝 Total de nós: {len(main_workflow['nodes'])}")
print(f"🔗 Total de conexões: {len(main_workflow['connections'])}")