#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MÓDULO DE REGRAS CUSTOMIZADAS LLM
==================================

Este módulo é responsável por toda a lógica relacionada ao descobrimento
e aplicação de regras customizadas usando Large Language Models (LLM).

Funcionalidades:
- Extração de observações das planilhas
- Comunicação com servidor Ollama
- Processamento individual de observações
- Aplicação de regras customizadas via pandas
- Geração da aba de regras customizadas aplicadas

Autor: Sistema de Processamento VR
Data: 2025
Versão: 1.0
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json
import ollama
import os


class LLMCustomRulesManager:
    """
    Gerenciador de regras customizadas baseadas em LLM.
    
    Responsável por extrair observações das planilhas, analisar com LLM,
    e aplicar regras customizadas descobertas pela IA.
    """
    
    def __init__(self, logger: logging.Logger, ollama_host: str = None, ollama_model: str = None):
        """
        Inicializa o gerenciador de regras LLM.
        
        Args:
            logger: Logger para registro de eventos
            ollama_host: Servidor Ollama para comunicação com LLM
            ollama_model: Modelo LLM a ser utilizado
        """
        self.logger = logger
        self.ollama_host = ollama_host or os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.ollama_model = ollama_model or self._detectar_ollama_model()
        
    def _detectar_ollama_model(self) -> str:
        """Detecta automaticamente o modelo Ollama a usar."""
        # Prioridade: variável de ambiente específica > variável padrão > fallback
        modelo = os.getenv('OLLAMA_MODEL') or os.getenv('OLLAMA_DEFAULT_MODEL') or 'llama2'
        self.logger.info(f"🧠 Modelo Ollama detectado: {modelo}")
        return modelo
    
    def check_for_custom_rules(self, dados_vr: pd.DataFrame, dados_planilhas: Dict, 
                             modelo_ollama: str = None) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Analisa observações das planilhas usando LLM para descobrir regras customizadas.
        
        Esta função:
        1. Extrai observações das planilhas
        2. Processa cada observação individualmente com a LLM
        3. Aplica regras customizadas descobertas
        4. Retorna dados atualizados e regras aplicadas
        
        Args:
            dados_vr: DataFrame com dados de VR calculados
            dados_planilhas: Dicionário com todas as planilhas carregadas
            modelo_ollama: Modelo LLM específico a usar (opcional)
            
        Returns:
            Tuple[pd.DataFrame, List[Dict]]: Dados atualizados e lista de regras aplicadas
        """
        self.logger.info("🚨 ENTRADA check_for_custom_rules - ESTE LOG DEVE APARECER PRIMEIRO!")
        self.logger.info("🤖 === INICIANDO ANÁLISE DE REGRAS CUSTOMIZADAS COM LLM ===")
        
        regras_aplicadas = []
        dados_vr_atualizado = dados_vr.copy()
        
        try:
            # 1. Determinar modelo a usar
            modelo_final = modelo_ollama or self.ollama_model
            self.logger.info(f"🧠 Usando modelo: {modelo_final}")
            
            # 2. Extrair observações
            self.logger.info("📊 Extraindo observações das planilhas...")
            self.logger.info("🚨 PRESTES A CHAMAR extrair_observacoes_planilhas - ESTE LOG DEVE APARECER!")
            observacoes = self.extrair_observacoes_planilhas(dados_planilhas)
            self.logger.info("🚨 RETORNOU DE extrair_observacoes_planilhas - ESTE LOG TAMBÉM DEVE APARECER!")
            
            total_criticas = len(observacoes['criticas'])
            total_operacionais = len(observacoes['operacionais'])
            total_observacoes = total_criticas + total_operacionais
            
            self.logger.info(f"📈 Total de observações encontradas: {total_observacoes}")
            self.logger.info(f"🔴 Críticas: {total_criticas} | 🟡 Operacionais: {total_operacionais}")
            
            if total_observacoes == 0:
                self.logger.info("ℹ️  Nenhuma observação relevante encontrada para análise")
                return dados_vr_atualizado, regras_aplicadas
            
            # 3. Processar observações críticas individualmente
            if observacoes['criticas']:
                self.logger.info(f"🔴 Processando {total_criticas} observações críticas...")
                for i, obs in enumerate(observacoes['criticas'], 1):
                    self.logger.info(f"📋 Observação crítica {i}/{total_criticas}")
                    regra_individual = self._processar_observacao_individual(
                        obs, dados_vr_atualizado, modelo_final, 'CRÍTICA', i, total_criticas
                    )
                    if regra_individual:
                        dados_vr_atualizado, regra_aplicada = self._aplicar_regra_customizada_individual(
                            dados_vr_atualizado, regra_individual, obs
                        )
                        # INCLUIR TODAS as regras (aplicadas E não aplicadas) para transparência total
                        if regra_aplicada:
                            regras_aplicadas.append(regra_aplicada)
            
            # 4. Processar observações operacionais individualmente
            if observacoes['operacionais']:
                self.logger.info(f"🟡 Processando {total_operacionais} observações operacionais...")
                for i, obs in enumerate(observacoes['operacionais'], 1):
                    self.logger.info(f"📋 Observação operacional {i}/{total_operacionais}")
                    regra_individual = self._processar_observacao_individual(
                        obs, dados_vr_atualizado, modelo_final, 'OPERACIONAL', i, total_operacionais
                    )
                    if regra_individual:
                        dados_vr_atualizado, regra_aplicada = self._aplicar_regra_customizada_individual(
                            dados_vr_atualizado, regra_individual, obs
                        )
                        # INCLUIR TODAS as regras (aplicadas E não aplicadas) para transparência total
                        if regra_aplicada:
                            regras_aplicadas.append(regra_aplicada)
                    
            self.logger.info(f"✅ Análise LLM concluída. Regras aplicadas: {len(regras_aplicadas)}")
            
            return dados_vr_atualizado, regras_aplicadas
            
        except Exception as e:
            self.logger.error(f"❌ Erro na análise de regras customizadas: {e}")
            return dados_vr_atualizado, regras_aplicadas
    
    def extrair_observacoes_planilhas(self, dados_planilhas: Dict) -> Dict:
        """
        Extrai todas as observações das planilhas conforme análise realizada.
        
        Args:
            dados_planilhas: Dicionário com todas as planilhas carregadas
            
        Returns:
            Dict com observações categorizadas por planilha e tipo
        """
        
        # 🚨 DEBUG CRÍTICO: ENTRADA DA FUNÇÃO
        self.logger.info("🚨 ===== INICIANDO extrair_observacoes_planilhas =====")
        self.logger.info(f"🚨 RECEBIDO dados_planilhas com {len(dados_planilhas)} planilhas")
        
        observacoes = {
            'criticas': [],
            'operacionais': [],
            'informativas': [],
            'contexto_geral': {}
        }
        
        # 🔍 DEBUG: Verificar quais planilhas estão disponíveis
        self.logger.info(f"🔍 DEBUG - Planilhas disponíveis: {list(dados_planilhas.keys())}")
        self.logger.info(f"🔍 DEBUG - Verificando se 'admissoes' está em dados_planilhas: {'admissoes' in dados_planilhas}")
        
        try:
            # 1. OBSERVAÇÕES CRÍTICAS - ADMISSÃO ABRIL (LÓGICA DINÂMICA)
            # 🚨 DEBUG CRÍTICO: Verificar se a condição será avaliada
            self.logger.info(f"🚨 DEBUG CRÍTICO - PRESTES A AVALIAR: if 'admissoes' in dados_planilhas")
            self.logger.info(f"🚨 DEBUG CRÍTICO - Chaves exatas: {list(dados_planilhas.keys())}")
            self.logger.info(f"🚨 DEBUG CRÍTICO - Resultado da condição: {'admissoes' in dados_planilhas}")
            
            if 'admissoes' in dados_planilhas:
                self.logger.info(f"✅ ADMISSÃO ABRIL ENCONTRADA! Iniciando processamento...")
            else:
                self.logger.warning(f"❌ ADMISSÃO ABRIL NÃO ENCONTRADA no dicionário dados_planilhas!")
                
            if 'admissoes' in dados_planilhas:
                df_admissoes = dados_planilhas['admissoes']
                self.logger.info(f"🔍 DEBUG ADMISSÕES - Shape: {df_admissoes.shape}")
                self.logger.info(f"🔍 DEBUG ADMISSÕES - Colunas: {list(df_admissoes.columns)}")
                self.logger.info(f"🔍 DEBUG ADMISSÕES - Primeiras 3 linhas:")
                for i in range(min(3, len(df_admissoes))):
                    linha = df_admissoes.iloc[i]
                    self.logger.info(f"🔍 DEBUG ADMISSÕES - Linha {i}: {dict(linha)}")
                
                # NOVA LÓGICA DINÂMICA: Encontrar a última coluna com dados
                coluna_obs = self._encontrar_ultima_coluna_com_dados(df_admissoes)
                self.logger.info(f"🔍 DEBUG ADMISSÕES - Coluna de observação encontrada: {coluna_obs}")
                
                if coluna_obs:
                    self.logger.info(f"📍 Coluna de observação identificada: {coluna_obs}")
                    contador = 0
                    for idx, linha in df_admissoes.iterrows():
                        obs_conteudo = linha[coluna_obs]
                        if pd.notna(obs_conteudo) and str(obs_conteudo).strip():
                            contador += 1
                            linha_completa = linha
                            # PROCURAR MATRÍCULA NAS COLUNAS ANTERIORES
                            matricula = self._extrair_matricula_colunas_anteriores(linha_completa, coluna_obs, df_admissoes.columns)
                            # CAPTURAR TODA A LINHA PARA CONTEXTO COMPLETO
                            dados_linha = self._extrair_dados_linha_completa(linha_completa, df_admissoes.columns)
                            self.logger.info(f"🔍 DEBUG ADMISSÕES - Observação {contador}: '{obs_conteudo}' | Matrícula: {matricula}")
                            observacoes['criticas'].append({
                                'planilha': 'ADMISSÃO ABRIL',
                                'matricula': matricula,
                                'observacao': str(obs_conteudo).strip(),
                                'tipo': 'critica',
                                'dados_linha_completa': dados_linha
                            })
                    self.logger.info(f"✅ DEBUG ADMISSÕES - Total observações encontradas: {contador}")
                else:
                    self.logger.warning("⚠️ DEBUG ADMISSÕES - Nenhuma coluna de observação encontrada")
                    # Debug: mostrar todas as colunas com dados
                    for col in df_admissoes.columns:
                        dados_nao_vazios = df_admissoes[col].dropna()
                        if len(dados_nao_vazios) > 0:
                            self.logger.info(f"🔍 DEBUG ADMISSÕES - Coluna '{col}' tem {len(dados_nao_vazios)} dados não vazios")
                            exemplos = [str(val) for val in dados_nao_vazios.head(3)]
                            self.logger.info(f"🔍 DEBUG ADMISSÕES - Exemplos '{col}': {exemplos}")
                            
            # 2. OBSERVAÇÕES OPERACIONAIS - AFASTAMENTOS (LÓGICA DINÂMICA)
            if 'afastamentos' in dados_planilhas:
                df_afastamentos = dados_planilhas['afastamentos']
                self.logger.info("🔍 Analisando observações em AFASTAMENTOS...")
                
                coluna_obs = self._encontrar_ultima_coluna_com_dados(df_afastamentos)
                
                if coluna_obs:
                    self.logger.info(f"📍 Coluna de observação identificada: {coluna_obs}")
                    for idx, linha in df_afastamentos.iterrows():
                        obs_conteudo = linha[coluna_obs]
                        if pd.notna(obs_conteudo) and str(obs_conteudo).strip():
                            linha_completa = linha
                            # PROCURAR MATRÍCULA NAS COLUNAS ANTERIORES
                            matricula = self._extrair_matricula_colunas_anteriores(linha_completa, coluna_obs, df_afastamentos.columns)
                            # CAPTURAR TODA A LINHA PARA CONTEXTO COMPLETO
                            dados_linha = self._extrair_dados_linha_completa(linha_completa, df_afastamentos.columns)
                            observacoes['operacionais'].append({
                                'planilha': 'AFASTAMENTOS',
                                'matricula': matricula,
                                'observacao': str(obs_conteudo).strip(),
                                'tipo': 'operacional',
                                'dados_linha_completa': dados_linha
                            })
            
            # 2. OBSERVAÇÕES OPERACIONAIS - AFASTAMENTOS
            if 'afastamentos' in dados_planilhas:
                df_afastamentos = dados_planilhas['afastamentos']
                self.logger.info("🔍 Analisando observações em AFASTAMENTOS...")
                
                # Coluna "na compra?" - RESTAURADA DO CÓDIGO ANTIGO
                if 'na compra?' in df_afastamentos.columns:
                    obs_compra = df_afastamentos['na compra?'].dropna()
                    for idx, obs in obs_compra.items():
                        if pd.notna(obs):
                            linha_completa = df_afastamentos.iloc[idx]
                            matricula = self._extrair_matricula_row(linha_completa)
                            # CAPTURAR TODA A LINHA PARA CONTEXTO COMPLETO
                            dados_linha = self._extrair_dados_linha_completa(linha_completa, df_afastamentos.columns)
                            observacoes['operacionais'].append({
                                'planilha': 'AFASTAMENTOS',
                                'matricula': matricula,
                                'observacao': str(obs),
                                'tipo': 'processo_compra',
                                'dados_linha_completa': dados_linha
                            })
                
                # Coluna "Unnamed: 3" ou "Col_3" (datas de retorno) - RESTAURADA DO CÓDIGO ANTIGO
                coluna_retorno = None
                if 'Unnamed: 3' in df_afastamentos.columns:
                    coluna_retorno = 'Unnamed: 3'
                elif 'Col_3' in df_afastamentos.columns:
                    coluna_retorno = 'Col_3'
                
                if coluna_retorno:
                    obs_retorno = df_afastamentos[coluna_retorno].dropna()
                    for idx, obs in obs_retorno.items():
                        if pd.notna(obs) and str(obs).strip():
                            linha_completa = df_afastamentos.iloc[idx]
                            matricula = self._extrair_matricula_row(linha_completa)
                            # CAPTURAR TODA A LINHA PARA CONTEXTO COMPLETO
                            dados_linha = self._extrair_dados_linha_completa(linha_completa, df_afastamentos.columns)
                            observacoes['operacionais'].append({
                                'planilha': 'AFASTAMENTOS',
                                'matricula': matricula,
                                'observacao': str(obs),
                                'tipo': 'data_retorno',
                                'dados_linha_completa': dados_linha
                            })
            
            # 3. OBSERVAÇÕES CRÍTICAS - VR MENSAL TEMPLATE (LÓGICA DINÂMICA)
            if 'vr_template' in dados_planilhas:
                df_vr = dados_planilhas['vr_template']
                self.logger.info("🔍 Analisando observações em VR MENSAL TEMPLATE...")
                
                # NOVA LÓGICA DINÂMICA: Encontrar a última coluna com dados
                coluna_obs = self._encontrar_ultima_coluna_com_dados(df_vr)
                
                if coluna_obs:
                    self.logger.info(f"📍 Coluna de observação identificada: {coluna_obs}")
                    for idx, linha in df_vr.iterrows():
                        obs_conteudo = linha[coluna_obs]
                        if pd.notna(obs_conteudo) and str(obs_conteudo).strip():
                            linha_completa = linha
                            # PROCURAR MATRÍCULA NAS COLUNAS ANTERIORES
                            matricula = self._extrair_matricula_colunas_anteriores(linha_completa, coluna_obs, df_vr.columns)
                            # CAPTURAR TODA A LINHA PARA CONTEXTO COMPLETO
                            dados_linha = self._extrair_dados_linha_completa(linha_completa, df_vr.columns)
                            observacoes['criticas'].append({
                                'planilha': 'VR MENSAL',
                                'matricula': matricula,
                                'observacao': str(obs_conteudo).strip(),
                                'tipo': 'critica',
                                'dados_linha_completa': dados_linha
                            })
            
            # 4. OBSERVAÇÕES OPERACIONAIS - EXTERIOR (LÓGICA DINÂMICA)
            if 'exterior' in dados_planilhas:
                df_exterior = dados_planilhas['exterior']
                self.logger.info("🔍 Analisando observações em EXTERIOR...")
                
                # NOVA LÓGICA DINÂMICA: Encontrar a última coluna com dados
                coluna_obs = self._encontrar_ultima_coluna_com_dados(df_exterior)
                
                if coluna_obs:
                    self.logger.info(f"📍 Coluna de observação identificada: {coluna_obs}")
                    for idx, linha in df_exterior.iterrows():
                        obs_conteudo = linha[coluna_obs]
                        if pd.notna(obs_conteudo) and str(obs_conteudo).strip():
                            linha_completa = linha
                            # PROCURAR MATRÍCULA NAS COLUNAS ANTERIORES
                            matricula = self._extrair_matricula_colunas_anteriores(linha_completa, coluna_obs, df_exterior.columns)
                            # CAPTURAR TODA A LINHA PARA CONTEXTO COMPLETO
                            dados_linha = self._extrair_dados_linha_completa(linha_completa, df_exterior.columns)
                            observacoes['operacionais'].append({
                                'planilha': 'EXTERIOR',
                                'matricula': matricula,
                                'observacao': str(obs_conteudo).strip(),
                                'tipo': 'operacional',
                                'dados_linha_completa': dados_linha
                            })
            
            # 5. OBSERVAÇÕES OPERACIONAIS - DESLIGADOS - RESTAURADA DO CÓDIGO ANTIGO
            if 'desligados' in dados_planilhas:
                df_desligados = dados_planilhas['desligados']
                self.logger.info("🔍 Analisando observações em DESLIGADOS...")
                
                # Coluna "COMUNICADO DE DESLIGAMENTO" - RESTAURADA DO CÓDIGO ANTIGO
                if 'COMUNICADO DE DESLIGAMENTO' in df_desligados.columns:
                    obs_comunicado = df_desligados['COMUNICADO DE DESLIGAMENTO'].dropna()
                    total_comunicados = len(obs_comunicado)
                    observacoes['operacionais'].append({
                        'planilha': 'DESLIGADOS',
                        'matricula': 'TODOS',
                        'observacao': f'{total_comunicados} desligamentos com comunicado OK',
                        'tipo': 'controle_comunicacao',
                        'dados_linha_completa': {}
                    })
            
            # Log final
            self.logger.info(f"📊 Observações extraídas por tipo:")
            self.logger.info(f"  - Críticas: {len(observacoes['criticas'])}")
            self.logger.info(f"  - Operacionais: {len(observacoes['operacionais'])}")
            
            return observacoes
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao extrair observações: {e}")
            return observacoes
    
    def _extrair_dados_linha_completa(self, linha: pd.Series, colunas: pd.Index) -> Dict:
        """
        Extrai todos os dados de uma linha para contexto completo da LLM.
        
        Args:
            linha: Série pandas com dados da linha
            colunas: Índice das colunas
            
        Returns:
            Dicionário com todos os dados da linha formatados
        """
        try:
            dados = {}
            
            for col in colunas:
                valor = linha[col]
                
                # Pular valores vazios/nulos
                if pd.isna(valor) or str(valor).strip() == '':
                    continue
                    
                # Renomear colunas Unnamed para melhor contexto
                col_nome = col
                if 'Unnamed' in str(col):
                    col_nome = f"Col_{col.split(':')[-1].strip()}" if ':' in str(col) else f"Col_{col.replace('Unnamed: ', '')}"
                
                dados[col_nome] = valor
                
            return dados
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao extrair dados completos da linha: {e}")
            return {'erro': 'Não foi possível extrair dados da linha'}
    
    def _extrair_matricula_vr_mensal(self, linha: pd.Series, colunas: pd.Index) -> str:
        """
        Extração inteligente de matrícula específica para planilha VR MENSAL.
        
        Args:
            linha: Série pandas com dados da linha
            colunas: Índice das colunas da planilha
            
        Returns:
            Matrícula encontrada ou identificação do tipo de linha
        """
        try:
            # Lista de possíveis colunas de matrícula em ordem de prioridade
            colunas_matricula = ['Unnamed: 0', 'Matricula', 'ID', 'codigo', 'CODIGO']
            
            for col_nome in colunas_matricula:
                if col_nome in colunas:
                    valor = linha[col_nome]
                    if pd.notna(valor):
                        valor_str = str(valor).strip()
                        if self._validar_matricula(valor_str):
                            return valor_str
            
            # Se não encontrou matrícula válida, identificar tipo de linha
            tipo_linha = self._identificar_tipo_linha_vr(linha, colunas)
            self.logger.debug(f"⚠️ Linha sem matrícula válida identificada como: {tipo_linha}")
            
            return f"SEM_MATRICULA_{tipo_linha.upper()}"
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao extrair matrícula VR MENSAL: {e}")
            return "ERRO_EXTRACAO"
    
    def _validar_matricula(self, valor: str) -> bool:
        """Valida se um valor parece ser uma matrícula válida."""
        if not valor or len(valor.strip()) == 0:
            return False
            
        valor = valor.strip()
        
        # 🚨 CORREÇÃO: Rejeitar datas (formato de timestamp)
        if '00:00:00' in valor or '-' in valor and len(valor) > 10:
            return False
            
        # 🚨 CORREÇÃO: Rejeitar valores muito longos (datas tem >10 chars)
        if len(valor) > 10:
            return False
        
        # Verificar se contém dígitos (matrícula geralmente tem números)
        if not any(c.isdigit() for c in valor):
            return False
            
        # 🚨 CORREÇÃO: Matrícula deve ser principalmente numérica
        if not valor.replace('.', '').replace(',', '').isdigit():
            return False
            
        # Verificar se não são palavras comuns de cabeçalho/total
        palavras_invalidas = ['total', 'subtotal', 'soma', 'nome', 'funcionario', 'matricula', 'codigo']
        if valor.lower() in palavras_invalidas:
            return False
            
        # Se passou nos filtros, provavelmente é uma matrícula
        return True
    
    def _encontrar_ultima_coluna_com_dados(self, df: pd.DataFrame) -> str:
        """
        Encontra dinamicamente a última coluna que contém dados não vazios.
        Esta será considerada a coluna de observações.
        """
        try:
            self.logger.info(f"🚨 CRÍTICO DEBUG - _encontrar_ultima_coluna_com_dados INICIADA!")
            self.logger.info(f"🚨 CRÍTICO DEBUG - DataFrame Shape: {df.shape}")
            self.logger.info(f"🚨 CRÍTICO DEBUG - Colunas: {list(df.columns)}")
            
            # Verificar colunas da direita para a esquerda
            for col in reversed(df.columns):
                self.logger.info(f"🚨 CRÍTICO DEBUG - Verificando coluna: '{col}'")
                
                # Verificar se a coluna tem pelo menos alguns dados não nulos
                dados_nao_nulos = df[col].dropna()
                self.logger.info(f"🚨 CRÍTICO DEBUG - Coluna '{col}': {len(dados_nao_nulos)} valores não nulos")
                
                if len(dados_nao_nulos) > 0:
                    # Verificar se são dados textuais (potenciais observações)
                    dados_texto = []
                    for val in dados_nao_nulos:
                        str_val = str(val).strip()
                        if str_val and str_val.lower() != 'nan':
                            dados_texto.append(str_val)
                    
                    self.logger.info(f"🚨 CRÍTICO DEBUG - Coluna '{col}': {len(dados_texto)} dados textuais válidos")
                    self.logger.info(f"🚨 CRÍTICO DEBUG - Exemplos: {dados_texto[:3]}")
                    
                    if dados_texto:
                        self.logger.info(f"✅ CRÍTICO DEBUG - COLUNA ENCONTRADA: '{col}' com {len(dados_texto)} observações")
                        return col
                        
            self.logger.warning(f"❌ CRÍTICO DEBUG - NENHUMA coluna com dados encontrada!")
            return None
            
        except Exception as e:
            self.logger.error(f"🚨 ERRO CRÍTICO em _encontrar_ultima_coluna_com_dados: {e}")
            import traceback
            self.logger.error(f"🚨 TRACEBACK CRÍTICO: {traceback.format_exc()}")
            return None
    
    def _extrair_matricula_colunas_anteriores(self, linha: pd.Series, coluna_obs: str, colunas: pd.Index) -> str:
        """
        Procura por matrícula nas colunas anteriores à coluna de observação.
        """
        try:
            # Encontrar índice da coluna de observação
            idx_coluna_obs = list(colunas).index(coluna_obs)
            
            # 🚨 DEBUG CRÍTICO: Log detalhado para ADMISSÃO ABRIL
            self.logger.info(f"🚨 DEBUG MATRÍCULA - Processando linha com obs coluna '{coluna_obs}' (índice {idx_coluna_obs})")
            self.logger.info(f"🚨 DEBUG MATRÍCULA - Colunas disponíveis: {list(colunas)}")
            
            # Verificar colunas anteriores (da direita para a esquerda)
            for i in range(idx_coluna_obs - 1, -1, -1):
                col_nome = colunas[i]
                valor = linha[col_nome]
                
                self.logger.info(f"🚨 DEBUG MATRÍCULA - Coluna '{col_nome}': valor={valor} (tipo: {type(valor)})")
                
                if pd.notna(valor):
                    valor_str = str(valor).strip()
                    self.logger.info(f"🚨 DEBUG MATRÍCULA - Testando '{valor_str}' - É válida? {self._validar_matricula(valor_str)}")
                    if self._validar_matricula(valor_str):
                        self.logger.info(f"✅ DEBUG MATRÍCULA - ENCONTRADA: '{valor_str}' na coluna '{col_nome}'")
                        return valor_str
            
            # Se não encontrou matrícula, identificar tipo de linha
            tipo_linha = self._identificar_tipo_linha_vr(linha, colunas)
            return f"SEM_MATRICULA_{tipo_linha.upper()}"
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao extrair matrícula das colunas anteriores: {e}")
            return "ERRO_EXTRACAO"
    
    def _identificar_tipo_linha_vr(self, linha: pd.Series, colunas: pd.Index) -> str:
        """
        Identifica o tipo de linha quando não há matrícula específica.
        
        Args:
            linha: Série pandas com dados da linha
            colunas: Índice das colunas
            
        Returns:
            Tipo identificado da linha
        """
        # Converter todos os valores da linha para string para análise
        valores_linha = []
        for col in colunas:
            if pd.notna(linha[col]):
                valores_linha.append(str(linha[col]).lower())
        
        linha_texto = ' '.join(valores_linha)
        
        # Identificar padrões comuns
        if any(palavra in linha_texto for palavra in ['total', 'subtotal', 'soma']):
            return 'total'
        elif any(palavra in linha_texto for palavra in ['nome', 'matricula', 'funcionario']):
            return 'cabecalho'
        elif any(palavra in linha_texto for palavra in ['observa', 'obs', 'geral', 'diferenca', 'dif']):
            return 'observacao_geral'
        else:
            return 'desconhecido'
    
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
    
    def _processar_observacao_individual(self, observacao: Dict, dados_vr: pd.DataFrame, modelo: str, 
                                       tipo_obs: str, indice: int, total: int) -> Dict:
        """
        Processa uma observação individual usando LLM.
        
        Args:
            observacao: Dicionário com dados da observação
            dados_vr: DataFrame com dados atuais do VR
            modelo: Modelo LLM a usar
            tipo_obs: Tipo da observação (CRÍTICA/OPERACIONAL)
            indice: Índice atual da observação
            total: Total de observações deste tipo
            
        Returns:
            Dicionário com regra sugerida pela LLM
        """
        try:
            self.logger.info(f"┌─ 📝 OBSERVAÇÃO {tipo_obs} {indice}/{total}")
            self.logger.info(f"├─ 📄 Planilha: {observacao.get('planilha', 'N/A')}")
            self.logger.info(f"├─ 🏷️  Matrícula: {observacao.get('matricula', 'N/A')}")
            self.logger.info(f"├─ 📝 Conteúdo: {str(observacao.get('observacao', ''))[:50]}...")
            
            # Log dos dados completos da linha se disponíveis
            dados_linha = observacao.get('dados_linha_completa', {})
            if dados_linha and dados_linha != {'erro': 'Não foi possível extrair dados da linha'}:
                self.logger.info(f"├─ 📊 Dados da linha completa:")
                for campo, valor in list(dados_linha.items())[:5]:  # Limitar a 5 campos nos logs
                    if valor is not None and str(valor) != 'nan':
                        self.logger.info(f"│  └─ {campo}: {valor}")
            
            # Verificar se funcionário existe no dataset atual
            funcionario_encontrado = False
            matricula = observacao.get('matricula')
            
            # Tratamento especial para observações sem matrícula específica
            # Garantir que matricula seja string para operações de string
            matricula_str = str(matricula) if matricula is not None else ""
            
            if matricula and matricula_str.startswith("SEM_MATRICULA_"):
                tipo_linha = matricula_str.replace("SEM_MATRICULA_", "").lower()
                self.logger.info(f"├─ ⚠️ Tipo: Observação {tipo_linha} (sem matrícula específica)")
                funcionario_encontrado = False
            elif matricula and matricula_str not in ['N/A', 'ERRO_EXTRACAO', 'nan']:
                funcionario_encontrado = matricula in dados_vr['Matricula'].values
                self.logger.info(f"├─ 👤 Funcionário no dataset: {'✅ Sim' if funcionario_encontrado else '❌ Não'}")
            else:
                self.logger.info(f"├─ 👤 Funcionário no dataset: ❓ Matrícula inválida ({matricula})")
            
            # Preparar contexto específico para esta observação
            prompt = self._criar_prompt_observacao_individual(observacao, dados_vr, funcionario_encontrado)
            
            self.logger.info(f"├─ 🤖 Consultando LLM ({modelo})...")
            
            # Consultar LLM
            resposta_llm = self._consultar_ollama(prompt, modelo)
            
            # Processar resposta
            regra_sugerida = self._processar_resposta_observacao_individual(resposta_llm, observacao)
            
            if regra_sugerida and regra_sugerida.get('acao') != 'nenhuma':
                self.logger.info(f"├─ ✅ LLM sugeriu: {regra_sugerida.get('acao')}")
                justificativa = regra_sugerida.get('justificativa', '')
                self.logger.info(f"└─ 💡 Motivo: {justificativa[:80]}...")
            else:
                self.logger.info(f"└─ ⚪ LLM não sugeriu ajustes para esta observação")
                
            return regra_sugerida
            
        except Exception as e:
            self.logger.error(f"└─ ❌ Erro ao processar observação {indice}: {e}")
            return None
    
    def _criar_prompt_observacao_individual(self, observacao: Dict, dados_vr: pd.DataFrame, 
                                          funcionario_encontrado: bool) -> str:
        """
        Cria prompt contextualizado para análise individual de observação.
        
        Args:
            observacao: Dados da observação
            dados_vr: DataFrame com dados do VR
            funcionario_encontrado: Se o funcionário está no dataset
            
        Returns:
            Prompt formatado para a LLM
        """
        matricula = observacao.get('matricula', 'N/A')
        planilha = observacao.get('planilha', 'N/A')
        conteudo = str(observacao.get('observacao', ''))

        # Contexto dos dados completos da linha onde a observação foi encontrada
        contexto_linha_completa = ""
        dados_linha = observacao.get('dados_linha_completa', {})
        if dados_linha and dados_linha != {'erro': 'Não foi possível extrair dados da linha'}:
            contexto_linha_completa = "\nDADOS COMPLETOS DA LINHA ONDE A OBSERVAÇÃO FOI ENCONTRADA:"
            for campo, valor in dados_linha.items():
                if valor is not None and str(valor) != 'nan':
                    contexto_linha_completa += f"\n- {campo}: {valor}"
            contexto_linha_completa += "\n"

        # Contexto do funcionário se encontrado no dataset VR
        contexto_funcionario = ""
        if funcionario_encontrado and matricula != 'N/A':
            funcionario_data = dados_vr[dados_vr['Matricula'] == matricula].iloc[0]
            contexto_funcionario = f"""
