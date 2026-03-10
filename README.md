# Cloud API Deployment Manager / Gerenciador de Deploy de API na Nuvem

## English

### About the Project

A cloud deployment management system for API applications on Azure. Implements deployment CRUD with version tracking, multiple deployment strategies (blue-green, canary, rolling), health check monitoring, and multi-environment management (dev/staging/prod) with promotion workflows.

### Architecture

```
azure-cloud-api-deploy/
|-- src/
|   |-- deploy/
|   |   |-- manager.py          # Deployment CRUD with versioning
|   |   |-- strategies.py       # Blue-green, canary, rolling strategies
|   |   |-- health_checker.py   # Health check monitoring
|   |-- environments/
|   |   |-- env_manager.py      # Environment management (dev/staging/prod)
|-- tests/
|   |-- test_deploy.py          # 20+ unit tests
|-- main.py                     # Demo script
|-- requirements.txt
|-- .gitignore
|-- README.md
```

### Key Features

- **Deployment Management**: Full CRUD with version history and rollback
- **Blue-Green Strategy**: Zero-downtime deployments with instant traffic switching
- **Canary Strategy**: Gradual traffic shifting with configurable percentages
- **Rolling Strategy**: Batch-based updates with configurable batch sizes
- **Health Monitoring**: Configurable probes with healthy/unhealthy thresholds
- **Environment Management**: Dev, staging, prod with promotion workflows
- **Protected Environments**: Approval-required deployments for production
- **Version History**: Complete audit trail of all deployment versions

### Deployment Strategies

| Strategy | Description |
|---|---|
| Blue-Green | Two identical environments with instant traffic switch |
| Canary | Gradual traffic shift (10% -> 25% -> 50% -> 100%) |
| Rolling | Batch-by-batch instance updates |

### How to Run

```bash
# Clone the repository
git clone https://github.com/galafis/azure-cloud-api-deploy.git
cd azure-cloud-api-deploy

# Install dependencies
pip install -r requirements.txt

# Run the demo
python main.py

# Run tests
pytest tests/ -v
```

### Technologies

| Technology | Purpose |
|---|---|
| Python 3.10+ | Core language |
| pytest | Testing framework |
| dataclasses | Data models |
| enum | Strategy and status types |

---

## Portugues

### Sobre o Projeto

Sistema de gerenciamento de deploy na nuvem para aplicacoes de API no Azure. Implementa CRUD de deployments com rastreamento de versoes, multiplas estrategias de deploy (blue-green, canary, rolling), monitoramento de health check e gerenciamento multi-ambiente (dev/staging/prod) com fluxos de promocao.

### Funcionalidades Principais

- **Gerenciamento de Deploy**: CRUD completo com historico de versoes e rollback
- **Estrategia Blue-Green**: Deploys sem downtime com troca instantanea de trafego
- **Estrategia Canary**: Desvio gradual de trafego com porcentagens configuraveis
- **Estrategia Rolling**: Atualizacoes em lotes com tamanho de batch configuravel
- **Monitoramento de Saude**: Probes configuraveis com limiares de saudavel/nao-saudavel
- **Gerenciamento de Ambientes**: Dev, staging, prod com fluxos de promocao
- **Ambientes Protegidos**: Deploys com aprovacao obrigatoria para producao
- **Historico de Versoes**: Trilha completa de auditoria de todas as versoes

### Como Executar

```bash
# Clonar o repositorio
git clone https://github.com/galafis/azure-cloud-api-deploy.git
cd azure-cloud-api-deploy

# Instalar dependencias
pip install -r requirements.txt

# Executar o demo
python main.py

# Executar os testes
pytest tests/ -v
```

### Tecnologias Utilizadas

| Tecnologia | Finalidade |
|---|---|
| Python 3.10+ | Linguagem principal |
| pytest | Framework de testes |
| Azure App Service | Hospedagem na nuvem |
| Docker | Containerizacao |

## Autor / Author

**Gabriel Demetrios Lafis**
