# db_utils.py
import asyncpg
import aiosql
import csv
import os
from datetime import datetime

from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

SQL_QUERIES = """
-- name: create_database_if_not_exists!
-- Attempt to create the database. This might require superuser privileges or specific grants.
-- It's often better to ensure the database exists manually or via a separate setup script.
-- For simplicity, we'll try to create it, but catch exceptions if it fails (e.g., due to lack of privileges or if it already exists).
CREATE DATABASE "{db_name}";

-- name: drop_tables!
DROP TABLE IF EXISTS itensnotafiscal;
DROP TABLE IF EXISTS notasfiscais;

-- name: create_notasfiscais_table!
CREATE TABLE IF NOT EXISTS notasfiscais (
    chave_acesso VARCHAR(44) PRIMARY KEY,
    modelo VARCHAR(100),
    serie_nf VARCHAR(10),
    numero_nf VARCHAR(20),
    natureza_operacao VARCHAR(255),
    data_emissao DATE,
    evento_mais_recente VARCHAR(255),
    data_hora_evento_mais_recente TIMESTAMP,
    cpf_cnpj_emitente VARCHAR(20),
    razao_social_emitente VARCHAR(255),
    inscricao_estadual_emitente VARCHAR(20),
    uf_emitente CHAR(2),
    municipio_emitente VARCHAR(100),
    cnpj_destinatario VARCHAR(20),
    nome_destinatario VARCHAR(255),
    uf_destinatario CHAR(2),
    indicador_ie_destinatario VARCHAR(50),
    destino_operacao VARCHAR(100),
    consumidor_final VARCHAR(50),
    presenca_comprador VARCHAR(100),
    valor_nota_fiscal DECIMAL(15,2)
);

-- name: create_itensnotafiscal_table!
CREATE TABLE IF NOT EXISTS itensnotafiscal (
    id_item_nf SERIAL PRIMARY KEY,
    chave_acesso_nf VARCHAR(44) NOT NULL,
    modelo VARCHAR(100),
    serie_nf VARCHAR(10),
    numero_nf VARCHAR(20),
    natureza_operacao VARCHAR(255),
    data_emissao DATE,
    cpf_cnpj_emitente VARCHAR(20),
    razao_social_emitente VARCHAR(255),
    inscricao_estadual_emitente VARCHAR(20),
    uf_emitente CHAR(2),
    municipio_emitente VARCHAR(100),
    cnpj_destinatario VARCHAR(20),
    nome_destinatario VARCHAR(255),
    uf_destinatario CHAR(2),
    indicador_ie_destinatario VARCHAR(50),
    destino_operacao VARCHAR(100),
    consumidor_final VARCHAR(50),
    presenca_comprador VARCHAR(100),
    numero_produto INT,
    descricao_produto VARCHAR(500),
    codigo_ncm_sh VARCHAR(20),
    ncm_sh_tipo_produto VARCHAR(255),
    cfop VARCHAR(10),
    quantidade DECIMAL(15,4),
    unidade VARCHAR(20),
    valor_unitario DECIMAL(15,4),
    valor_total DECIMAL(15,2),
    CONSTRAINT fk_nota_fiscal FOREIGN KEY (chave_acesso_nf) REFERENCES notasfiscais (chave_acesso) ON DELETE CASCADE
);

-- name: insert_nota_fiscal#
INSERT INTO notasfiscais (
    chave_acesso, modelo, serie_nf, numero_nf, natureza_operacao, data_emissao,
    evento_mais_recente, data_hora_evento_mais_recente, cpf_cnpj_emitente, razao_social_emitente,
    inscricao_estadual_emitente, uf_emitente, municipio_emitente, cnpj_destinatario,
    nome_destinatario, uf_destinatario, indicador_ie_destinatario, destino_operacao,
    consumidor_final, presenca_comprador, valor_nota_fiscal
) VALUES (
    :chave_acesso, :modelo, :serie_nf, :numero_nf, :natureza_operacao, :data_emissao,
    :evento_mais_recente, :data_hora_evento_mais_recente, :cpf_cnpj_emitente, :razao_social_emitente,
    :inscricao_estadual_emitente, :uf_emitente, :municipio_emitente, :cnpj_destinatario,
    :nome_destinatario, :uf_destinatario, :indicador_ie_destinatario, :destino_operacao,
    :consumidor_final, :presenca_comprador, :valor_nota_fiscal
)
ON CONFLICT (chave_acesso) DO NOTHING;

-- name: insert_item_nota_fiscal#
INSERT INTO itensnotafiscal (
    chave_acesso_nf, modelo, serie_nf, numero_nf, natureza_operacao, data_emissao,
    cpf_cnpj_emitente, razao_social_emitente, inscricao_estadual_emitente, uf_emitente,
    municipio_emitente, cnpj_destinatario, nome_destinatario, uf_destinatario,
    indicador_ie_destinatario, destino_operacao, consumidor_final, presenca_comprador,
    numero_produto, descricao_produto, codigo_ncm_sh, ncm_sh_tipo_produto, cfop,
    quantidade, unidade, valor_unitario, valor_total
) VALUES (
    :chave_acesso_nf, :modelo, :serie_nf, :numero_nf, :natureza_operacao, :data_emissao,
    :cpf_cnpj_emitente, :razao_social_emitente, :inscricao_estadual_emitente, :uf_emitente,
    :municipio_emitente, :cnpj_destinatario, :nome_destinatario, :uf_destinatario,
    :indicador_ie_destinatario, :destino_operacao, :consumidor_final, :presenca_comprador,
    :numero_produto, :descricao_produto, :codigo_ncm_sh, :ncm_sh_tipo_produto, :cfop,
    :quantidade, :unidade, :valor_unitario, :valor_total
);

-- name: get_database_stats^
SELECT 
    (SELECT COUNT(*) FROM notasfiscais) as notas_fiscais,
    (SELECT COUNT(*) FROM itensnotafiscal) as itens_nota_fiscal,
    (SELECT SUM(valor_nota_fiscal) FROM notasfiscais) as total_value,
    (SELECT MAX(data_emissao) FROM notasfiscais) as last_upload
;
"""

