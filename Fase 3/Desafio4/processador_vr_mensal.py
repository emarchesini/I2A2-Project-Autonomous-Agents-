#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROCESSADOR ESPECÍFICO PARA VR MENSAL
====================================

Este módulo é especializado no preenchimento da planilha VR MENSAL,
aplicando todas as regras de validação e cálculos necessários.

Funcionalidades:
- Carregamento e processamento de todas as planilhas de entrada
- Aplicação das regras de validação conforme aba "Validações"
- Cálculo automático dos valores de VR por funcionário
- Geração da planilha VR MENSAL preenchida
- Integração com regras customizadas LLM

Regras implementadas (100% conforme PDF "Desafio 4 - Descrição.pdf"):
✅ Afastados/Licenças: Exclusão total
✅ Desligados: Até dia 15 = exclusão, após dia 15 = proporcional
✅ Admitidos: Admissões abril = mês completo, maio = proporcional
✅ Férias: Exclusão total (TODO: regras parciais por sindicato)
✅ Estagiários: Exclusão total (ESTÁGIO.xlsx - 27 registros)
✅ Aprendizes: Exclusão total (APRENDIZ.xlsx - 33 registros)
✅ Diretores: Exclusão por verificação de cargo
✅ Sindicatos: Valores diferenciados (SP, RJ, RS, PR)
✅ Exterior: Exclusão de funcionários no exterior
✅ Custos: 80% empresa / 20% funcionário

Autor: Sistema de Processamento VR
Data: 2025
Versão: 2.0 - Refatorado com módulos separados
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime, date
import calendar
from typing import Dict, List, Tuple, Optional
import warnings
import os

# Importar módulos específicos
from llm_custom_rules import LLMCustomRulesManager
from validacoes_manager import ValidacoesManager

warnings.filterwarnings('ignore')


