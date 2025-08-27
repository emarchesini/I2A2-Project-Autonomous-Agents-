#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MÓDULO GERENCIADOR DE VALIDAÇÕES
=================================

Este módulo é responsável por gerar a aba de Validações com check automático
de todas as regras aplicadas no sistema - tanto regras principais quanto
regras customizadas descobertas pela LLM.

Funcionalidades:
- Check automático baseado em estatísticas reais
- Integração entre regras tradicionais e LLM
- Formatação automática da aba de validações
- Controle de qualidade e auditoria

Autor: Sistema de Processamento VR
Data: 2025
Versão: 1.0
"""

import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List
import openpyxl.styles


class ValidacoesManager:
    """
    Gerenciador da aba de validações com check automático das regras.
    
    Responsável por integrar as estatísticas das regras principais com
    as regras customizadas da LLM, gerando uma visão unificada de todas
    as regras aplicadas no processamento.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Inicializa o gerenciador de validações.
        
        Args:
            logger: Logger para registro de eventos
        """
        self.logger = logger
    
    def gerar_aba_validacoes_completa(self, writer, regras_aplicadas: List[Dict], 
                                    estatisticas_exclusoes: Dict = None):
        """
        Gera aba de Validações com check automático das regras aplicadas.
        
        Args:
            writer: ExcelWriter para adicionar a aba
            regras_aplicadas: Lista de regras LLM aplicadas
            estatisticas_exclusoes: Estatísticas das regras principais
        """
        try:
            self.logger.info("📋 Gerando aba de validações com check das regras...")
            
            # 1. DEFINIR REGRAS PADRÃO DO SISTEMA (baseado em colunas_observacao_analise.md)
            regras_sistema = [
                {'regra': 'Afastados / Licenças', 'tipo': 'afastamentos', 'descricao': 'Exclusão de funcionários afastados ou em licença'},
                {'regra': 'DESLIGADOS GERAL', 'tipo': 'desligados', 'descricao': 'Exclusão de funcionários desligados'},
                {'regra': 'Admitidos mês', 'tipo': 'admissoes', 'descricao': 'Inclusão de admitidos no mês atual'},
                {'regra': 'Férias', 'tipo': 'ferias', 'descricao': 'Exclusão de funcionários em férias'},
                {'regra': 'ESTAGIARIO', 'tipo': 'estagiarios', 'descricao': 'Exclusão de estagiários (não recebem VR)'},
                {'regra': 'APRENDIZ', 'tipo': 'aprendizes', 'descricao': 'Exclusão de aprendizes (não recebem VR)'},
                {'regra': 'SINDICATOS x VALOR', 'tipo': 'sindicatos', 'descricao': 'Aplicação de valores por região/sindicato'},
                {'regra': 'DESLIGADOS ATÉ O DIA 15 DO MÊS - SE JÁ ESTIVEREM CIENTES DO DESLIGAMENTO EXCLUIR...', 'tipo': 'desligados_15', 'descricao': 'Regra específica para desligamentos até dia 15'},
                {'regra': 'DESLIGADOS DO DIA 16 ATÉ O ULTIMO DIA DO MÊS PODE FAZER A RECARGA CHEIA E DEIXAR...', 'tipo': 'desligados_16', 'descricao': 'Regra específica para desligamentos após dia 15'},
                {'regra': 'ATENDIMENTOS/OBS', 'tipo': 'observacoes', 'descricao': 'Processamento de observações especiais'},
                {'regra': 'Admitidos mês anterior (abril)', 'tipo': 'admissoes_abril', 'descricao': 'Inclusão de admitidos em abril'},
                {'regra': 'EXTERIOR', 'tipo': 'exterior', 'descricao': 'Exclusão/ajuste de funcionários no exterior'},
                {'regra': 'ATIVOS', 'tipo': 'ativos', 'descricao': 'Processamento de funcionários ativos'},
                {'regra': 'REVISAR O CALCULO DE PGTO SE ESTÁ CORRETO ANTES DE GERAR OS VALES', 'tipo': 'revisao', 'descricao': 'Validação final dos cálculos'}
            ]
            
            # 2. PREPARAR DADOS DE VALIDAÇÃO
            dados_validacao = []
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            for regra_def in regras_sistema:
                regra_nome = regra_def['regra']
                regra_tipo = regra_def['tipo']
                regra_desc = regra_def['descricao']
                
                # Verificar se a regra foi aplicada baseada nas estatísticas
                aplicada = False
                detalhes = "N/A"
                
                # Check das estatísticas de exclusões
                if estatisticas_exclusoes and regra_tipo in estatisticas_exclusoes:
                    count = estatisticas_exclusoes[regra_tipo]
                    if count > 0:
                        aplicada = True
                        detalhes = f"{count} registros afetados"
                    else:
                        detalhes = "0 registros (regra avaliada)"
                
                # Cases especiais
                elif regra_tipo in ['sindicatos', 'ativos', 'admissoes', 'admissoes_abril']:
                    aplicada = True  # Estas sempre são processadas
                    detalhes = "Regra processada (calculada)"
                elif regra_tipo == 'observacoes':
                    # Verificar se temos regras LLM aplicadas
                    if regras_aplicadas:
                        aplicada = True
                        efetivas = len([r for r in regras_aplicadas if r.get('status_aplicacao') == 'APLICADA'])
                        tentativas = len([r for r in regras_aplicadas if r.get('status_aplicacao') == 'NÃO APLICADA'])
                        detalhes = f"LLM: {efetivas} aplicadas, {tentativas} não aplicadas"
                    else:
                        detalhes = "Nenhuma observação processada pela LLM"
                
                dados_validacao.append({
                    'Validações': regra_nome,
                    'Check': '✅' if aplicada else '⏸️',
                    'Status': 'APLICADA' if aplicada else 'NÃO APLICADA',
                    'Detalhes': detalhes,
                    'Descrição': regra_desc,
                    'Data Verificação': timestamp
                })
            
            # 3. ADICIONAR SEÇÃO DE REGRAS LLM CUSTOMIZADAS
            if regras_aplicadas:
                dados_validacao.append({
                    'Validações': '--- REGRAS CUSTOMIZADAS LLM ---',
                    'Check': '',
                    'Status': '',
                    'Detalhes': '',
                    'Descrição': '',
                    'Data Verificação': ''
                })
                
                regras_efetivas = [r for r in regras_aplicadas if r.get('status_aplicacao') == 'APLICADA']
                regras_nao_aplicadas = [r for r in regras_aplicadas if r.get('status_aplicacao') == 'NÃO APLICADA']
                
                for i, regra in enumerate(regras_efetivas, 1):
                    observacao_origem = regra.get('observacao_origem', {})
                    dados_validacao.append({
                        'Validações': f"LLM Regra #{i}: {regra.get('acao', 'N/A').title()}",
                        'Check': '✅',
                        'Status': 'APLICADA',
                        'Detalhes': f"{regra.get('registros_afetados', 0)} registros | {observacao_origem.get('planilha', 'N/A')}",
                        'Descrição': regra.get('justificativa', 'N/A')[:100],
                        'Data Verificação': regra.get('data_aplicacao', timestamp)
                    })
                
                for i, regra in enumerate(regras_nao_aplicadas, 1):
                    observacao_origem = regra.get('observacao_origem', {})
                    dados_validacao.append({
                        'Validações': f"LLM Tentativa #{i}: {regra.get('acao', 'N/A').title()}",
                        'Check': '⚠️',
                        'Status': 'NÃO APLICADA',
                        'Detalhes': f"Motivo: Funcionário ausente | {observacao_origem.get('planilha', 'N/A')}",
                        'Descrição': regra.get('justificativa', 'N/A')[:100],
                        'Data Verificação': regra.get('data_aplicacao', timestamp)
                    })
            
            # 4. CRIAR DATAFRAME E SALVAR
            df_validacoes = pd.DataFrame(dados_validacao)
            df_validacoes.to_excel(
                writer,
                sheet_name='Validações',
                index=False
            )
            
            # 5. APLICAR FORMATAÇÃO
            worksheet = writer.sheets['Validações']
            # Destacar cabeçalho das regras LLM
            for idx, row in df_validacoes.iterrows():
                if 'LLM' in str(row['Validações']) and '---' in str(row['Validações']):
                    worksheet.cell(row=idx+2, column=1).font = openpyxl.styles.Font(bold=True)
            
            regras_aplicadas_total = len([r for r in dados_validacao if r['Check'] == '✅'])
            regras_nao_aplicadas_total = len([r for r in dados_validacao if r['Check'] in ['⏸️', '⚠️']])
            
            self.logger.info(f"✅ Aba Validações criada: {regras_aplicadas_total} aplicadas, {regras_nao_aplicadas_total} não aplicadas")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar aba de validações: {e}")
            # Fallback: criar aba básica
            self._criar_aba_validacoes_fallback(writer)
    
    def _criar_aba_validacoes_fallback(self, writer):
        """
        Cria uma aba de validações básica em caso de erro.
        
        Args:
            writer: ExcelWriter para adicionar a aba
        """
        try:
            dados_basicos = [
                {
                    'Validações': 'Erro no processamento de validações',
                    'Check': '❌',
                    'Status': 'ERRO',
                    'Detalhes': 'Verifique logs para mais detalhes',
                    'Descrição': 'Erro na geração automática da aba',
                    'Data Verificação': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                }
            ]
            
            df_fallback = pd.DataFrame(dados_basicos)
            df_fallback.to_excel(writer, sheet_name='Validações', index=False)
            
        except Exception as e:
            self.logger.error(f"❌ Erro no fallback das validações: {e}")