queries = aiosql.from_str(SQL_QUERIES, "asyncpg")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@db:{DB_PORT}/{DB_NAME}"
ADMIN_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@db:{DB_PORT}/postgres" # Connect to a default db for creating the target db

def parse_date(date_str):
    if not date_str: return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None

def parse_datetime(datetime_str):
    if not datetime_str: return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue
    return None

def parse_decimal(value_str, default=0.0):
    if not value_str: return default
    try:
        return float(str(value_str).replace(',', '.')) # Handle comma as decimal separator
    except ValueError:
        return default

def parse_int(value_str, default=0):
    if not value_str: return default
    try:
        return int(value_str)
    except ValueError:
        return default

async def create_db_and_tables():
    # Try to create the database itself. This requires connecting to a default database like 'postgres'.
    conn_admin = None
    try:
        conn_admin = await asyncpg.connect(ADMIN_DATABASE_URL)
        # Check if database exists
        db_exists = await conn_admin.fetchval(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        if not db_exists:
            print(f"Database {DB_NAME} does not exist. Attempting to create...")
            await conn_admin.execute(f"CREATE DATABASE \"{DB_NAME}\"") # Use escaped quotes for db name
            print(f"Database {DB_NAME} created successfully or already existed.")
        else:
            print(f"Database {DB_NAME} already exists.")
    except asyncpg.exceptions.DuplicateDatabaseError:
        print(f"Database {DB_NAME} already exists.")
    except Exception as e:
        print(f"Could not create or connect to admin database to create {DB_NAME}: {e}")
        print("Please ensure the database {DB_NAME} exists and the user has connection rights.")
        # Potentially re-raise or handle as a critical failure if DB creation is mandatory here
    finally:
        if conn_admin:
            await conn_admin.close()

    # Connect to the target database to create tables
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await queries.drop_tables(conn) # Drop tables if they exist to start fresh
        await queries.create_notasfiscais_table(conn)
        await queries.create_itensnotafiscal_table(conn)
        print("Tables 'notasfiscais' and 'itensnotafiscal' created successfully.")
    except Exception as e:
        print(f"Error creating tables: {e}")
        raise # Re-raise the exception to be caught by the endpoint handler
    finally:
        if conn:
            await conn.close()

async def load_data_from_csv(cabecalho_path: str, itens_path: str):
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Load notasfiscais (cabecalho)
        with open(cabecalho_path, mode='r', encoding='utf-8-sig') as csvfile: # utf-8-sig to handle BOM
            reader = csv.reader(csvfile, delimiter=',')
            next(reader)  # Skip header row
            nf_data = []
            for row in reader:
                if len(row) < 21:  # Ensure we have enough columns
                    continue
                # Use column positions based on the CSV structure
                # 0=CHAVE DE ACESSO, 1=MODELO, 2=SÉRIE, 3=NÚMERO, 4=NATUREZA DA OPERAÇÃO, 5=DATA EMISSÃO
                # 6=EVENTO MAIS RECENTE, 7=DATA/HORA EVENTO MAIS RECENTE, 8=CPF/CNPJ Emitente, 9=RAZÃO SOCIAL EMITENTE
                # 10=INSCRIÇÃO ESTADUAL EMITENTE, 11=UF EMITENTE, 12=MUNICÍPIO EMITENTE, 13=CNPJ DESTINATÁRIO
                # 14=NOME DESTINATÁRIO, 15=UF DESTINATÁRIO, 16=INDICADOR IE DESTINATÁRIO, 17=DESTINO DA OPERAÇÃO
                # 18=CONSUMIDOR FINAL, 19=PRESENÇA DO COMPRADOR, 20=VALOR NOTA FISCAL
                nf_data.append({
                    'chave_acesso': row[0] if len(row) > 0 else None,
                    'modelo': row[1] if len(row) > 1 else None,
                    'serie_nf': row[2] if len(row) > 2 else None,
                    'numero_nf': row[3] if len(row) > 3 else None,
                    'natureza_operacao': row[4] if len(row) > 4 else None,
                    'data_emissao': parse_date(row[5]) if len(row) > 5 else None,
                    'evento_mais_recente': row[6] if len(row) > 6 else None,
                    'data_hora_evento_mais_recente': parse_datetime(row[7]) if len(row) > 7 else None,
                    'cpf_cnpj_emitente': row[8] if len(row) > 8 else None,
                    'razao_social_emitente': row[9] if len(row) > 9 else None,
                    'inscricao_estadual_emitente': row[10] if len(row) > 10 else None,
                    'uf_emitente': row[11] if len(row) > 11 else None,
                    'municipio_emitente': row[12] if len(row) > 12 else None,
                    'cnpj_destinatario': row[13] if len(row) > 13 else None,
                    'nome_destinatario': row[14] if len(row) > 14 else None,
                    'uf_destinatario': row[15] if len(row) > 15 else None,
                    'indicador_ie_destinatario': row[16] if len(row) > 16 else None,
                    'destino_operacao': row[17] if len(row) > 17 else None,
                    'consumidor_final': row[18] if len(row) > 18 else None,
                    'presenca_comprador': row[19] if len(row) > 19 else None,
                    'valor_nota_fiscal': parse_decimal(row[20]) if len(row) > 20 else None
                })
            # Filter out rows where chave_acesso is None or empty, as it's a PRIMARY KEY
            nf_data_valid = [r for r in nf_data if r['chave_acesso']]
            if nf_data_valid:
                insert_sql = """
                INSERT INTO notasfiscais (
                    chave_acesso, modelo, serie_nf, numero_nf, natureza_operacao, data_emissao,
                    evento_mais_recente, data_hora_evento_mais_recente, cpf_cnpj_emitente, razao_social_emitente,
                    inscricao_estadual_emitente, uf_emitente, municipio_emitente, cnpj_destinatario,
                    nome_destinatario, uf_destinatario, indicador_ie_destinatario, destino_operacao,
                    consumidor_final, presenca_comprador, valor_nota_fiscal
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
                )
                ON CONFLICT (chave_acesso) DO NOTHING;
                """
                for nf_record in nf_data_valid:
                    await conn.execute(insert_sql, 
                        nf_record['chave_acesso'], nf_record['modelo'], nf_record['serie_nf'], 
                        nf_record['numero_nf'], nf_record['natureza_operacao'], nf_record['data_emissao'],
                        nf_record['evento_mais_recente'], nf_record['data_hora_evento_mais_recente'], 
                        nf_record['cpf_cnpj_emitente'], nf_record['razao_social_emitente'],
                        nf_record['inscricao_estadual_emitente'], nf_record['uf_emitente'], 
                        nf_record['municipio_emitente'], nf_record['cnpj_destinatario'],
                        nf_record['nome_destinatario'], nf_record['uf_destinatario'], 
                        nf_record['indicador_ie_destinatario'], nf_record['destino_operacao'],
                        nf_record['consumidor_final'], nf_record['presenca_comprador'], 
                        nf_record['valor_nota_fiscal']
                    )
            print(f"Loaded {len(nf_data_valid)} records into notasfiscais.")

        # Load itensnotafiscal
        with open(itens_path, mode='r', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            next(reader)  # Skip header row
            item_data = []
            for row in reader:
                if len(row) < 27:  # Ensure we have enough columns
                    continue
                # Use column positions based on the CSV structure
                # 0=CHAVE DE ACESSO, 1=MODELO, 2=SÉRIE, 3=NÚMERO, 4=NATUREZA DA OPERAÇÃO, 5=DATA EMISSÃO
                # 6=CPF/CNPJ Emitente, 7=RAZÃO SOCIAL EMITENTE, 8=INSCRIÇÃO ESTADUAL EMITENTE, 9=UF EMITENTE
                # 10=MUNICÍPIO EMITENTE, 11=CNPJ DESTINATÁRIO, 12=NOME DESTINATÁRIO, 13=UF DESTINATÁRIO
                # 14=INDICADOR IE DESTINATÁRIO, 15=DESTINO DA OPERAÇÃO, 16=CONSUMIDOR FINAL, 17=PRESENÇA DO COMPRADOR
                # 18=NÚMERO PRODUTO, 19=DESCRIÇÃO DO PRODUTO/SERVIÇO, 20=CÓDIGO NCM/SH, 21=NCM/SH (TIPO DE PRODUTO)
                # 22=CFOP, 23=QUANTIDADE, 24=UNIDADE, 25=VALOR UNITÁRIO, 26=VALOR TOTAL
                item_data.append({
                    'chave_acesso_nf': row[0] if len(row) > 0 else None,
                    'modelo': row[1] if len(row) > 1 else None,
                    'serie_nf': row[2] if len(row) > 2 else None,
                    'numero_nf': row[3] if len(row) > 3 else None,
                    'natureza_operacao': row[4] if len(row) > 4 else None,
                    'data_emissao': parse_date(row[5]) if len(row) > 5 else None,
                    'cpf_cnpj_emitente': row[6] if len(row) > 6 else None,
                    'razao_social_emitente': row[7] if len(row) > 7 else None,
                    'inscricao_estadual_emitente': row[8] if len(row) > 8 else None,
                    'uf_emitente': row[9] if len(row) > 9 else None,
                    'municipio_emitente': row[10] if len(row) > 10 else None,
                    'cnpj_destinatario': row[11] if len(row) > 11 else None,
                    'nome_destinatario': row[12] if len(row) > 12 else None,
                    'uf_destinatario': row[13] if len(row) > 13 else None,
                    'indicador_ie_destinatario': row[14] if len(row) > 14 else None,
                    'destino_operacao': row[15] if len(row) > 15 else None,
                    'consumidor_final': row[16] if len(row) > 16 else None,
                    'presenca_comprador': row[17] if len(row) > 17 else None,
                    'numero_produto': parse_int(row[18]) if len(row) > 18 else None,
                    'descricao_produto': row[19] if len(row) > 19 else None,
                    'codigo_ncm_sh': row[20] if len(row) > 20 else None,
                    'ncm_sh_tipo_produto': row[21] if len(row) > 21 else None,
                    'cfop': row[22] if len(row) > 22 else None,
                    'quantidade': parse_decimal(row[23]) if len(row) > 23 else None,
                    'unidade': row[24] if len(row) > 24 else None,
                    'valor_unitario': parse_decimal(row[25]) if len(row) > 25 else None,
                    'valor_total': parse_decimal(row[26]) if len(row) > 26 else None
                })
            # Filter out rows where chave_acesso_nf is None or empty
            item_data_valid = [r for r in item_data if r['chave_acesso_nf']]
            if item_data_valid:
                insert_sql = """
                INSERT INTO itensnotafiscal (
                    chave_acesso_nf, modelo, serie_nf, numero_nf, natureza_operacao, data_emissao,
                    cpf_cnpj_emitente, razao_social_emitente, inscricao_estadual_emitente, uf_emitente,
                    municipio_emitente, cnpj_destinatario, nome_destinatario, uf_destinatario,
                    indicador_ie_destinatario, destino_operacao, consumidor_final, presenca_comprador,
                    numero_produto, descricao_produto, codigo_ncm_sh, ncm_sh_tipo_produto, cfop,
                    quantidade, unidade, valor_unitario, valor_total
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27
                );
                """
                for item_record in item_data_valid:
                    await conn.execute(insert_sql,
                        item_record['chave_acesso_nf'], item_record['modelo'], item_record['serie_nf'],
                        item_record['numero_nf'], item_record['natureza_operacao'], item_record['data_emissao'],
                        item_record['cpf_cnpj_emitente'], item_record['razao_social_emitente'],
                        item_record['inscricao_estadual_emitente'], item_record['uf_emitente'],
                        item_record['municipio_emitente'], item_record['cnpj_destinatario'],
                        item_record['nome_destinatario'], item_record['uf_destinatario'],
                        item_record['indicador_ie_destinatario'], item_record['destino_operacao'],
                        item_record['consumidor_final'], item_record['presenca_comprador'],
                        item_record['numero_produto'], item_record['descricao_produto'],
                        item_record['codigo_ncm_sh'], item_record['ncm_sh_tipo_produto'],
                        item_record['cfop'], item_record['quantidade'], item_record['unidade'],
                        item_record['valor_unitario'], item_record['valor_total']
                    )
            print(f"Loaded {len(item_data_valid)} records into itensnotafiscal.")

    except FileNotFoundError as e:
        print(f"Error: CSV file not found - {e}")
        raise
    except Exception as e:
        print(f"Error loading data from CSV: {e}")
        raise # Re-raise for endpoint to handle
    finally:
        if conn:
            await conn.close()

async def get_database_statistics():
    """Get database statistics for status reporting"""
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        stats = await queries.get_database_stats(conn)
        
        if stats:
            return {
                "notas_fiscais": stats["notas_fiscais"] or 0,
                "itens_nota_fiscal": stats["itens_nota_fiscal"] or 0,
                "total_records": (stats["notas_fiscais"] or 0) + (stats["itens_nota_fiscal"] or 0),
                "total_value": float(stats["total_value"]) if stats["total_value"] else 0.0,
                "last_upload": stats["last_upload"].isoformat() if stats["last_upload"] else None
            }
        else:
            return {
                "notas_fiscais": 0,
                "itens_nota_fiscal": 0,
                "total_records": 0,
                "total_value": 0.0,
                "last_upload": None
            }
    except Exception as e:
        print(f"Error getting database statistics: {e}")
        return {
            "notas_fiscais": 0,
            "itens_nota_fiscal": 0,
            "total_records": 0,
            "total_value": 0.0,
            "last_upload": None
        }
    finally:
        if conn:
            await conn.close() 