DADOS ATUAIS DO FUNCIONÁRIO NO DATASET VR (Matrícula {matricula}):
- Nome: {funcionario_data.get('Nome', 'N/A')}
- Valor VR Total: R$ {funcionario_data.get('TOTAL', 0):.2f}
- Custo Empresa: R$ {funcionario_data.get('Custo empresa', 0):.2f}
- Desconto Funcionário: R$ {funcionario_data.get('Desconto profissional', 0):.2f}
- Dias Trabalho: {funcionario_data.get('Dias trabalho', 'N/A')}
"""

        # Contexto específico por planilha baseado na análise das colunas
        contexto_planilha = self._obter_contexto_planilha(planilha)

        # Contexto especial para observações sem matrícula específica
        contexto_sem_matricula = ""
        matricula_str = str(matricula) if matricula is not None else ""
        if matricula and matricula_str.startswith("SEM_MATRICULA_"):
            tipo_linha = matricula_str.replace("SEM_MATRICULA_", "").lower()
            contexto_sem_matricula = f"""
⚠️ OBSERVAÇÃO ESPECIAL - SEM MATRÍCULA ESPECÍFICA:
Esta observação foi encontrada em uma linha do tipo '{tipo_linha}' que não possui matrícula de funcionário específico.

POSSÍVEIS INTERPRETAÇÕES:
• TOTAL/SUBTOTAL: Observação sobre cálculos gerais ou resumos
• CABEÇALHO: Observação informativa sobre a planilha
• OBSERVAÇÃO_GERAL: Regra ou ajuste que se aplica a múltiplos funcionários
• DESCONHECIDO: Linha não identificada claramente

