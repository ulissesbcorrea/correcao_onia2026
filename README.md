# 🔍 ONIA — Fraud Detection Dashboard

Sistema de detecção de fraude para a **2ª Olimpíada Nacional de Inteligência Artificial (ONIA)**, 2ª etapa, 3ª fase. Permite que múltiplos avaliadores revisem ~1500 alunos, identifiquem colas (respostas idênticas na mesma escola, justificativas similares), e gerenciem o fluxo de aprovação/rejeição até atingir a meta de 200 aprovados.

---

## 📊 Funcionalidades

### Para Administradores
- **Upload de XLSX** — importa dados da planilha com detecção automática de linhas amarelas (alto risco de fraude)
- **Dashboard** — visão geral: total de alunos, aprovados, rejeitados, flags de fraude, progresso para 200
- **Gerenciar Avaliadores** — criar/desativar contas de avaliadores
- **Distribuir Alunos** — round-robin automático entre avaliadores ativos
- **Redistribuir** — rebalancear carga de trabalho

### Para Avaliadores
- **Fila de Revisão** — lista paginada dos alunos atribuídos, com destaque amarelo/vermelho para fraudes
- **Detalhe do Aluno** — nome, escola, acertos (0-20), respostas Q1-Q20, foto da justificativa
- **Aprovar / Rejeitar** — decisão com comentário opcional
- **Link para Eduspace** — acesso direto à plataforma de correção com fotos das justificativas

### Detecção de Fraude (automática pós-upload)
1. **Respostas Idênticas — Mesma Escola** — flag HIGH se 100% idênticas, MEDIUM se ≥80%
2. **Justificativas Idênticas** — compara hash SHA-256 das fotos entre alunos da mesma escola
3. **Linhas Amarelas** — importadas como flags manuais de alto risco

### Meta de 200 Aprovados
- Contador atômico incrementado a cada aprovação
- Barra de progresso na navbar com polling a cada 30s
- Modal de celebração ao atingir 200

---

## 🏗️ Arquitetura

```
Flask 3.x (SSR com Jinja2) + Bootstrap 5 + SQLite
├── JWT: flask-jwt-extended (admin / evaluator roles)
├── ORM: Flask-SQLAlchemy
├── XLSX: openpyxl (com detecção de fill amarelo)
├── Fuzzy: rapidfuzz
└── Senhas: bcrypt
```

### Estrutura de Arquivos

```
onia/
├── run.py                        # Dev server (Flask built-in)
├── config.py                     # Dev / Test / Prod
├── requirements.txt
├── .env.example
│
├── app/
│   ├── __init__.py               # create_app() factory
│   ├── extensions.py             # db, migrate, jwt
│   │
│   ├── models/                   # SQLAlchemy models
│   │   ├── evaluator.py          # Usuários (admin / evaluator)
│   │   ├── school.py             # Escolas
│   │   ├── student.py            # Alunos (status, is_flagged)
│   │   ├── answer.py             # Respostas Q1-Q20
│   │   ├── justification.py      # URLs das justificativas
│   │   ├── fraud_flag.py         # Alertas de fraude
│   │   ├── review.py             # Decisões dos avaliadores
│   │   ├── import_log.py         # Log de uploads
│   │   └── approval_counter.py   # Contador singleton (meta 200)
│   │
│   ├── auth/                     # Login JWT, criar/gerenciar avaliadores
│   ├── upload/                   # Upload XLSX + parser (openpyxl)
│   ├── fraud/                    # Algoritmos de detecção + endpoints
│   ├── review/                   # Fila, aprovar/rejeitar, counter
│   ├── distribution/             # Round-robin assignment
│   ├── dashboard/                # Summary + lista paginada
│   │
│   ├── templates/                # Jinja2 (Bootstrap 5)
│   │   ├── login.html
│   │   ├── admin/dashboard.html
│   │   └── evaluator/assignments.html
│   │
│   └── utils/                    # Error handlers, pagination
│
└── deploy/
    ├── install.sh                # Script de instalação completa
    ├── onia.service              # Systemd unit
    ├── onia-nginx.conf           # Config nginx
    └── rollback.sh               # Script de reversão
```

### Database Schema

| Tabela | Descrição |
|--------|-----------|
| `evaluators` | Usuários: id, name, email (unique), password_hash (bcrypt), role |
| `schools` | Escolas: id, name (unique), city, state, polo |
| `students` | Alunos: name, school_id (FK), score, status, is_flagged, flag_level |
| `answers` | Respostas: student_id (FK), question_number (1-20), selected_option (A-E) |
| `justifications` | Fotos: student_id (FK), photo_url, photo_hash (SHA-256) |
| `fraud_flags` | Alertas: student_id (FK), source (manual/algorithmic), level, reason |
| `reviews` | Decisões: student_id (FK), evaluator_id (FK), decision, notes |
| `import_logs` | Tracking de uploads XLSX |
| `approval_counter` | Singleton (id=1): count, goal (200), alert_triggered |

---

## 🚀 Deploy (Oracle Cloud)

