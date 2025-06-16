# Dicionário de Dados - Sistema de Notas Fiscais

## Tabela: notasfiscais

Armazena os dados principais (cabeçalho) das notas fiscais eletrônicas.

| Campo | Tipo | Tamanho | Descrição |
|-------|------|---------|-----------|
| chave_acesso | VARCHAR | 44 | Chave de acesso única da nota fiscal (PK) |
| modelo | VARCHAR | 100 | Modelo da nota fiscal (ex: "55 - NF-E EMITIDA EM SUBSTITUIÇÃO AO MODELO 1 OU 1A") |
| serie_nf | VARCHAR | 10 | Série da nota fiscal |
| numero_nf | VARCHAR | 20 | Número da nota fiscal |
| natureza_operacao | VARCHAR | 255 | Descrição da natureza da operação |
| data_emissao | DATE | - | Data de emissão da nota fiscal |
| evento_mais_recente | VARCHAR | 255 | Último evento registrado para a nota fiscal |
| data_hora_evento_mais_recente | TIMESTAMP | - | Data e hora do último evento |
| cpf_cnpj_emitente | VARCHAR | 20 | CPF ou CNPJ do emitente |
| razao_social_emitente | VARCHAR | 255 | Razão social do emitente |
| inscricao_estadual_emitente | VARCHAR | 20 | Inscrição estadual do emitente |
| uf_emitente | CHAR | 2 | UF do emitente |
| municipio_emitente | VARCHAR | 100 | Município do emitente |
| cnpj_destinatario | VARCHAR | 20 | CNPJ do destinatário |
| nome_destinatario | VARCHAR | 255 | Nome/razão social do destinatário |
| uf_destinatario | CHAR | 2 | UF do destinatário |
| indicador_ie_destinatario | VARCHAR | 50 | Indicador de inscrição estadual do destinatário |
| destino_operacao | VARCHAR | 100 | Tipo de destino da operação (interna/interestadual) |
| consumidor_final | VARCHAR | 50 | Indicador se é consumidor final |
| presenca_comprador | VARCHAR | 100 | Indicador de presença do comprador na transação |
| valor_nota_fiscal | DECIMAL | 15,2 | Valor total da nota fiscal |

## Tabela: itensnotafiscal

Armazena os itens/produtos de cada nota fiscal.

| Campo | Tipo | Tamanho | Descrição |
|-------|------|---------|-----------|
| id_item_nf | SERIAL | - | ID único do item (PK) |
| chave_acesso_nf | VARCHAR | 44 | Chave de acesso da nota fiscal (FK) |
| modelo | VARCHAR | 100 | Modelo da nota fiscal |
| serie_nf | VARCHAR | 10 | Série da nota fiscal |
| numero_nf | VARCHAR | 20 | Número da nota fiscal |
| natureza_operacao | VARCHAR | 255 | Descrição da natureza da operação |
| data_emissao | DATE | - | Data de emissão da nota fiscal |
| cpf_cnpj_emitente | VARCHAR | 20 | CPF ou CNPJ do emitente |
| razao_social_emitente | VARCHAR | 255 | Razão social do emitente |
| inscricao_estadual_emitente | VARCHAR | 20 | Inscrição estadual do emitente |
| uf_emitente | CHAR | 2 | UF do emitente |
| municipio_emitente | VARCHAR | 100 | Município do emitente |
| cnpj_destinatario | VARCHAR | 20 | CNPJ do destinatário |
| nome_destinatario | VARCHAR | 255 | Nome/razão social do destinatário |
| uf_destinatario | CHAR | 2 | UF do destinatário |
| indicador_ie_destinatario | VARCHAR | 50 | Indicador de inscrição estadual do destinatário |
| destino_operacao | VARCHAR | 100 | Tipo de destino da operação |
| consumidor_final | VARCHAR | 50 | Indicador se é consumidor final |
| presenca_comprador | VARCHAR | 100 | Indicador de presença do comprador |
| numero_produto | INT | - | Número sequencial do produto na nota |
| descricao_produto | VARCHAR | 500 | Descrição do produto/serviço |
| codigo_ncm_sh | VARCHAR | 20 | Código NCM/SH do produto |
| ncm_sh_tipo_produto | VARCHAR | 255 | Descrição do tipo de produto conforme NCM/SH |
| cfop | VARCHAR | 10 | Código Fiscal de Operações e Prestações |
| quantidade | DECIMAL | 15,4 | Quantidade do produto |
| unidade | VARCHAR | 20 | Unidade de medida |
| valor_unitario | DECIMAL | 15,4 | Valor unitário do produto |
| valor_total | DECIMAL | 15,2 | Valor total do item (quantidade × valor unitário) |

## Relacionamentos

- `itensnotafiscal.chave_acesso_nf` → `notasfiscais.chave_acesso` (FK)
- Uma nota fiscal pode ter múltiplos itens
- Exclusão em cascata: ao excluir uma nota fiscal, todos os itens são excluídos

## Observações

- Todos os campos são derivados diretamente dos arquivos CSV fornecidos
- A chave de acesso é única e serve como identificador principal
- Valores monetários usam precisão de 2 casas decimais
- Quantidades podem ter até 4 casas decimais para maior precisão
- Campos de texto têm tamanhos adequados para comportar os dados reais 