AÇÃO RECOMENDADA:
- Se for regra geral que afeta múltiplos funcionários: analisar para possível aplicação
- Se for apenas informativo/total: responder com {{"acao": "nenhuma"}}
- Priorize ações apenas se houver impacto claro no cálculo de VR
"""

        prompt = f"""Você é um especialista em análise de dados de RH e Vale Refeição.

TAREFA: Analise a observação abaixo e determine se é necessário fazer algum ajuste específico.

OBSERVAÇÃO PARA ANÁLISE:
- Planilha: {planilha}
- Matrícula: {matricula}
- Conteúdo: "{conteudo}"
{contexto_linha_completa}
{contexto_funcionario}
{contexto_sem_matricula}

{contexto_planilha}

CONTEXTO GERAL:
- Sistema de Vale Refeição mensal
- Valor padrão por dia: baseado em sindicato
- Descontos e ajustes baseados em observações
- Funcionário {'ESTÁ' if funcionario_encontrado else 'NÃO ESTÁ'} no dataset atual

INSTRUÇÕES:
1. Analise se a observação indica necessidade de ajuste específico
2. Considere apenas ações práticas aplicáveis via pandas
3. Responda APENAS em formato JSON válido
4. Se não houver ajuste necessário, responda com {{"acao": "nenhuma"}}