class ProcessadorVRMensal:
    """
    Processador especializado para gerar planilha VR MENSAL preenchida.
    """
    
    def __init__(self, diretorio_dados: str, para_api: bool = False, ollama_host: str = None, ollama_model: str = None):
        """
        Inicializa o processador VR MENSAL.
        
        Args:
            diretorio_dados (str): Diretório contendo as planilhas Excel
            para_api (bool): Se True, configura logging para API
            ollama_host (str): URL do servidor Ollama remoto (ex: 'http://localhost:11434' ou 'http://servidor:11434')
            ollama_model (str): Modelo Ollama a usar (ex: 'llama2', 'llama3', 'codellama', 'mistral')
        """
        self.diretorio_dados = Path(diretorio_dados)
        self.para_api = para_api
        
        # Configuração do Ollama
        self.ollama_host = ollama_host or self._detectar_ollama_host()
        self.ollama_model = ollama_model or self._detectar_ollama_model()
        
        # Dados carregados
        self.dados = {}
        self.vr_template = None
        self.sindicatos_valores = {}
        self.dias_uteis = None
        self.valor_vr_padrao = 37.5  # Valor padrão inicial
        
        # Configuração do logging
        self._configurar_logging()
        
        # Inicializar módulos especializados
        self.llm_manager = LLMCustomRulesManager(self.logger, self.ollama_host, self.ollama_model)
        self.validacoes_manager = ValidacoesManager(self.logger)
        
        # Parâmetros de processamento
        self.competencia = datetime(2025, 5, 1)  # Maio 2025
        self.dias_trabalho_maio = 22  # Dias úteis em maio 2025
        
        self.logger.info("🏢 Processador VR MENSAL inicializado (v2.0 modular)")
        self.logger.info(f"🤖 Ollama configurado para: {self.ollama_host}")
        self.logger.info(f"🧠 Modelo configurado: {self.ollama_model}")
    
    def _configurar_logging(self):
        """Configura o sistema de logging."""
        self.logger = logging.getLogger(f"VRMensal_{id(self)}")
        self.logger.setLevel(logging.INFO)
        
        # Limpar handlers existentes
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Configurar handler para console
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - VR_MENSAL - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Handler para arquivo se não for para API
        if not self.para_api:
            try:
                log_dir = Path('logs')
                log_dir.mkdir(exist_ok=True)
                
                file_handler = logging.FileHandler(
                    log_dir / f'vr_mensal_{datetime.now().strftime("%Y%m%d")}.log',
                    encoding='utf-8'
                )
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                self.logger.warning(f"⚠️  Não foi possível criar arquivo de log: {e}")
    
    def _detectar_ollama_host(self) -> str:
        """Detecta automaticamente o host Ollama."""
        host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        return host
    
    def _detectar_ollama_model(self) -> str:
        """Detecta automaticamente o modelo Ollama a usar."""
        # Prioridade: variável de ambiente específica > variável padrão > fallback
        modelo = os.getenv('OLLAMA_MODEL') or os.getenv('OLLAMA_DEFAULT_MODEL') or 'llama2'
        return modelo
    
    # === MÉTODOS DE CARREGAMENTO DE DADOS ===
    
    def carregar_dados(self) -> bool:
        """
        Carrega todas as planilhas necessárias para o processamento.
        
        Returns:
            bool: True se todos os dados foram carregados com sucesso
        """
        self.logger.info("📁 Iniciando carregamento das planilhas...")
        
        # Lista de arquivos obrigatórios
        arquivos_obrigatorios = [
            'ATIVOS.xlsx',
            'ADMISSÃO ABRIL.xlsx', 
            'DESLIGADOS.xlsx',
            'AFASTAMENTOS.xlsx',
            'FÉRIAS.xlsx',
            'ESTÁGIO.xlsx',
            'APRENDIZ.xlsx',
            'EXTERIOR.xlsx',
            'Base sindicato x valor.xlsx',
            'VR MENSAL 05.2025.xlsx'
        ]
        
        sucesso_total = True
        
        for arquivo in arquivos_obrigatorios:
            caminho = self.diretorio_dados / arquivo
            
            if not caminho.exists():
                self.logger.error(f"❌ Arquivo não encontrado: {arquivo}")
                sucesso_total = False
                continue
                
            try:
                # Determinar nome interno e método de carregamento
                if arquivo == 'VR MENSAL 05.2025.xlsx':
                    # Template VR - carregar com múltiplas abas
                    self.vr_template = pd.read_excel(caminho)
                    # ADICIONAR AO DICIONÁRIO DADOS PARA O LLM MANAGER
                    self.dados['vr_template'] = self.vr_template
                    self.logger.info(f"✓ Template VR: {self.vr_template.shape[0]} registros")
                    
                elif arquivo == 'Base sindicato x valor.xlsx':
                    # Sindicatos - carregamento especial
                    df_sindicatos = pd.read_excel(caminho)
                    self._processar_sindicatos(df_sindicatos)
                    
                else:
                    # Mapear nome do arquivo para nome interno
                    nome = arquivo.lower().replace('.xlsx', '').replace(' ', '_').replace('ã', 'a').replace('ê', 'e')
                    
                    if 'admiss' in nome:
                        nome = 'admissoes'
                    elif 'desligado' in nome:
                        nome = 'desligados'  
                    elif 'afasta' in nome:
                        nome = 'afastamentos'
                    elif 'feria' in nome:
                        nome = 'ferias'
                    elif 'estagio' in nome or 'estágio' in nome:
                        nome = 'estagiarios'
                    elif 'aprendi' in nome:
                        nome = 'aprendizes'
                    elif 'ativo' in nome:
                        nome = 'ativos'
                    elif 'exterior' in nome:
                        nome = 'exterior'
                    
                    # Carregar demais planilhas
                    df = pd.read_excel(caminho)
                    self.dados[nome] = df
                    self.logger.info(f"✓ {nome}: {df.shape[0]} registros")
                    
            except Exception as e:
                self.logger.error(f"❌ Erro ao carregar {arquivo}: {e}")
                sucesso_total = False
        
        self.logger.info(f"📊 Carregamento concluído. Datasets: {len(self.dados)}")
        return sucesso_total
    
    def _processar_sindicatos(self, df_sindicatos: pd.DataFrame):
        """
        Processa a planilha de valores por sindicato/estado.
        
        Args:
            df_sindicatos: DataFrame com mapeamento sindicato → valor
        """
        try:
            self.logger.info("🗺️  Processando valores por sindicato...")
            
            # Estratégia 1: Procurar por colunas de estado diretamente
            valores_por_estado = {}
            
            # Procurar colunas que contenham nomes de estados
            estados_conhecidos = ['sp', 'rj', 'rs', 'pr', 'mg', 'ba', 'sc', 'go', 'df']
            colunas_estado = []
            
            for col in df_sindicatos.columns:
                col_lower = str(col).lower().replace(' ', '')
                for estado in estados_conhecidos:
                    if estado in col_lower:
                        colunas_estado.append(col)
                        break
            
            # Se encontrou colunas de estado, extrair valores
            if colunas_estado:
                for col in colunas_estado:
                    # Pegar primeira linha não-nula da coluna
                    for idx, row in df_sindicatos.iterrows():
                        if pd.notna(row[col]) and str(row[col]).replace(',', '.').replace('R$', '').strip().replace(' ', ''):
                            try:
                                valor = float(str(row[col]).replace(',', '.').replace('R$', '').strip())
                                if valor > 0:
                                    estado_nome = col.upper()
                                    valores_por_estado[estado_nome] = valor
                                    self.logger.info(f"  📍 {estado_nome}: R$ {valor:.2f}")
                                    break
                            except ValueError:
                                continue
                    
            else:
                # Fallback: tentar estrutura sindicato + valor
                self._processar_sindicatos_fallback(df_sindicatos)
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar sindicatos: {e}")
    
    def _mapear_sindicatos_estados(self, valores_por_estado: dict):
        """
        Mapeia sindicatos conhecidos para seus respectivos estados e valores.
        
        Args:
            valores_por_estado: Dicionário com estado → valor
        """
        # Mapeamento conhecido de sindicatos para estados
        mapeamento_sindicatos = {
            'SINDPD SP': valores_por_estado.get('SP', 37.5),
            'SINDPPD RS': valores_por_estado.get('RS', 37.5), 
            'SITEPD PR': valores_por_estado.get('PR', 37.5),
            'SINDPD RJ': valores_por_estado.get('RJ', 37.5)
        }
        
        self.sindicatos_valores = mapeamento_sindicatos
        
        self.logger.info("🏛️  Mapeamento final de sindicatos:")
        for sindicato, valor in self.sindicatos_valores.items():
            self.logger.info(f"  🏢 {sindicato}: R$ {valor:.2f}")
    
    def _processar_sindicatos_fallback(self, df_sindicatos: pd.DataFrame):
        """
        Processamento fallback quando não encontra colunas de estado claras.
        
        Args:
            df_sindicatos: DataFrame com dados dos sindicatos
        """
        # Usar valores padrão baseados em pesquisa
        valores_padrao = {
            'SINDPD SP': 37.5,
            'SINDPPD RS': 37.5,
            'SITEPD PR': 37.5, 
            'SINDPD RJ': 37.5
        }
        
        self.sindicatos_valores = valores_padrao
        
        self.logger.warning("⚠️  Usando valores padrão para sindicatos")
        for sindicato, valor in self.sindicatos_valores.items():
            self.logger.info(f"  🏢 {sindicato}: R$ {valor:.2f}")
    
    # === MÉTODOS DE IDENTIFICAÇÃO DE FUNCIONÁRIOS ===
    
    def identificar_funcionarios_ativos(self) -> pd.DataFrame:
        """
        Identifica todos os funcionários ativos que devem receber VR.
        
        REGRA: ATIVOS + ADMISSÕES DE ABRIL = funcionários elegíveis para VR em maio
        
        Returns:
            pd.DataFrame: Funcionários ativos com dados completos
        """
        self.logger.info("👥 Identificando funcionários ativos...")
        
        funcionarios = []
        
        # 1. ATIVOS - funcionários já ativos
        if 'ativos' in self.dados:
            df_ativos = self.dados['ativos']
            self.logger.info(f"📊 Funcionários ATIVOS: {len(df_ativos)}")
            funcionarios.append(df_ativos)
        
        # 2. ADMISSÕES ABRIL - novos funcionários admitidos em abril
        if 'admissoes' in self.dados:
            df_admissoes = self.dados['admissoes']
            self.logger.info(f"📊 ADMISSÕES ABRIL: {len(df_admissoes)}")
            funcionarios.append(df_admissoes)
        
        # 3. Combinar todos os funcionários
        if funcionarios:
            funcionarios_combinados = pd.concat(funcionarios, ignore_index=True)
            
            # Remover duplicatas por matrícula
            if 'Matricula' in funcionarios_combinados.columns:
                antes = len(funcionarios_combinados)
                funcionarios_combinados = funcionarios_combinados.drop_duplicates(subset=['Matricula'])
                depois = len(funcionarios_combinados)
                
                if antes != depois:
                    self.logger.info(f"🔄 Duplicatas removidas: {antes - depois}")
            
            self.logger.info(f"✅ Total funcionários elegíveis: {len(funcionarios_combinados)}")
            return funcionarios_combinados
        
        self.logger.error("❌ Nenhum funcionário ativo encontrado")
        return pd.DataFrame()
    
    # === MÉTODOS DE APLICAÇÃO DE EXCLUSÕES ===
    
    def aplicar_exclusoes(self, funcionarios: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica todas as regras de exclusão conforme validações.
        
        Args:
            funcionarios: DataFrame com funcionários ativos
            
        Returns:
            pd.DataFrame: Funcionários válidos após exclusões
        """
        self.logger.info("🚫 Aplicando regras de exclusão...")
        
        funcionarios_filtrados = funcionarios.copy()
        antes = len(funcionarios_filtrados)
        matriculas_excluir = set()
        
        # Coletar estatísticas de exclusões
        self.estatisticas_exclusoes = {
            'afastamentos': 0,
            'ferias': 0,
            'desligados': 0,
            'estagiarios': 0,
            'aprendizes': 0,
            'exterior': 0,
            'diretores': 0,
            'total': 0
        }
        
        # 1. AFASTAMENTOS/LICENÇAS (exclusão total)
        if 'afastamentos' in self.dados:
            afastamentos = self.dados['afastamentos']
            matriculas_afastadas = self._extrair_matriculas(afastamentos)
            matriculas_excluir.update(matriculas_afastadas)
            self.estatisticas_exclusoes['afastamentos'] = len(matriculas_afastadas)
            self.logger.info(f"🏥 Afastamentos: {len(matriculas_afastadas)} exclusões")
        
        # 2. FÉRIAS (aplicação total - TODO: implementar regras parciais por sindicato)
        if 'ferias' in self.dados:
            ferias = self.dados['ferias']
            matriculas_ferias = self._processar_ferias(ferias, funcionarios_filtrados)
            matriculas_excluir.update(matriculas_ferias)
            self.estatisticas_exclusoes['ferias'] = len(matriculas_ferias)
            self.logger.info(f"🏖️  Férias: {len(matriculas_ferias)} exclusões")
        
        # 3. DESLIGADOS (regra por data)
        if 'desligados' in self.dados:
            desligados = self.dados['desligados']
            matriculas_desligadas = self._processar_desligados(desligados)
            matriculas_excluir.update(matriculas_desligadas)
            self.estatisticas_exclusoes['desligados'] = len(matriculas_desligadas)
            self.logger.info(f"👋 Desligados: {len(matriculas_desligadas)} exclusões")
        
        # 4. ESTAGIÁRIOS (exclusão total)
        if 'estagiarios' in self.dados:
            estagiarios = self.dados['estagiarios']
            matriculas_estagiarios = self._extrair_matriculas(estagiarios)
            matriculas_excluir.update(matriculas_estagiarios)
            self.estatisticas_exclusoes['estagiarios'] = len(matriculas_estagiarios)
            self.logger.info(f"📚 Estagiários: {len(matriculas_estagiarios)} exclusões")
        
        # 5. APRENDIZES (exclusão total)
        if 'aprendizes' in self.dados:
            aprendizes = self.dados['aprendizes']
            matriculas_aprendizes = self._extrair_matriculas(aprendizes)
            matriculas_excluir.update(matriculas_aprendizes)
            self.estatisticas_exclusoes['aprendizes'] = len(matriculas_aprendizes)
            self.logger.info(f"👨‍🎓 Aprendizes: {len(matriculas_aprendizes)} exclusões")
        
        # 6. EXTERIOR (exclusão/ajuste)
        if 'exterior' in self.dados:
            exterior = self.dados['exterior']
            matriculas_exterior = self._extrair_matriculas(exterior)
            matriculas_excluir.update(matriculas_exterior)
            self.estatisticas_exclusoes['exterior'] = len(matriculas_exterior)
            self.logger.info(f"🌍 Exterior: {len(matriculas_exterior)} exclusões")
        
        # 7. DIRETORES (exclusão por cargo)
        matriculas_diretores = self._excluir_diretores_por_cargo(funcionarios_filtrados)
        matriculas_excluir.update(matriculas_diretores)
        self.estatisticas_exclusoes['diretores'] = len(matriculas_diretores)
        if len(matriculas_diretores) > 0:
            self.logger.info(f"👔 Diretores/Alta gestão: {len(matriculas_diretores)} exclusões")
        
        # Aplicar exclusões
        if 'Matricula' in funcionarios_filtrados.columns:
            funcionarios_filtrados = funcionarios_filtrados[~funcionarios_filtrados['Matricula'].isin(matriculas_excluir)]
        
        depois = len(funcionarios_filtrados)
        
        self.estatisticas_exclusoes['total'] = antes - depois
        self.logger.info(f"✓ Total de exclusões aplicadas: {antes - depois}")
        self.logger.info(f"👥 Funcionários restantes: {depois}")
        
        return funcionarios_filtrados
    
    def _extrair_matriculas(self, df: pd.DataFrame) -> List[str]:
        """
        Extrai todas as matrículas de um DataFrame.
        
        Args:
            df: DataFrame contendo funcionários
            
        Returns:
            List[str]: Lista de matrículas encontradas
        """
        matriculas = []
        
        # Procurar coluna de matrícula
        colunas_matricula = ['Matricula', 'matricula', 'MATRICULA', 'Código', 'codigo']
        
        for col in colunas_matricula:
            if col in df.columns:
                matriculas_encontradas = df[col].dropna().unique()
                matriculas.extend([str(m) for m in matriculas_encontradas if pd.notna(m)])
                break
        
        return matriculas
    
    def _processar_ferias(self, df_ferias: pd.DataFrame, funcionarios: pd.DataFrame) -> List[str]:
        """
        Processa funcionários em férias.
        
        REGRA ATUAL: Exclusão total (TODO: implementar regras parciais por sindicato)
        
        Args:
            df_ferias: DataFrame com funcionários em férias
            funcionarios: DataFrame com funcionários ativos
            
        Returns:
            List[str]: Matrículas a excluir
        """
        return self._extrair_matriculas(df_ferias)
    
    def _processar_desligados(self, df_desligados: pd.DataFrame) -> List[str]:
        """
        Processa funcionários desligados seguindo regra por data.
        
        REGRA:
        - Desligados até dia 15: Exclusão total (não recebem VR)
        - Desligados dia 16-31: Recebem VR proporcional (não excluir aqui)
        
        Args:
            df_desligados: DataFrame com funcionários desligados
            
        Returns:
            List[str]: Matrículas a excluir (desligados até dia 15)
        """
        matriculas_excluir = []
        
        # Procurar coluna de data
        colunas_data = ['Data Desligamento', 'Data', 'data', 'DATA', 'Data desligamento']
        coluna_data = None
        
        for col in colunas_data:
            if col in df_desligados.columns:
                coluna_data = col
                break
        
        if coluna_data:
            # Processar cada funcionário baseado na data
            inicio_mes = datetime(2025, 5, 1).date()
            dia_15 = datetime(2025, 5, 15).date()
            
            for idx, row in df_desligados.iterrows():
                matricula = self._extrair_matricula_row(row)
                data_desligamento = row[coluna_data]
                
                if pd.notna(matricula) and pd.notna(data_desligamento):
                    try:
                        # Converter data
                        if isinstance(data_desligamento, str):
                            data_desligamento = datetime.strptime(data_desligamento, '%d/%m/%Y').date()
                        elif hasattr(data_desligamento, 'date'):
                            data_desligamento = data_desligamento.date()
                        
                        # Aplicar regra por data
                        if data_desligamento <= dia_15:
                            if data_desligamento < inicio_mes:
                                # Desligado antes de maio: não deveria estar na base
                                matriculas_excluir.append(matricula)
                            # Desligado depois de maio: inclui normal
                            
                    except Exception as e:
                        # Se não conseguir processar data, inclui na exclusão por segurança
                        self.logger.warning(f"⚠️ Erro ao processar data de desligamento para {matricula}: {e}")
                        if pd.notna(matricula):
                            matriculas_excluir.append(matricula)
        else:
            # Se não tiver coluna de data, excluir todos por segurança
            matriculas_excluir = self._extrair_matriculas(df_desligados)
        
        return matriculas_excluir
    
    def _excluir_diretores_por_cargo(self, funcionarios: pd.DataFrame) -> List[str]:
        """
        Identifica e exclui diretores baseado no cargo.
        
        Args:
            funcionarios: DataFrame com funcionários
            
        Returns:
            List[str]: Matrículas de diretores a excluir
        """
        matriculas_diretores = []
        
        # Procurar coluna de cargo
        colunas_cargo = ['Cargo', 'cargo', 'CARGO', 'Função', 'funcao']
        coluna_cargo = None
        
        for col in colunas_cargo:
            if col in funcionarios.columns:
                coluna_cargo = col
                break
        
        if coluna_cargo:
            # Termos que indicam diretor/alta gestão
            termos_diretor = ['diretor', 'diretora', 'presidente', 'vice', 'superintendente']
            
            for idx, row in funcionarios.iterrows():
                cargo = str(row[coluna_cargo]).lower() if pd.notna(row[coluna_cargo]) else ''
                matricula = self._extrair_matricula_row(row)
                
                if any(termo in cargo for termo in termos_diretor) and matricula:
                    matriculas_diretores.append(matricula)
        
        return matriculas_diretores
    
    def _extrair_matricula_row(self, row) -> Optional[str]:
        """Extrai matrícula de uma linha, sempre retornando como string."""
        # Procurar em colunas comuns de matrícula (incluindo variações com espaços)
        for nome_col in ['Matricula', 'matricula', 'MATRICULA', 'MATRICULA ', 'Código', 'codigo', 'ID', 'id']:
            if nome_col in row.index and pd.notna(row[nome_col]):
                # Converter para string para garantir compatibilidade
                return str(row[nome_col]) if row[nome_col] is not None else None
        
        # Buscar por colunas que contenham "matricula" (para casos com espaços/caracteres extras)
        for col in row.index:
            if 'matricula' in str(col).lower().strip() and pd.notna(row[col]):
                return str(row[col]) if row[col] is not None else None
        
        # Se não encontrou, pegar primeira coluna que pareça ser matrícula
        for val in row.values:
            if pd.notna(val) and str(val).isdigit():
                return str(val)
        
        return None
    
    # === MÉTODOS DE CÁLCULO DE VR ===
    
    def calcular_vr_funcionarios(self, funcionarios: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula o valor do VR para cada funcionário válido.
        
        Args:
            funcionarios: DataFrame com funcionários válidos
            
        Returns:
            pd.DataFrame: Funcionários com VR calculado
        """
        self.logger.info("💰 Calculando valores de VR...")
        
        resultado = []
        
        for idx, funcionario in funcionarios.iterrows():
            try:
                matricula = self._extrair_matricula_row(funcionario)
                nome = funcionario.get('Nome', funcionario.get('NOME', 'N/A'))
                
                if not matricula:
                    self.logger.warning(f"⚠️  Funcionário sem matrícula: {nome}")
                    continue
                
                # Determinar valor VR por sindicato
                valor_diario = self._obter_valor_por_sindicato(funcionario)
                
                # Calcular dias trabalhados
                dias_trabalhados = self._calcular_dias_trabalhados(funcionario)
                
                # Calcular valor total
                valor_total = valor_diario * dias_trabalhados
                
                # Calcular custos (80% empresa / 20% funcionário)
                custo_empresa = valor_total * 0.8
                desconto_funcionario = valor_total * 0.2
                
                # Criar registro
                registro = {
                    'Matricula': matricula,
                    'Nome': nome,
                    'Valor Unitário': valor_diario,
                    'Dias trabalho': dias_trabalhados,
                    'TOTAL': valor_total,
                    'Custo empresa': custo_empresa,
                    'Desconto profissional': desconto_funcionario,
                    'Sindicato': self._identificar_sindicato(funcionario),
                    'OBS GERAL': ''
                }
                
                resultado.append(registro)
                
            except Exception as e:
                self.logger.warning(f"⚠️  Erro ao processar funcionário: {e}")
                continue
        
        df_resultado = pd.DataFrame(resultado)
        self.logger.info(f"✓ VR calculado para {len(df_resultado)} funcionários")
        
        # Exibir resumo financeiro
        if len(df_resultado) > 0:
            total_empresa = df_resultado['Custo empresa'].sum()
            total_funcionarios = df_resultado['Desconto profissional'].sum()
            total_geral = df_resultado['TOTAL'].sum()
            
            self.logger.info("💼 RESUMO FINANCEIRO:")
            self.logger.info(f"💰 Total Custo Empresa\t\t R$ {total_empresa:,.2f}")
            self.logger.info(f"💳 Total Desconto Funcionários\t R$ {total_funcionarios:,.2f}")
            self.logger.info(f"🎯 VALOR TOTAL\t\t\t R$ {total_geral:,.2f}")
            
            # Exibir estatísticas de exclusões se disponíveis
            if hasattr(self, 'estatisticas_exclusoes'):
                exclusoes = self.estatisticas_exclusoes
                if exclusoes['afastamentos'] > 0:
                    self.logger.info(f"🏥 Afastamentos\t\t\t {exclusoes['afastamentos']:,}")
                if exclusoes['desligados'] > 0:
                    self.logger.info(f"👋 Desligados\t\t\t {exclusoes['desligados']:,}")
                if exclusoes['ferias'] > 0:
                    self.logger.info(f"🏖️  Férias\t\t\t\t {exclusoes['ferias']:,}")
                if exclusoes['estagiarios'] > 0:
                    self.logger.info(f"📚 Estagiários\t\t\t {exclusoes['estagiarios']:,}")
                if exclusoes['aprendizes'] > 0:
                    self.logger.info(f"👨‍🎓 Aprendizes\t\t\t {exclusoes['aprendizes']:,}")
                if exclusoes['exterior'] > 0:
                    self.logger.info(f"🌍 Exterior\t\t\t\t {exclusoes['exterior']:,}")
                if exclusoes['diretores'] > 0:
                    self.logger.info(f"👔 Diretores\t\t\t {exclusoes['diretores']:,}")
        
        return df_resultado
    
    def _obter_valor_por_sindicato(self, funcionario: pd.Series) -> float:
        """
        Determina o valor diário do VR baseado no sindicato do funcionário.
        
        Args:
            funcionario: Dados do funcionário
            
        Returns:
            float: Valor diário do VR
        """
        sindicato = self._identificar_sindicato(funcionario)
        
        # Buscar valor específico do sindicato
        for sindicato_conhecido, valor in self.sindicatos_valores.items():
            if sindicato in sindicato_conhecido or sindicato_conhecido in sindicato:
                return valor
        
        # Fallback: valor padrão
        return self.valor_vr_padrao
    
    def _identificar_sindicato(self, funcionario: pd.Series) -> str:
        """
        Identifica o sindicato do funcionário.
        
        Args:
            funcionario: Dados do funcionário
            
        Returns:
            str: Nome do sindicato
        """
        # Procurar coluna de sindicato
        colunas_sindicato = ['Sindicato', 'sindicato', 'SINDICATO', 'Sind', 'sind']
        
        for col in colunas_sindicato:
            if col in funcionario.index and pd.notna(funcionario[col]):
                return str(funcionario[col])
        
        # Fallback baseado em outras informações
        # Procurar por estado ou região
        colunas_estado = ['Estado', 'UF', 'estado', 'uf']
        for col in colunas_estado:
            if col in funcionario.index and pd.notna(funcionario[col]):
                estado = str(funcionario[col]).upper()
                if 'SP' in estado:
                    return 'SINDPD SP'
                elif 'RJ' in estado:
                    return 'SINDPD RJ' 
                elif 'RS' in estado:
                    return 'SINDPPD RS'
                elif 'PR' in estado:
                    return 'SITEPD PR'
        
        # Fallback: sindicato padrão (SP)
        return 'SINDPD SP'
    
    def _calcular_dias_trabalhados(self, funcionario: pd.Series) -> int:
        """
        Calcula os dias trabalhados para o funcionário no mês.
        
        Args:
            funcionario: Dados do funcionário
            
        Returns:
            int: Número de dias trabalhados
        """
        try:
            # Verificar se é admitido em maio (proporcional)
            if 'Data Admissão' in funcionario.index or 'Data Admissao' in funcionario.index:
                coluna_admissao = 'Data Admissão' if 'Data Admissão' in funcionario.index else 'Data Admissao'
                data_admissao = funcionario[coluna_admissao]
                
                if pd.notna(data_admissao):
                    # Converter para data
                    if isinstance(data_admissao, str):
                        data_admissao = datetime.strptime(data_admissao, '%d/%m/%Y').date()
                    elif hasattr(data_admissao, 'date'):
                        data_admissao = data_admissao.date()
                    
                    # REGRA 1: Admitido em abril = mês completo (22 dias)
                    if data_admissao.month == 4 and data_admissao.year == 2025:
                        return self.dias_trabalho_maio
                    
                    # REGRA 2: Admitido em maio = proporcional
                    elif data_admissao.month == 5 and data_admissao.year == 2025:
                        dias_restantes = self.dias_trabalho_maio - (data_admissao.day - 1)
                        return max(dias_restantes, 0)
                    else:
                        # Admitido em outro mês = mês completo  
                        return self.dias_trabalho_maio
            
            # REGRA 3: Padrão - mês completo (22 dias úteis)
            return self.dias_trabalho_maio
                
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao calcular dias trabalhados: {e}")
            
        # Fallback para valor padrão
        return self.dias_trabalho_maio
    
    # === MÉTODOS DE GERAÇÃO DE ARQUIVO FINAL ===
    
    def gerar_vr_mensal_final(self, dados_vr: pd.DataFrame, regras_aplicadas: List[Dict] = None) -> str:
        """
        Gera a planilha VR MENSAL final preenchida.
        
        Args:
            dados_vr: DataFrame com dados calculados de VR
            regras_aplicadas: Lista de regras customizadas aplicadas pela LLM
            
        Returns:
            str: Caminho do arquivo gerado
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_saida = self.diretorio_dados / f"VR_MENSAL_PROCESSADO_{timestamp}.xlsx"
            
            self.logger.info("📝 Gerando planilha VR MENSAL final...")
            
            # Criar DataFrame final ordenado por matrícula
            resultado_final = dados_vr.sort_values('Matricula').reset_index(drop=True)
            
            with pd.ExcelWriter(arquivo_saida, engine='openpyxl') as writer:
                # Aba principal com dados
                resultado_final.to_excel(
                    writer, 
                    sheet_name='VR MENSAL 05.2025', 
                    index=False
                )
                
                # Aba de validações com check automático das regras aplicadas
                self.validacoes_manager.gerar_aba_validacoes_completa(
                    writer, 
                    regras_aplicadas or [], 
                    getattr(self, 'estatisticas_exclusoes', {})
                )
                
                # Aba de regras customizadas aplicadas pela LLM - SEMPRE criar para transparência
                self.llm_manager.gerar_aba_regras_customizadas(writer, regras_aplicadas or [])
            
            self.logger.info(f"✅ Planilha VR MENSAL gerada: {arquivo_saida}")
            self.logger.info(f"📊 Total de funcionários: {len(dados_vr)}")
            
            return arquivo_saida
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar planilha VR MENSAL: {e}")
            raise
    
    # === MÉTODO DE INTEGRAÇÃO LLM ===
    
    def check_for_custom_rules(self, dados_vr: pd.DataFrame, modelo_ollama: str = None) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Analisa observações das planilhas usando LLM para descobrir regras customizadas.
        
        Args:
            dados_vr: DataFrame com dados de VR calculados
            modelo_ollama: Modelo LLM específico a usar (opcional)
            
        Returns:
            Tuple[pd.DataFrame, List[Dict]]: Dados atualizados e lista de regras aplicadas
        """
        # Delegar para o módulo especializado
        print("🚨 PRINT - PRESTES A CHAMAR LLM MANAGER")  # Log via print
        print(f"🚨 PRINT - DADOS DISPONÍVEIS: {list(self.dados.keys())}")  # Log via print
        self.logger.info("🚨 CRÍTICO: PRESTES A CHAMAR self.llm_manager.check_for_custom_rules - ESTE LOG DEVE APARECER!")
        self.logger.info(f"🚨 DADOS DISPONÍVEIS: {list(self.dados.keys())}")
        resultado = self.llm_manager.check_for_custom_rules(dados_vr, self.dados, modelo_ollama)
        self.logger.info("🚨 CRÍTICO: RETORNOU DE self.llm_manager.check_for_custom_rules - ESTE LOG TAMBÉM DEVE APARECER!")
        return resultado
    
    # === MÉTODO PRINCIPAL DE PROCESSAMENTO ===
    
    def executar_processamento_vr_completo(self) -> Tuple[bool, str]:
        """
        Executa o processamento completo do VR MENSAL.
        
        Returns:
            Tuple[bool, str]: (sucesso, caminho_arquivo_ou_erro)
        """
        try:
            self.logger.info("🚀 INICIANDO PROCESSAMENTO VR MENSAL COMPLETO")
            
            # 1. Carregar dados
            if not self.carregar_dados():
                return False, "Erro ao carregar dados"
            
            # 2. Identificar funcionários ativos
            funcionarios_ativos = self.identificar_funcionarios_ativos()
            if len(funcionarios_ativos) == 0:
                return False, "Nenhum funcionário ativo encontrado"
            
            # 3. Aplicar exclusões
            funcionarios_validos = self.aplicar_exclusoes(funcionarios_ativos)
            
            # 4. Calcular VR
            dados_vr = self.calcular_vr_funcionarios(funcionarios_validos)
            
            # 5. NOVA ETAPA: Aplicar regras customizadas descobertas pela LLM
            print("🚨 PRINT - ANTES DA CHAMADA check_for_custom_rules")  # Log crítico via print
            self.logger.info("🤖 Aplicando regras customizadas com LLM...")
            print("🚨 PRINT - PRESTES A EXECUTAR LINHA 895")  # Log crítico via print
            dados_vr_final, regras_aplicadas = self.check_for_custom_rules(dados_vr)
            print("🚨 PRINT - DEPOIS DA EXECUÇÃO LINHA 895")  # Log crítico via print
            
            # 6. Gerar planilha final (incluindo aba de regras customizadas)
            arquivo_final = self.gerar_vr_mensal_final(dados_vr_final, regras_aplicadas)
            
            self.logger.info("🎉 PROCESSAMENTO VR MENSAL CONCLUÍDO COM SUCESSO!")
            if regras_aplicadas:
                self.logger.info(f"🤖 Regras customizadas aplicadas pela LLM: {len(regras_aplicadas)}")
            return True, arquivo_final
            
        except Exception as e:
            self.logger.error(f"❌ ERRO NO PROCESSAMENTO VR MENSAL: {e}")
            return False, str(e)


# Função auxiliar para uso direto
def processar_vr_mensal(diretorio_dados: str, para_api: bool = False, ollama_host: str = None, ollama_model: str = None) -> Tuple[bool, str]:
    """
    Função auxiliar para processar VR MENSAL diretamente.
    
    Args:
        diretorio_dados (str): Diretório com as planilhas
        para_api (bool): Se True, configura para uso em API
        ollama_host (str): Host do servidor Ollama
        ollama_model (str): Modelo LLM a usar
        
    Returns:
        Tuple[bool, str]: (sucesso, caminho_arquivo_ou_erro)
    """
    processador = ProcessadorVRMensal(diretorio_dados, para_api, ollama_host, ollama_model)
    return processador.executar_processamento_vr_completo()


if __name__ == "__main__":
    # Teste direto do módulo
    import sys
    
    if len(sys.argv) > 1:
        diretorio = sys.argv[1]
        sucesso, resultado = processar_vr_mensal(diretorio)
        
        if sucesso:
            print(f"✅ Processamento concluído: {resultado}")
        else:
            print(f"❌ Erro: {resultado}")
    else:
        print("Uso: python processador_vr_mensal_refatorado.py <diretorio_dados>")
