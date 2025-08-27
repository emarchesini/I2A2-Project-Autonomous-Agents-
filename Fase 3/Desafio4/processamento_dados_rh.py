#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROCESSADOR DE DADOS DE RH - DESAFIO 4
======================================

Este módulo foi desenvolvido para processar os dados de RH contidos nas planilhas Excel
do Desafio 4. O processamento é realizado por etapas com logging detalhado para
acompanhamento da execução.

Autor: Sistema de Processamento de Dados
Data: 2025
Versão: 1.0

FUNCIONALIDADES:
- Carregamento de múltiplas planilhas Excel
- Análise exploratória dos dados
- Processamento e transformação dos dados
- Consolidação de dados de diferentes fontes
- Geração de planilha consolidada final
- Logging detalhado de todas as operações

ARQUIVOS PROCESSADOS:
- ADMISSÃO ABRIL.xlsx - Dados de admissões em abril
- AFASTAMENTOS.xlsx - Registros de afastamentos
- APRENDIZ.xlsx - Dados de aprendizes
- ATIVOS.xlsx - Funcionários ativos
- Base dias uteis.xlsx - Calendário de dias úteis
- Base sindicato x valor.xlsx - Valores por sindicato
- DESLIGADOS.xlsx - Funcionários desligados
- ESTÁGIO.xlsx - Dados de estagiários
- EXTERIOR.xlsx - Funcionários no exterior
- FÉRIAS.xlsx - Registros de férias
- VR MENSAL 05.2025.xlsx - Vale refeição mensal
"""

import pandas as pd
import numpy as np
import os
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
import warnings
import traceback
from typing import Dict, List, Any, Optional, Tuple

# Configuração de warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

class ProcessadorDadosRH:
    """
    Classe principal para processamento de dados de RH.
    
    Esta classe encapsula todas as funcionalidades necessárias para:
    - Carregar dados de planilhas Excel
    - Processar e transformar os dados
    - Gerar análises e relatórios
    - Manter logs detalhados das operações
    """
    
    def __init__(self, diretorio_dados: str = "Desafio 4 - Dados", para_api: bool = False):
        """
        Inicializa o processador de dados de RH.
        
        Args:
            diretorio_dados (str): Caminho para o diretório contendo as planilhas Excel
            para_api (bool): Se True, configura logging para API (apenas console)
        """
        self.diretorio_dados = Path(diretorio_dados)
        self.dataframes = {}
        self.metadados = {}
        self.resultados_processamento = {}
        self.para_api = para_api
        
        # Configuração do logging
        if para_api:
            self._configurar_logging_para_api()
        else:
            self._configurar_logging()
        
        # Lista de arquivos esperados
        self.arquivos_esperados = [
            "ADMISSÃO ABRIL.xlsx",
            "AFASTAMENTOS.xlsx", 
            "APRENDIZ.xlsx",
            "ATIVOS.xlsx",
            "Base dias uteis.xlsx",
            "Base sindicato x valor.xlsx",
            "DESLIGADOS.xlsx",
            "ESTÁGIO.xlsx",
            "EXTERIOR.xlsx",
            "FÉRIAS.xlsx",
            "VR MENSAL 05.2025.xlsx"
        ]
        
        self.logger.info("=" * 80)
        self.logger.info("PROCESSADOR DE DADOS DE RH - DESAFIO 4")
        self.logger.info("=" * 80)
        self.logger.info(f"Diretório de dados: {self.diretorio_dados.absolute()}")
        self.logger.info(f"Inicializado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def _configurar_logging(self):
        """
        Configura o sistema de logging para acompanhamento detalhado da execução.
        """
        # Criar diretório de logs se não existir
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Nome do arquivo de log com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"processamento_rh_{timestamp}.log"
        
        # Configuração do logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Sistema de logging configurado. Arquivo: {log_file}")
    
    def verificar_arquivos(self) -> bool:
        """
        Verifica se todos os arquivos esperados existem no diretório.
        
        Returns:
            bool: True se todos os arquivos existem, False caso contrário
        """
        self.logger.info("\n" + "=" * 50)
        self.logger.info("ETAPA 1: VERIFICAÇÃO DE ARQUIVOS")
        self.logger.info("=" * 50)
        
        arquivos_encontrados = []
        arquivos_ausentes = []
        
        for arquivo in self.arquivos_esperados:
            caminho_arquivo = self.diretorio_dados / arquivo
            if caminho_arquivo.exists():
                arquivos_encontrados.append(arquivo)
                self.logger.info(f"✓ Arquivo encontrado: {arquivo}")
            else:
                arquivos_ausentes.append(arquivo)
                self.logger.warning(f"✗ Arquivo ausente: {arquivo}")
        
        self.logger.info(f"\nResumo da verificação:")
        self.logger.info(f"  - Arquivos encontrados: {len(arquivos_encontrados)}")
        self.logger.info(f"  - Arquivos ausentes: {len(arquivos_ausentes)}")
        
        if arquivos_ausentes:
            self.logger.warning(f"  - Lista de arquivos ausentes: {arquivos_ausentes}")
            return False
        
        self.logger.info("✓ Todos os arquivos necessários foram encontrados!")
        return True
    
    def carregar_planilhas(self) -> bool:
        """
        Carrega todas as planilhas Excel em DataFrames do pandas.
        
        Returns:
            bool: True se o carregamento foi bem-sucedido, False caso contrário
        """
        self.logger.info("\n" + "=" * 50)
        self.logger.info("ETAPA 2: CARREGAMENTO DAS PLANILHAS")
        self.logger.info("=" * 50)
        
        sucesso_total = True
        
        for arquivo in self.arquivos_esperados:
            caminho_arquivo = self.diretorio_dados / arquivo
            
            if not caminho_arquivo.exists():
                self.logger.warning(f"Pulando arquivo ausente: {arquivo}")
                continue
            
            try:
                self.logger.info(f"Carregando: {arquivo}")
                
                # Tentar carregar com diferentes engines
                try:
                    df = pd.read_excel(caminho_arquivo, engine='openpyxl')
                except Exception:
                    try:
                        df = pd.read_excel(caminho_arquivo, engine='xlrd')
                    except Exception:
                        df = pd.read_excel(caminho_arquivo)
                
                # Armazenar DataFrame e metadados
                nome_limpo = arquivo.replace('.xlsx', '').upper()
                self.dataframes[nome_limpo] = df
                
                # Coletar metadados
                self.metadados[nome_limpo] = {
                    'arquivo_original': arquivo,
                    'linhas': len(df),
                    'colunas': len(df.columns),
                    'colunas_nomes': list(df.columns),
                    'tipos_dados': df.dtypes.to_dict(),
                    'valores_nulos': df.isnull().sum().to_dict(),
                    'tamanho_memoria': df.memory_usage(deep=True).sum(),
                    'carregado_em': datetime.now()
                }
                
                self.logger.info(f"  ✓ Sucesso - {len(df)} linhas, {len(df.columns)} colunas")
                self.logger.info(f"    Colunas: {list(df.columns)}")
                
            except Exception as e:
                self.logger.error(f"  ✗ Erro ao carregar {arquivo}: {str(e)}")
                self.logger.error(f"    Detalhes: {traceback.format_exc()}")
                sucesso_total = False
        
        self.logger.info(f"\nResumo do carregamento:")
        self.logger.info(f"  - Planilhas carregadas: {len(self.dataframes)}")
        
        total_linhas = sum(meta['linhas'] for meta in self.metadados.values())
        total_colunas = sum(meta['colunas'] for meta in self.metadados.values())
        
        self.logger.info(f"  - Total de linhas: {total_linhas:,}")
        self.logger.info(f"  - Total de colunas: {total_colunas}")
        
        return sucesso_total
    
    def analisar_estrutura_dados(self):
        """
        Realiza análise exploratória detalhada dos dados carregados.
        """
        self.logger.info("\n" + "=" * 50)
        self.logger.info("ETAPA 3: ANÁLISE ESTRUTURAL DOS DADOS")
        self.logger.info("=" * 50)
        
        for nome, df in self.dataframes.items():
            self.logger.info(f"\n{'=' * 30}")
            self.logger.info(f"ANÁLISE: {nome}")
            self.logger.info(f"{'=' * 30}")
            
            # Informações básicas
            self.logger.info(f"Dimensões: {df.shape[0]} linhas x {df.shape[1]} colunas")
            self.logger.info(f"Memória utilizada: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
            
            # Análise de colunas
            self.logger.info(f"\nColunas ({len(df.columns)}):")
            for i, col in enumerate(df.columns, 1):
                tipo = df[col].dtype
                nulos = df[col].isnull().sum()
                pct_nulos = (nulos / len(df)) * 100 if len(df) > 0 else 0
                
                self.logger.info(f"  {i:2d}. {col} ({tipo}) - {nulos} nulos ({pct_nulos:.1f}%)")
            
            # Análise de valores únicos em colunas categóricas
            colunas_categoricas = df.select_dtypes(include=['object']).columns
            if len(colunas_categoricas) > 0:
                self.logger.info(f"\nAnálise de colunas categóricas:")
                for col in colunas_categoricas[:5]:  # Limitar a 5 colunas
                    valores_unicos = df[col].nunique()
                    self.logger.info(f"  {col}: {valores_unicos} valores únicos")
                    
                    if valores_unicos <= 10:  # Mostrar valores se poucos
                        valores = df[col].value_counts().head()
                        self.logger.info(f"    Top valores: {dict(valores)}")
            
            # Análise de colunas numéricas
            colunas_numericas = df.select_dtypes(include=[np.number]).columns
            if len(colunas_numericas) > 0:
                self.logger.info(f"\nEstatísticas de colunas numéricas:")
                stats = df[colunas_numericas].describe()
                for col in colunas_numericas[:3]:  # Limitar a 3 colunas
                    self.logger.info(f"  {col}:")
                    self.logger.info(f"    Min: {stats.loc['min', col]:.2f}")
                    self.logger.info(f"    Max: {stats.loc['max', col]:.2f}")
                    self.logger.info(f"    Média: {stats.loc['mean', col]:.2f}")
            
            # Identificar possíveis chaves primárias
            self.logger.info(f"\nAnálise de chaves potenciais:")
            for col in df.columns:
                if df[col].nunique() == len(df) and df[col].nunique() > 1:
                    self.logger.info(f"  {col}: Possível chave primária (100% únicos)")
                elif df[col].nunique() / len(df) > 0.95:
                    pct_unicos = (df[col].nunique() / len(df)) * 100
                    self.logger.info(f"  {col}: Alta unicidade ({pct_unicos:.1f}%)")
    
    def processar_dados_funcionarios(self):
        """
        Processa especificamente os dados relacionados a funcionários.
        """
        self.logger.info("\n" + "=" * 50)
        self.logger.info("ETAPA 4: PROCESSAMENTO DE DADOS DE FUNCIONÁRIOS")
        self.logger.info("=" * 50)
        
        # Identificar datasets com dados de funcionários
        datasets_funcionarios = []
        
        for nome, df in self.dataframes.items():
            # Procurar colunas que indicam dados de funcionários
            colunas_funcionario = ['cpf', 'matricula', 'nome', 'funcionario', 'empregado', 'colaborador']
            tem_dados_funcionario = any(
                any(palavra in col.lower() for palavra in colunas_funcionario)
                for col in df.columns
            )
            
            if tem_dados_funcionario:
                datasets_funcionarios.append(nome)
                self.logger.info(f"✓ Dataset com dados de funcionários: {nome}")
        
        if not datasets_funcionarios:
            self.logger.warning("Nenhum dataset com dados de funcionários identificado")
            return
        
        # Analisar cada dataset de funcionários
        for nome in datasets_funcionarios:
            df = self.dataframes[nome]
            self.logger.info(f"\nProcessando dataset: {nome}")
            
            # Identificar colunas de identificação
            colunas_id = []
            for col in df.columns:
                col_lower = col.lower()
                if any(palavra in col_lower for palavra in ['cpf', 'matricula', 'codigo', 'id']):
                    colunas_id.append(col)
            
            if colunas_id:
                self.logger.info(f"  Colunas de identificação: {colunas_id}")
                
                # Verificar duplicatas
                for col in colunas_id:
                    duplicatas = df[col].duplicated().sum()
                    if duplicatas > 0:
                        self.logger.warning(f"    {col}: {duplicatas} valores duplicados")
                    else:
                        self.logger.info(f"    {col}: Sem duplicatas")
            
            # Analisar dados demográficos se disponíveis
            colunas_demograficas = []
            for col in df.columns:
                col_lower = col.lower()
                if any(palavra in col_lower for palavra in ['idade', 'sexo', 'genero', 'nascimento', 'cargo', 'departamento', 'setor']):
                    colunas_demograficas.append(col)
            
            if colunas_demograficas:
                self.logger.info(f"  Colunas demográficas: {colunas_demograficas}")
                
                for col in colunas_demograficas:
                    if df[col].dtype == 'object':
                        valores = df[col].value_counts().head()
                        self.logger.info(f"    {col}: {dict(valores)}")
    
    def processar_dados_temporais(self):
        """
        Processa dados relacionados a datas e períodos.
        """
        self.logger.info("\n" + "=" * 50)
        self.logger.info("ETAPA 5: PROCESSAMENTO DE DADOS TEMPORAIS")
        self.logger.info("=" * 50)
        
        for nome, df in self.dataframes.items():
            # Identificar colunas de data
            colunas_data = []
            for col in df.columns:
                col_lower = col.lower()
                if any(palavra in col_lower for palavra in ['data', 'inicio', 'fim', 'periodo', 'mes', 'ano', 'admissao', 'desligamento']):
                    # Verificar se realmente contém datas
                    amostra = df[col].dropna().head(10)
                    if len(amostra) > 0:
                        try:
                            pd.to_datetime(amostra.iloc[0])
                            colunas_data.append(col)
                        except:
                            # Pode ser string representando data
                            if any(str(val).replace('/', '').replace('-', '').isdigit() for val in amostra):
                                colunas_data.append(col)
            
            if colunas_data:
                self.logger.info(f"\nDataset {nome} - Colunas temporais: {colunas_data}")
                
                for col in colunas_data:
                    try:
                        # Tentar converter para datetime
                        datas_convertidas = pd.to_datetime(df[col], errors='coerce')
                        data_min = datas_convertidas.min()
                        data_max = datas_convertidas.max()
                        
                        if pd.notna(data_min) and pd.notna(data_max):
                            self.logger.info(f"  {col}: {data_min.date()} até {data_max.date()}")
                            
                            # Analisar distribuição por ano/mês
                            if len(datas_convertidas.dropna()) > 0:
                                anos = datas_convertidas.dt.year.value_counts().sort_index()
                                self.logger.info(f"    Distribuição por ano: {dict(anos.head())}")
                    
                    except Exception as e:
                        self.logger.warning(f"  Erro ao processar {col}: {str(e)}")
    
    def gerar_relatorio_consolidado(self):
        """
        Gera um relatório consolidado dos dados processados.
        """
        self.logger.info("\n" + "=" * 50)
        self.logger.info("ETAPA 6: RELATÓRIO CONSOLIDADO")
        self.logger.info("=" * 50)
        
        total_registros = sum(len(df) for df in self.dataframes.values())
        total_colunas = sum(len(df.columns) for df in self.dataframes.values())
        
        self.logger.info(f"\nRESUMO GERAL:")
        self.logger.info(f"  - Total de datasets: {len(self.dataframes)}")
        self.logger.info(f"  - Total de registros: {total_registros:,}")
        self.logger.info(f"  - Total de colunas: {total_colunas}")
        
        # Resumo por dataset
        self.logger.info(f"\nRESUMO POR DATASET:")
        for nome, df in self.dataframes.items():
            self.logger.info(f"  {nome}:")
            self.logger.info(f"    - Registros: {len(df):,}")
            self.logger.info(f"    - Colunas: {len(df.columns)}")
            self.logger.info(f"    - Completude: {((1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100):.1f}%")
        
        # Identificar possíveis relacionamentos
        self.logger.info(f"\nANÁLISE DE RELACIONAMENTOS:")
        datasets = list(self.dataframes.keys())
        
        for i, dataset1 in enumerate(datasets):
            for dataset2 in datasets[i+1:]:
                df1 = self.dataframes[dataset1]
                df2 = self.dataframes[dataset2]
                
                # Procurar colunas em comum
                colunas_comuns = set(df1.columns) & set(df2.columns)
                if colunas_comuns:
                    self.logger.info(f"  {dataset1} ↔ {dataset2}:")
                    self.logger.info(f"    Colunas em comum: {list(colunas_comuns)}")
    
    def salvar_resultados(self):
        """
        Salva os resultados do processamento em arquivos.
        """
        self.logger.info("\n" + "=" * 50)
        self.logger.info("ETAPA 7: SALVANDO RESULTADOS")
        self.logger.info("=" * 50)
        
        # Criar diretório de resultados
        resultado_dir = Path("resultados_processamento")
        resultado_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Salvar metadados
        metadados_file = resultado_dir / f"metadados_{timestamp}.txt"
        with open(metadados_file, 'w', encoding='utf-8') as f:
            f.write("METADADOS DOS DATASETS PROCESSADOS\n")
            f.write("=" * 50 + "\n\n")
            
            for nome, meta in self.metadados.items():
                f.write(f"DATASET: {nome}\n")
                f.write(f"Arquivo original: {meta['arquivo_original']}\n")
                f.write(f"Dimensões: {meta['linhas']} x {meta['colunas']}\n")
                f.write(f"Colunas: {', '.join(meta['colunas_nomes'])}\n")
                f.write(f"Processado em: {meta['carregado_em']}\n")
                f.write("-" * 30 + "\n\n")
        
        self.logger.info(f"✓ Metadados salvos em: {metadados_file}")
        
        # Salvar datasets processados (opcional - apenas amostras)
        for nome, df in self.dataframes.items():
            if len(df) > 0:
                amostra_file = resultado_dir / f"amostra_{nome}_{timestamp}.csv"
                amostra = df.head(100)  # Primeiras 100 linhas
                amostra.to_csv(amostra_file, index=False, encoding='utf-8')
                self.logger.info(f"✓ Amostra de {nome} salva em: {amostra_file}")
    
    def gerar_planilha_consolidada(self, caminho_arquivo: str):
        """
        Gera uma planilha Excel consolidada com todos os dados processados.
        
        Args:
            caminho_arquivo (str): Caminho onde salvar a planilha consolidada
        """
        self.logger.info("\n" + "=" * 50)
        self.logger.info("GERANDO PLANILHA CONSOLIDADA")
        self.logger.info("=" * 50)
        
        try:
            with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
                
                # Aba com resumo geral
                self._criar_aba_resumo(writer)
                
                # Aba com funcionários ativos consolidados
                self._criar_aba_funcionarios_ativos(writer)
                
                # Aba com movimentações (admissões, desligamentos)
                self._criar_aba_movimentacoes(writer)
                
                # Aba com afastamentos e férias
                self._criar_aba_afastamentos_ferias(writer)
                
                # Aba com dados financeiros (VR, sindicato)
                self._criar_aba_dados_financeiros(writer)
                
                # Abas individuais com dados originais (limitados)
                for nome, df in self.dataframes.items():
                    if len(df) > 0:
                        # Limitar a 1000 linhas para não sobrecarregar
                        df_limitado = df.head(1000)
                        nome_aba = nome[:31]  # Excel limita nomes de aba a 31 caracteres
                        df_limitado.to_excel(writer, sheet_name=nome_aba, index=False)
                        self.logger.info(f"  ✓ Aba '{nome_aba}' criada com {len(df_limitado)} registros")
            
            self.logger.info(f"✓ Planilha consolidada salva em: {caminho_arquivo}")
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar planilha consolidada: {str(e)}")
            raise
    
    def _criar_aba_resumo(self, writer):
        """Cria aba com resumo geral dos dados."""
        resumo_data = []
        
        # Informações gerais
        resumo_data.append(['RESUMO GERAL DOS DADOS DE RH', ''])
        resumo_data.append(['Data do Processamento', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        resumo_data.append(['', ''])
        
        # Estatísticas por dataset
        resumo_data.append(['ESTATÍSTICAS POR DATASET', ''])
        resumo_data.append(['Dataset', 'Registros'])
        
        for nome, df in self.dataframes.items():
            resumo_data.append([nome, len(df)])
        
        resumo_data.append(['', ''])
        resumo_data.append(['TOTAL GERAL', sum(len(df) for df in self.dataframes.values())])
        
        # Criar DataFrame e salvar
        df_resumo = pd.DataFrame(resumo_data, columns=['Descrição', 'Valor'])
        df_resumo.to_excel(writer, sheet_name='RESUMO', index=False)
        self.logger.info("  ✓ Aba 'RESUMO' criada")
    
    def _criar_aba_funcionarios_ativos(self, writer):
        """Cria aba consolidada com funcionários ativos."""
        funcionarios_datasets = []
        
        # Identificar datasets com funcionários
        for nome in ['ATIVOS', 'APRENDIZ', 'ESTÁGIO', 'EXTERIOR']:
            if nome in self.dataframes:
                df = self.dataframes[nome].copy()
                df['ORIGEM'] = nome
                funcionarios_datasets.append(df)
        
        if funcionarios_datasets:
            df_consolidado = pd.concat(funcionarios_datasets, ignore_index=True, sort=False)
            df_consolidado.to_excel(writer, sheet_name='FUNCIONARIOS_ATIVOS', index=False)
            self.logger.info(f"  ✓ Aba 'FUNCIONARIOS_ATIVOS' criada com {len(df_consolidado)} registros")
        else:
            # Criar aba vazia se não houver dados
            pd.DataFrame({'MENSAGEM': ['Nenhum dado de funcionários ativos encontrado']}).to_excel(
                writer, sheet_name='FUNCIONARIOS_ATIVOS', index=False)
            self.logger.info("  ✓ Aba 'FUNCIONARIOS_ATIVOS' criada (vazia)")
    
    def _criar_aba_movimentacoes(self, writer):
        """Cria aba com movimentações (admissões e desligamentos)."""
        movimentacoes_datasets = []
        
        # Admissões
        if 'ADMISSÃO ABRIL' in self.dataframes:
            df = self.dataframes['ADMISSÃO ABRIL'].copy()
            df['TIPO_MOVIMENTACAO'] = 'ADMISSÃO'
            movimentacoes_datasets.append(df)
        
        # Desligamentos
        if 'DESLIGADOS' in self.dataframes:
            df = self.dataframes['DESLIGADOS'].copy()
            df['TIPO_MOVIMENTACAO'] = 'DESLIGAMENTO'
            movimentacoes_datasets.append(df)
        
        if movimentacoes_datasets:
            df_consolidado = pd.concat(movimentacoes_datasets, ignore_index=True, sort=False)
            df_consolidado.to_excel(writer, sheet_name='MOVIMENTACOES', index=False)
            self.logger.info(f"  ✓ Aba 'MOVIMENTACOES' criada com {len(df_consolidado)} registros")
        else:
            pd.DataFrame({'MENSAGEM': ['Nenhum dado de movimentação encontrado']}).to_excel(
                writer, sheet_name='MOVIMENTACOES', index=False)
            self.logger.info("  ✓ Aba 'MOVIMENTACOES' criada (vazia)")
    
    def _criar_aba_afastamentos_ferias(self, writer):
        """Cria aba com afastamentos e férias."""
        ausencias_datasets = []
        
        # Afastamentos
        if 'AFASTAMENTOS' in self.dataframes:
            df = self.dataframes['AFASTAMENTOS'].copy()
            df['TIPO_AUSENCIA'] = 'AFASTAMENTO'
            ausencias_datasets.append(df)
        
        # Férias
        if 'FÉRIAS' in self.dataframes:
            df = self.dataframes['FÉRIAS'].copy()
            df['TIPO_AUSENCIA'] = 'FÉRIAS'
            ausencias_datasets.append(df)
        
        if ausencias_datasets:
            df_consolidado = pd.concat(ausencias_datasets, ignore_index=True, sort=False)
            df_consolidado.to_excel(writer, sheet_name='AFASTAMENTOS_FERIAS', index=False)
            self.logger.info(f"  ✓ Aba 'AFASTAMENTOS_FERIAS' criada com {len(df_consolidado)} registros")
        else:
            pd.DataFrame({'MENSAGEM': ['Nenhum dado de ausências encontrado']}).to_excel(
                writer, sheet_name='AFASTAMENTOS_FERIAS', index=False)
            self.logger.info("  ✓ Aba 'AFASTAMENTOS_FERIAS' criada (vazia)")
    
    def _criar_aba_dados_financeiros(self, writer):
        """Cria aba com dados financeiros."""
        financeiros_datasets = []
        
        # Vale Refeição
        if 'VR MENSAL 05.2025' in self.dataframes:
            df = self.dataframes['VR MENSAL 05.2025'].copy()
            df['TIPO_FINANCEIRO'] = 'VALE_REFEICAO'
            financeiros_datasets.append(df)
        
        # Base sindicato
        if 'BASE SINDICATO X VALOR' in self.dataframes:
            df = self.dataframes['BASE SINDICATO X VALOR'].copy()
            df['TIPO_FINANCEIRO'] = 'SINDICATO'
            financeiros_datasets.append(df)
        
        if financeiros_datasets:
            df_consolidado = pd.concat(financeiros_datasets, ignore_index=True, sort=False)
            df_consolidado.to_excel(writer, sheet_name='DADOS_FINANCEIROS', index=False)
            self.logger.info(f"  ✓ Aba 'DADOS_FINANCEIROS' criada com {len(df_consolidado)} registros")
        else:
            pd.DataFrame({'MENSAGEM': ['Nenhum dado financeiro encontrado']}).to_excel(
                writer, sheet_name='DADOS_FINANCEIROS', index=False)
            self.logger.info("  ✓ Aba 'DADOS_FINANCEIROS' criada (vazia)")
    
    def _configurar_logging_para_api(self):
        """
        Configura logging para uso em API (sem arquivo, apenas console).
        """
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)
    
    def executar_processamento_completo(self):
        """
        Executa todo o pipeline de processamento de dados.
        """
        try:
            inicio_execucao = datetime.now()
            self.logger.info(f"Iniciando processamento completo em: {inicio_execucao}")
            
            # Etapa 1: Verificar arquivos
            if not self.verificar_arquivos():
                self.logger.error("Processamento interrompido - arquivos ausentes")
                return False
            
            # Etapa 2: Carregar planilhas
            if not self.carregar_planilhas():
                self.logger.error("Processamento interrompido - erro no carregamento")
                return False
            
            # Etapa 3: Analisar estrutura
            self.analisar_estrutura_dados()
            
            # Etapa 4: Processar dados de funcionários
            self.processar_dados_funcionarios()
            
            # Etapa 5: Processar dados temporais
            self.processar_dados_temporais()
            
            # Etapa 6: Gerar relatório
            self.gerar_relatorio_consolidado()
            
            # Etapa 7: Salvar resultados
            self.salvar_resultados()
            
            # Finalização
            fim_execucao = datetime.now()
            duracao = fim_execucao - inicio_execucao
            
            self.logger.info(f"\n" + "=" * 80)
            self.logger.info("PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
            self.logger.info("=" * 80)
            self.logger.info(f"Duração total: {duracao}")
            self.logger.info(f"Datasets processados: {len(self.dataframes)}")
            self.logger.info(f"Total de registros: {sum(len(df) for df in self.dataframes.values()):,}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro durante o processamento: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False


def main():
    """
    Função principal para execução do script.
    """
    print("=" * 80)
    print("PROCESSADOR DE DADOS DE RH - DESAFIO 4")
    print("=" * 80)
    print("Inicializando processamento...")
    
    # Criar instância do processador
    processador = ProcessadorDadosRH()
    
    # Executar processamento completo
    sucesso = processador.executar_processamento_completo()
    
    if sucesso:
        print("\n✓ Processamento concluído com sucesso!")
        print("Verifique os logs e arquivos de resultado para detalhes.")
    else:
        print("\n✗ Processamento falhou. Verifique os logs para detalhes.")
        sys.exit(1)


if __name__ == "__main__":
    main()