TIPOS DE AJUSTES POSSÍVEIS:
- "excluir": Remover funcionário do dataset
- "ajustar_valor": Modificar valor do VR
- "ajustar_dias": Modificar dias trabalhados
- "nenhuma": Nenhum ajuste necessário

FORMATO DA RESPOSTA (JSON):
{{
  "acao": "tipo_da_acao",
  "valor": "valor_numerico_se_aplicavel",
  "justificativa": "razão_para_o_ajuste",
  "confianca": "alta/media/baixa"
}}

RESPOSTA:"""
        return prompt
    
    def _obter_contexto_planilha(self, planilha: str) -> str:
        """
        Obtém contexto específico baseado na planilha de origem.
        
        Args:
            planilha: Nome da planilha
            
        Returns:
            Contexto específico para a planilha
        """
        planilha_normalizada = planilha.upper().replace(' ', '_')
        
        if 'ADMISSAO' in planilha_normalizada or 'ABRIL' in planilha_normalizada:
            return """CONTEXTO ESPECÍFICO - PLANILHA ADMISSÃO ABRIL:
Esta planilha contém funcionários admitidos em abril que devem receber VR integral em maio:

SITUAÇÕES IDENTIFICADAS:
• "demitido": Funcionário foi demitido - DEVE SER EXCLUÍDO do VR
• "não recebe VR": Funcionário não tem direito ao benefício - EXCLUIR
• "transferido": Funcionário mudou de setor/filial
• Observações sobre situações especiais de admissão