### Pré-requisitos
- Ubuntu 22.04+ com Python 3.9+, nginx, git
- Domínio configurado com HTTPS (Certbot/Let's Encrypt)

### Instalação

```bash
# 1. Clonar o repositório
cd ~/servers
git clone https://github.com/ulissesbcorrea/correcao_onia2026.git
cd correcao_onia2026

# 2. Rodar script de instalação
bash deploy/install.sh

# 3. Verificar status
sudo systemctl status onia
```

O script `install.sh`:
- Cria virtualenv e instala dependências
- Cria `.env` com chaves seguras
- Inicializa o banco de dados e cria admin
- Instala systemd service (`onia`)
- Configura nginx em `/h2ia/onia/`

### Comandos de Manutenção

```bash
sudo systemctl status onia          # Status do serviço
sudo systemctl restart onia         # Reiniciar
sudo journalctl -u onia -f          # Logs em tempo real
sudo systemctl stop onia            # Parar

# Rollback (remove serviço, preserva banco)
bash deploy/rollback.sh
```

### Nginx

O serviço é acessível em `https://absapt.tk/h2ia/onia/`. A configuração do nginx faz proxy para `127.0.0.1:8001` (gunicorn com 4 workers).

---

## 💻 Desenvolvimento Local

```bash
cd onia
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Criar banco e admin
python3 -c "
import bcrypt
from app import create_app
from app.extensions import db
from app.models import Evaluator, ApprovalCounter
app = create_app()
with app.app_context():
    db.create_all()
    pw = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt()).decode()
    db.session.add(Evaluator(name='Admin', email='admin@onia.com', password_hash=pw, role='admin'))
    db.session.add(ApprovalCounter(id=1, count=0, goal=200))
    db.session.commit()
"

# Iniciar servidor de desenvolvimento
python run.py
# Acessar: http://localhost:5001/login
```

---

## 📤 Upload do XLSX

### Estrutura esperada da planilha

| Coluna | Descrição |
|--------|-----------|
| Id | Identificador do aluno |
| Avaliador | Nome do avaliador (pode vir vazio) |
| Status | Status atual na planilha |
| Justificativa | URL/indicador da justificativa |
| Nome Completo | Nome do aluno |
| Acertos | Número de acertos (0-20) |
| Estado | UF |
| Município | Cidade |
| Escola | Nome da escola |
| Polo | Polo regional |
| Situação | Status adicional |
| Q1..Q20 | Respostas de múltipla escolha (A-E) |

**Linhas com preenchimento amarelo** = alto risco de fraude (importadas como flags manuais).

### Via API

```bash
TOKEN=$(curl -s -X POST https://absapt.tk/h2ia/onia/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@onia.com","password":"admin123"}' | jq -r '.access_token')

curl -X POST https://absapt.tk/h2ia/onia/api/upload/xlsx \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@2ONIA_2etapa_3fase.xlsx"
```

### Via Interface

1. Login como admin
2. No dashboard, clique em "Selecionar Arquivo"
3. Escolha o `.xlsx` e aguarde o processamento
4. Os alunos serão importados e a detecção de fraude rodará automaticamente

---

## 🔑 API Endpoints

### Auth (`/api/auth`)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/login` | Login → JWT tokens |
| POST | `/refresh` | Renovar access token |
| GET | `/me` | Dados do usuário logado |
| GET | `/evaluators` | Listar avaliadores |
| POST | `/evaluators` | Criar avaliador (admin) |
| DELETE | `/evaluators/<id>` | Desativar avaliador (admin) |

### Upload (`/api/upload`)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/xlsx` | Upload e importação XLSX (admin) |
| GET | `/batches` | Listar uploads anteriores |
| GET | `/batches/<id>` | Detalhes de um upload |

### Fraude (`/api/fraud`)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/alerts` | Listar flags de fraude (filtros: level, school, resolved) |
| GET | `/alerts/<id>` | Detalhe de uma flag |
| POST | `/detect` | Re-executar detecção |
| GET | `/stats` | Estatísticas de fraude |

### Review (`/api/review`)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/queue` | Fila do avaliador (paginada, filtrável) |
| GET | `/submissions/<id>` | Detalhe completo do aluno |
| POST | `/submissions/<id>/approve` | Aprovar aluno |
| POST | `/submissions/<id>/reject` | Rejeitar aluno |

### Distribution (`/api/distribution`)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/status` | Progresso por avaliador |
| POST | `/assign` | Distribuir alunos (round-robin) |
| POST | `/redistribute` | Redistribuir (remove pendentes e reatribui) |

### Dashboard (`/api/dashboard`)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/summary` | Cards de resumo |
| GET | `/submissions` | Lista paginada e filtrável |
| GET | `/counter` | Status do contador de 200 |

---

## 🔒 Segurança

- Senhas hasheadas com bcrypt
- JWT com access token (15min) + refresh token (7 dias)
- Rotas protegidas por decorators: `@admin_required`, `@evaluator_required`
- Upload restrito a admins
- Chaves secretas configuráveis via `.env`

---

## 📝 Licença

Projeto interno — Olimpíada Nacional de Inteligência Artificial (ONIA).