AÇÃO RECOMENDADA: 
- "demitido"/"não recebe" = EXCLUSÃO obrigatória
- Outras situações = analisar caso a caso
CONFIANÇA: ALTA - Observações claras sobre status do funcionário."""

        elif 'DESLIGADOS' in planilha_normalizada or 'DESLIGADO' in planilha_normalizada:
            return """CONTEXTO ESPECÍFICO - PLANILHA DESLIGADOS:
Esta planilha contém funcionários desligados com regras específicas por data:

REGRA APLICADA NO SISTEMA:
• Desligados até dia 15: Exclusão total (não recebem VR)
• Desligados após dia 15: VR proporcional calculado automaticamente

SITUAÇÕES IDENTIFICADAS:
• Contadores de desligamentos (ex: "47 desligamentos com comunicado OK")
• Observações sobre comunicação de desligamentos
• Status de processamento dos desligamentos

AÇÃO RECOMENDADA: Geralmente informativo
CONFIANÇA: MÉDIA - Observações principalmente estatísticas."""

        elif 'AFASTAMENTO' in planilha_normalizada:
            return """CONTEXTO ESPECÍFICO - PLANILHA AFASTAMENTOS:
Esta planilha contém funcionários afastados (licenças, saúde, etc.):

SITUAÇÕES IDENTIFICADAS:
• "retorno de férias + licença em DD/MM": Data de retorno
• "retorno da licença em DD/MM": Fim do afastamento
• Descrições de tipo de afastamento (maternidade, saúde, etc.)

AÇÃO RECOMENDADA:
- Datas de retorno podem indicar ajuste de dias trabalhados
- Períodos parciais requerem cálculo proporcional
CONFIANÇA: MÉDIA - Requer interpretação de datas e períodos."""

        elif 'VR MENSAL' in planilha_normalizada or 'VR_MENSAL' in planilha_normalizada:
            return """CONTEXTO ESPECÍFICO - PLANILHA VR MENSAL (MAIS IMPORTANTE):
Esta é a planilha principal com observações gerais e ajustes manuais. É a FONTE MAIS CRÍTICA de informações:

SITUAÇÕES FREQUENTES IDENTIFICADAS:
• "DESLIGAMENTO - REMOVIDO": Funcionário deve ser EXCLUÍDO
• Diferenças de VR por mudança de horário/valor (ex: "DIF DE VR... VALOR: X")  
• Correções de desconto indevido (ex: "(+) X dias Y valor")
• "ALTERAÇÃO DE FILIAL - AJUSTADO MANUALMENTE": Ajustes por mudança
• "EXTERIOR": Ajustes para funcionários que retornaram/saíram do exterior
• "(+/-) X DIF POR...": Correções de diferenças de pagamento
• "removido afastado": Funcionário afastado removido

PADRÕES DE VALORES:
- Valores específicos mencionados devem ser aplicados (ex: "R$ 450,00")
- Diferenças calculadas devem ser somadas/subtraídas
- Menções a dias específicos indicam ajuste proporcional

AÇÃO RECOMENDADA: ANALISAR DETALHADAMENTE - alta probabilidade de ajuste necessário.
CONFIANÇA: ALTA - Observações diretas da planilha de processamento."""

        elif 'EXTERIOR' in planilha_normalizada:
            return """CONTEXTO ESPECÍFICO - PLANILHA EXTERIOR:
Esta planilha contém funcionários em situação especial no exterior:

SITUAÇÕES IDENTIFICADAS:
• "desligado": Funcionário foi desligado - DEVE SER EXCLUÍDO
• "RETORNOU DO EXTERIOR": Funcionário retornou, pode precisar ajuste
• "removido": Funcionário foi removido da lista - DEVE SER EXCLUÍDO
• Situações dinâmicas de mudança de status

AÇÃO RECOMENDADA: 
- "desligado"/"removido" = EXCLUSÃO
- "retornou" = possível ajuste de valores ou dias
CONFIANÇA: ALTA - Situações bem definidas no exterior."""

        elif 'FERIAS' in planilha_normalizada or 'FÉRIAS' in planilha_normalizada:
            return """CONTEXTO ESPECÍFICO - PLANILHA DE FÉRIAS:
Esta planilha contém funcionários em férias durante o período:

SITUAÇÕES IDENTIFICADAS:
• Confirmação de status de férias
• Informações sobre período de férias
• Possíveis ajustes por período parcial

AÇÃO RECOMENDADA: 
- Observações geralmente informativas
- Períodos parciais podem requerer ajuste de dias
CONFIANÇA: BAIXA - Observações geralmente descritivas."""

        elif 'ATIVOS' in planilha_normalizada:
            return """CONTEXTO ESPECÍFICO - PLANILHA ATIVOS:
Esta planilha contém funcionários ativos no mês:

SITUAÇÕES IDENTIFICADAS:
• Status de funcionários ativos
• Confirmações de elegibilidade para VR
• Observações sobre situações especiais

AÇÃO RECOMENDADA: Observações geralmente informativas
CONFIANÇA: BAIXA - Status de funcionários ativos raramente requer ajuste."""

        else:
            return """CONTEXTO GERAL:
Planilha não reconhecida especificamente. Análise baseada no conteúdo da observação:

AÇÃO RECOMENDADA: 
- Focar no conteúdo específico da observação
- Considerar padrões comuns (valores, datas, ações)
CONFIANÇA: MÉDIA - Análise baseada apenas no conteúdo."""
    
    def _processar_resposta_observacao_individual(self, resposta: str, observacao: Dict) -> Dict:
        """
        Processa a resposta da LLM para uma observação individual.
        
        Args:
            resposta: Resposta JSON da LLM
            observacao: Dados da observação original
            
        Returns:
            Dicionário com regra processada
        """
        try:
            # Tentar extrair JSON da resposta
            resposta_limpa = resposta.strip()
            
            # Procurar por JSON na resposta
            inicio_json = resposta_limpa.find('{')
            fim_json = resposta_limpa.rfind('}') + 1
            
            if inicio_json >= 0 and fim_json > inicio_json:
                json_str = resposta_limpa[inicio_json:fim_json]
                
                try:
                    dados = json.loads(json_str)
                    
                    # Validar campos obrigatórios
                    if 'acao' in dados:
                        return {
                            'id': f"regra_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(observacao)) % 10000}",
                            'acao': dados.get('acao', 'nenhuma'),
                            'valor': dados.get('valor'),
                            'justificativa': dados.get('justificativa', 'Sem justificativa'),
                            'confianca': dados.get('confianca', 'baixa'),
                            'planilha_origem': observacao.get('planilha', 'N/A'),
                            'matricula_origem': observacao.get('matricula', 'N/A'),
                            'observacao_original': observacao
                        }
                    
                except json.JSONDecodeError as e:
                    self.logger.warning(f"⚠️ Erro ao decodificar JSON da resposta LLM: {e}")
            
            return None
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao processar resposta individual: {e}")
            return None
    
    def _aplicar_regra_customizada_individual(self, dados_vr: pd.DataFrame, regra: Dict, 
                                            observacao: Dict) -> Tuple[pd.DataFrame, Optional[Dict]]:
        """
        Aplica uma regra customizada individual descoberta pela LLM.
        
        Args:
            dados_vr: DataFrame com dados do VR
            regra: Regra a ser aplicada
            observacao: Observação que originou a regra
            
        Returns:
            Tuple com dados atualizados e regra aplicada (se houver)
        """
        try:
            dados_antes = len(dados_vr)
            registros_afetados = []
            matricula = observacao.get('matricula')
            
            self.logger.info(f"  🔧 Aplicando regra: {regra.get('acao')} (Confiança: {regra.get('confianca')})")
            
            # AÇÃO: EXCLUIR funcionário
            if regra.get('acao') == 'excluir' and matricula and matricula != 'N/A':
                mask = dados_vr['Matricula'] == matricula
                if mask.any():
                    funcionario = dados_vr[mask].iloc[0]
                    dados_vr = dados_vr[~mask]
                    registros_afetados.append({
                        'matricula': matricula,
                        'nome': funcionario.get('Nome', 'N/A'),
                        'acao': 'excluído',
                        'motivo': regra.get('justificativa', ''),
                        'observacao': str(observacao.get('observacao', ''))[:100]
                    })
                    self.logger.info(f"  ✅ Funcionário {matricula} excluído")
                else:
                    self.logger.warning(f"  ⚠️ REGRA NÃO APLICADA: Funcionário {matricula} não está no dataset atual (já pode estar desligado)")
                    registros_afetados.append({
                        'matricula': matricula,
                        'nome': 'N/A - Não encontrado no dataset',
                        'acao': 'TENTATIVA DE EXCLUSÃO - NÃO APLICADA',
                        'motivo': f"Funcionário não está no dataset atual. {regra.get('justificativa', '')}",
                        'observacao': str(observacao.get('observacao', ''))[:100]
                    })
            
            # AÇÃO: AJUSTAR VALOR
            elif regra.get('acao') == 'ajustar_valor' and matricula and matricula != 'N/A':
                mask = dados_vr['Matricula'] == matricula
                if mask.any():
                    try:
                        valor_ajuste = float(regra.get('valor', 0))
                        valor_anterior = dados_vr.loc[mask, 'TOTAL'].iloc[0]
                        
                        dados_vr.loc[mask, 'TOTAL'] = valor_ajuste
                        dados_vr.loc[mask, 'Custo empresa'] = valor_ajuste * 0.8
                        dados_vr.loc[mask, 'Desconto profissional'] = valor_ajuste * 0.2
                        
                        registros_afetados.append({
                            'matricula': matricula,
                            'nome': dados_vr.loc[mask, 'Nome'].iloc[0],
                            'acao': f'valor ajustado: R$ {valor_anterior:.2f} → R$ {valor_ajuste:.2f}',
                            'motivo': regra.get('justificativa', ''),
                            'observacao': str(observacao.get('observacao', ''))[:100]
                        })
                        self.logger.info(f"  ✅ Valor ajustado: R$ {valor_anterior:.2f} → R$ {valor_ajuste:.2f}")
                    except ValueError:
                        self.logger.warning(f"  ⚠️ Valor inválido para ajuste: {regra.get('valor')}")
                else:
                    self.logger.warning(f"  ⚠️ REGRA NÃO APLICADA: Funcionário {matricula} não está no dataset atual (pode estar afastado/licenciado)")
                    registros_afetados.append({
                        'matricula': matricula,
                        'nome': 'N/A - Não encontrado no dataset',
                        'acao': f'TENTATIVA DE AJUSTE VALOR R$ {regra.get("valor", 0)} - NÃO APLICADA',
                        'motivo': f"Funcionário não está no dataset atual. {regra.get('justificativa', '')}",
                        'observacao': str(observacao.get('observacao', ''))[:100]
                    })
            
            # AÇÃO: AJUSTAR DIAS
            elif regra.get('acao') == 'ajustar_dias' and matricula and matricula != 'N/A':
                mask = dados_vr['Matricula'] == matricula
                if mask.any():
                    try:
                        dias_ajuste = int(regra.get('valor', 0))
                        dias_anterior = dados_vr.loc[mask, 'Dias trabalho'].iloc[0]
                        valor_diario = dados_vr.loc[mask, 'TOTAL'].iloc[0] / max(dias_anterior, 1)
                        
                        novo_total = valor_diario * dias_ajuste
                        dados_vr.loc[mask, 'Dias trabalho'] = dias_ajuste
                        dados_vr.loc[mask, 'TOTAL'] = novo_total
                        dados_vr.loc[mask, 'Custo empresa'] = novo_total * 0.8
                        dados_vr.loc[mask, 'Desconto profissional'] = novo_total * 0.2
                        
                        registros_afetados.append({
                            'matricula': matricula,
                            'nome': dados_vr.loc[mask, 'Nome'].iloc[0],
                            'acao': f'dias ajustados: {dias_anterior} → {dias_ajuste} dias',
                            'motivo': regra.get('justificativa', ''),
                            'observacao': str(observacao.get('observacao', ''))[:100]
                        })
                        self.logger.info(f"  ✅ Dias ajustados: {dias_anterior} → {dias_ajuste}")
                    except ValueError:
                        self.logger.warning(f"  ⚠️ Valor inválido para dias: {regra.get('valor')}")
                else:
                    self.logger.warning(f"  ⚠️ REGRA NÃO APLICADA: Funcionário {matricula} não está no dataset atual (pode estar afastado/licenciado)")
                    registros_afetados.append({
                        'matricula': matricula,
                        'nome': 'N/A - Não encontrado no dataset',
                        'acao': f'TENTATIVA DE AJUSTE DIAS {regra.get("valor", 0)} - NÃO APLICADA',
                        'motivo': f"Funcionário não está no dataset atual. {regra.get('justificativa', '')}",
                        'observacao': str(observacao.get('observacao', ''))[:100]
                    })
            
            # Casos especiais de regras não aplicáveis
            else:
                acao = regra.get('acao', 'desconhecida')
                if not matricula or matricula in ['N/A', 'ERRO_EXTRACAO']:
                    motivo_especial = "Observação sem matrícula específica válida"
                elif str(matricula).startswith("SEM_MATRICULA_"):
                    motivo_especial = "Observação de linha geral/cabeçalho (sem funcionário específico)"
                else:
                    motivo_especial = "Matrícula não encontrada ou ação não suportada"
                    
                self.logger.warning(f"  ⚠️ REGRA NÃO APLICADA: {acao.upper()} - {motivo_especial}")
                registros_afetados.append({
                    'matricula': str(matricula) if matricula else 'N/A',
                    'nome': 'N/A - Caso especial',
                    'acao': f'TENTATIVA DE {acao.upper()} - NÃO APLICADA',
                    'motivo': f"{motivo_especial}. {regra.get('justificativa', '')}",
                    'observacao': str(observacao.get('observacao', ''))[:100]
                })
            
            dados_depois = len(dados_vr)
            
            # Sempre retornar regra registrada (aplicada ou não)
            if registros_afetados:
                # Determinar se foi realmente aplicada ou apenas tentada
                aplicada_efetivamente = any('NÃO APLICADA' not in reg.get('acao', '') for reg in registros_afetados)
                
                regra_aplicada = {
                    'id': regra.get('id'),
                    'acao': regra.get('acao'),
                    'justificativa': regra.get('justificativa'),
                    'confianca': regra.get('confianca'),
                    'registros_antes': dados_antes,
                    'registros_depois': dados_depois,
                    'registros_afetados': len(registros_afetados),
                    'detalhes_afetados': registros_afetados,
                    'data_aplicacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status_aplicacao': 'APLICADA' if aplicada_efetivamente else 'NÃO APLICADA',
                    'observacao_origem': {
                        'planilha': observacao.get('planilha'),
                        'matricula': observacao.get('matricula'),
                        'conteudo': str(observacao.get('observacao', ''))[:200]
                    }
                }
                
                if aplicada_efetivamente:
                    self.logger.info(f"  ✅ Regra aplicada com sucesso: {len(registros_afetados)} registros afetados")
                else:
                    self.logger.warning(f"  ⚠️ Regra registrada mas não aplicada: {len(registros_afetados)} tentativas")
                
                return dados_vr, regra_aplicada
            
            # Caso extremo - nenhum registro foi criado
            self.logger.error(f"  ❌ Erro inesperado: Regra {regra.get('acao')} não gerou nem tentativa de aplicação")
            return dados_vr, None
            
        except Exception as e:
            self.logger.error(f"  ❌ Erro ao aplicar regra individual: {e}")
            return dados_vr, None
    
    def _consultar_ollama(self, prompt: str, modelo: str = None) -> str:
        """
        Consulta o servidor Ollama com o prompt fornecido.
        
        Args:
            prompt: Prompt para a LLM
            modelo: Modelo específico a usar
            
        Returns:
            Resposta da LLM
        """
        try:
            modelo_usar = modelo or self.ollama_model
            self.logger.info(f"🤖 Consultando modelo {modelo_usar} em {self.ollama_host}...")
            
            # Inicializar cliente Ollama
            client = ollama.Client(host=self.ollama_host)
            
            response = client.chat(
                model=modelo_usar,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            )
            
            return response['message']['content']
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao consultar Ollama em {self.ollama_host}: {e}")
            # Fallback com regras básicas baseadas em padrões conhecidos
            return self._gerar_resposta_fallback()
    
    def _gerar_resposta_fallback(self) -> str:
        """
        Gera uma resposta fallback quando a LLM não está disponível.
        
        Returns:
            Resposta JSON padrão
        """
        return '{"acao": "nenhuma", "justificativa": "LLM não disponível - análise automática não realizada", "confianca": "baixa"}'
    
    def gerar_aba_regras_customizadas(self, writer, regras_aplicadas: List[Dict]):
        """
        Gera aba com documentação das regras customizadas aplicadas pela LLM.
        
        Args:
            writer: ExcelWriter para adicionar a aba
            regras_aplicadas: Lista de regras aplicadas
        """
        try:
            self.logger.info("📝 Gerando aba de regras customizadas aplicadas...")
            
            # Cabeçalho informativo
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            # Separar regras aplicadas vs não aplicadas
            regras_efetivamente_aplicadas = [r for r in regras_aplicadas if r.get('status_aplicacao') == 'APLICADA']
            regras_nao_aplicadas = [r for r in regras_aplicadas if r.get('status_aplicacao') == 'NÃO APLICADA']
            
            info_processamento = [
                {
                    'INFORMAÇÃO': 'Data de Processamento',
                    'VALOR': timestamp
                },
                {
                    'INFORMAÇÃO': 'Total de Sugestões da LLM',
                    'VALOR': len(regras_aplicadas)
                },
                {
                    'INFORMAÇÃO': 'Regras Efetivamente Aplicadas',
                    'VALOR': len(regras_efetivamente_aplicadas)
                },
                {
                    'INFORMAÇÃO': 'Regras NÃO Aplicadas (motivo)',
                    'VALOR': len(regras_nao_aplicadas)
                },
                {
                    'INFORMAÇÃO': 'Status do Processamento',
                    'VALOR': 'Concluído com Sucesso' if regras_aplicadas else 'Concluído - Nenhuma Sugestão da LLM'
                },
                {
                    'INFORMAÇÃO': 'Modelo LLM Utilizado',
                    'VALOR': self.ollama_model
                },
                {
                    'INFORMAÇÃO': 'Host Ollama',
                    'VALOR': self.ollama_host
                }
            ]
            
            # DataFrame com informações do processamento
            df_info = pd.DataFrame(info_processamento)
            df_info.to_excel(
                writer,
                sheet_name='Regras_Customizadas_Aplicadas',
                index=False,
                startrow=0
            )
            
            if regras_aplicadas and len(regras_aplicadas) > 0:
                # Separar dados por status de aplicação
                dados_regras_aplicadas = []
                dados_regras_nao_aplicadas = []
                detalhes_aplicadas = []
                detalhes_nao_aplicadas = []
                
                for regra in regras_aplicadas:
                    regra_data = {
                        'ID da Regra': regra.get('id', ''),
                        'Ação': regra.get('acao', ''),
                        'Status': regra.get('status_aplicacao', 'N/A'),
                        'Registros Antes': regra.get('registros_antes', 0),
                        'Registros Depois': regra.get('registros_depois', 0),
                        'Registros Afetados': regra.get('registros_afetados', 0),
                        'Motivação': regra.get('justificativa', ''),
                        'Data de Processamento': regra.get('data_aplicacao', ''),
                        'Planilha de Origem': regra.get('observacao_origem', {}).get('planilha', ''),
                        'Matrícula de Origem': regra.get('observacao_origem', {}).get('matricula', ''),
                        'Observação Original': regra.get('observacao_origem', {}).get('conteudo', '')[:100]
                    }
                    
                    # Separar por status
                    if regra.get('status_aplicacao') == 'APLICADA':
                        dados_regras_aplicadas.append(regra_data)
                        for detalhe in regra.get('detalhes_afetados', []):
                            detalhes_aplicadas.append({
                                'ID da Regra': regra.get('id', ''),
                                'Matrícula': detalhe.get('matricula', ''),
                                'Ação Realizada': detalhe.get('acao', ''),
                                'Motivo': detalhe.get('motivo', ''),
                                'Observação': detalhe.get('observacao', '')[:80]
                            })
                    else:
                        dados_regras_nao_aplicadas.append(regra_data)
                        for detalhe in regra.get('detalhes_afetados', []):
                            detalhes_nao_aplicadas.append({
                                'ID da Regra': regra.get('id', ''),
                                'Matrícula': detalhe.get('matricula', ''),
                                'Tentativa de Ação': detalhe.get('acao', ''),
                                'Motivo da NÃO Aplicação': detalhe.get('motivo', ''),
                                'Observação': detalhe.get('observacao', '')[:80]
                            })
                
                current_row = len(df_info) + 3
                worksheet = writer.sheets['Regras_Customizadas_Aplicadas']
                
                # SEÇÃO 1: REGRAS EFETIVAMENTE APLICADAS
                if dados_regras_aplicadas:
                    worksheet.cell(row=current_row, column=1, value="🟢 REGRAS EFETIVAMENTE APLICADAS PELA LLM:")
                    current_row += 1
                    
                    df_aplicadas = pd.DataFrame(dados_regras_aplicadas)
                    df_aplicadas.to_excel(
                        writer,
                        sheet_name='Regras_Customizadas_Aplicadas',
                        index=False,
                        startrow=current_row
                    )
                    current_row += len(df_aplicadas) + 2
                    
                    if detalhes_aplicadas:
                        worksheet.cell(row=current_row, column=1, value="📋 DETALHES DOS REGISTROS MODIFICADOS:")
                        current_row += 1
                        
                        df_detalhes_aplicadas = pd.DataFrame(detalhes_aplicadas)
                        df_detalhes_aplicadas.to_excel(
                            writer,
                            sheet_name='Regras_Customizadas_Aplicadas',
                            index=False,
                            startrow=current_row
                        )
                        current_row += len(df_detalhes_aplicadas) + 3
                
                # SEÇÃO 2: REGRAS NÃO APLICADAS (COM MOTIVO)
                if dados_regras_nao_aplicadas:
                    worksheet.cell(row=current_row, column=1, value="🟡 REGRAS SUGERIDAS PELA LLM MAS NÃO APLICADAS:")
                    current_row += 1
                    
                    df_nao_aplicadas = pd.DataFrame(dados_regras_nao_aplicadas)
                    df_nao_aplicadas.to_excel(
                        writer,
                        sheet_name='Regras_Customizadas_Aplicadas',
                        index=False,
                        startrow=current_row
                    )
                    current_row += len(df_nao_aplicadas) + 2
                    
                    if detalhes_nao_aplicadas:
                        worksheet.cell(row=current_row, column=1, value="📋 DETALHES DAS TENTATIVAS NÃO APLICADAS:")
                        current_row += 1
                        
                        df_detalhes_nao_aplicadas = pd.DataFrame(detalhes_nao_aplicadas)
                        df_detalhes_nao_aplicadas.to_excel(
                            writer,
                            sheet_name='Regras_Customizadas_Aplicadas',
                            index=False,
                            startrow=current_row
                        )
            
            else:
                # Caso não haja regras aplicadas - mostrar explicação
                explicacao = [
                    {
                        'OBSERVAÇÃO': 'Nenhuma regra customizada foi aplicada pela LLM',
                        'POSSÍVEIS MOTIVOS': ''
                    },
                    {
                        'OBSERVAÇÃO': '1. Todas as observações foram analisadas como adequadas',
                        'POSSÍVEIS MOTIVOS': 'LLM determinou que não há ajustes necessários'
                    },
                    {
                        'OBSERVAÇÃO': '2. Não foram encontradas observações críticas nas planilhas',
                        'POSSÍVEIS MOTIVOS': 'Planilhas sem colunas de observação preenchidas'
                    },
                    {
                        'OBSERVAÇÃO': '3. Erro de comunicação com servidor Ollama',
                        'POSSÍVEIS MOTIVOS': 'Verificar conectividade e configuração'
                    }
                ]
                
                df_explicacao = pd.DataFrame(explicacao)
                df_explicacao.to_excel(
                    writer,
                    sheet_name='Regras_Customizadas_Aplicadas',
                    index=False,
                    startrow=len(df_info) + 3
                )
                
                # Adicionar cabeçalho para seção explicativa
                worksheet = writer.sheets['Regras_Customizadas_Aplicadas']
                worksheet.cell(row=len(df_info) + 2, column=1, value="ANÁLISE DO PROCESSAMENTO:")
            
            self.logger.info(f"✅ Aba de regras customizadas criada com {len(regras_aplicadas)} regras")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar aba de regras customizadas: {e}")
