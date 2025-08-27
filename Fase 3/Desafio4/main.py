#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SERVIÇO FASTAPI PARA PROCESSAMENTO VR MENSAL
============================================

Este serviço recebe um arquivo ZIP contendo planilhas Excel de dados de RH,
processa os dados conforme regras específicas e retorna a planilha VR MENSAL
devidamente preenchida com os valores calculados.

Endpoints:
- POST /processar-planilhas: Recebe ZIP e retorna VR MENSAL preenchido
- GET /health: Verificação de saúde do serviço
- GET /: Documentação interativa

Planilhas processadas:
- ATIVOS.xlsx, ADMISSÃO ABRIL.xlsx, DESLIGADOS.xlsx
- AFASTAMENTOS.xlsx, FÉRIAS.xlsx, ESTÁGIO.xlsx, APRENDIZ.xlsx
- EXTERIOR.xlsx, Base sindicato x valor.xlsx, Base dias uteis.xlsx
- VR MENSAL 05.2025.xlsx (template)

Autor: Sistema de Processamento VR MENSAL
Data: 2025
Versão: 2.0
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import tempfile
import zipfile
import os
import logging
from pathlib import Path
from datetime import datetime
import shutil
from typing import Dict, Any
import json

from processador_vr_mensal import ProcessadorVRMensal

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Criar instância do FastAPI
app = FastAPI(
    title="Processador VR MENSAL",
    description="API especializada no processamento e preenchimento da planilha VR MENSAL",
    version="2.0.0",
    docs_url="/",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Página inicial com instruções de uso.
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Processador de Dados de RH</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .upload-area { 
                border: 2px dashed #ccc; 
                padding: 40px; 
                text-align: center; 
                margin: 20px 0;
                border-radius: 10px;
            }
            .btn { 
                background: #007bff; 
                color: white; 
                padding: 10px 20px; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer;
                font-size: 16px;
            }
            .btn:hover { background: #0056b3; }
            .status { margin: 20px 0; padding: 10px; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .processing { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏢 Processador de Dados de RH</h1>
            <p>Este serviço processa planilhas Excel de dados de RH e gera uma planilha consolidada.</p>
            
            <h2>📋 Como usar:</h2>
            <ol>
                <li>Comprima todas as planilhas Excel em um arquivo ZIP</li>
                <li>Faça upload do arquivo ZIP usando o formulário abaixo</li>
                <li>Aguarde o processamento (pode levar alguns minutos)</li>
                <li>Baixe a planilha consolidada gerada</li>
            </ol>
            
            <h2>📁 Planilhas esperadas no ZIP:</h2>
            <ul>
                <li>ADMISSÃO ABRIL.xlsx</li>
                <li>AFASTAMENTOS.xlsx</li>
                <li>APRENDIZ.xlsx</li>
                <li>ATIVOS.xlsx</li>
                <li>Base dias uteis.xlsx</li>
                <li>Base sindicato x valor.xlsx</li>
                <li>DESLIGADOS.xlsx</li>
                <li>ESTÁGIO.xlsx</li>
                <li>EXTERIOR.xlsx</li>
                <li>FÉRIAS.xlsx</li>
                <li>VR MENSAL 05.2025.xlsx</li>
            </ul>
            
            <div class="upload-area">
                <h3>📤 Upload do arquivo ZIP</h3>
                <form id="uploadForm" enctype="multipart/form-data">
                    <input type="file" id="zipFile" name="file" accept=".zip" required style="margin: 10px;">
                    <br>
                    <button type="submit" class="btn">Processar Planilhas</button>
                </form>
                
                <div id="status" style="display: none;"></div>
                <div id="download" style="display: none;"></div>
            </div>
            
            <h2>🔗 Links úteis:</h2>
            <ul>
                <li><a href="/docs">📚 Documentação da API (Swagger)</a></li>
                <li><a href="/redoc">📖 Documentação alternativa (ReDoc)</a></li>
                <li><a href="/health">❤️ Status de saúde do serviço</a></li>
            </ul>
        </div>
        
        <script>
            document.getElementById('uploadForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const fileInput = document.getElementById('zipFile');
                const statusDiv = document.getElementById('status');
                const downloadDiv = document.getElementById('download');
                
                if (!fileInput.files[0]) {
                    alert('Por favor, selecione um arquivo ZIP.');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                statusDiv.style.display = 'block';
                statusDiv.className = 'status processing';
                statusDiv.innerHTML = '⏳ Processando planilhas... Isso pode levar alguns minutos.';
                downloadDiv.style.display = 'none';
                
                try {
                    const response = await fetch('/processar-planilhas', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'dados_consolidados_rh.xlsx';
                        
                        statusDiv.className = 'status success';
                        statusDiv.innerHTML = '✅ Processamento concluído com sucesso!';
                        
                        downloadDiv.style.display = 'block';
                        downloadDiv.innerHTML = '<button class="btn" onclick="this.previousElementSibling.click()">⬇️ Baixar Planilha Consolidada</button>';
                        downloadDiv.insertBefore(a, downloadDiv.firstChild);
                        a.style.display = 'none';
                        a.click();
                        
                    } else {
                        const error = await response.json();
                        statusDiv.className = 'status error';
                        statusDiv.innerHTML = '❌ Erro no processamento: ' + error.detail;
                    }
                } catch (error) {
                    statusDiv.className = 'status error';
                    statusDiv.innerHTML = '❌ Erro de conexão: ' + error.message;
                }
            });
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """
    Verificação de saúde do serviço.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Processador de Dados de RH",
        "version": "1.0.0"
    }

@app.post("/processar-planilhas")
async def processar_planilhas(
    file: UploadFile = File(...),
    ollama_host: str = Query(None, description="URL do servidor Ollama remoto (ex: http://servidor:11434)"),
    ollama_model: str = Query(None, description="Modelo Ollama a usar (ex: llama2, llama3, codellama, mistral)")
):
    """
    Processa planilhas de RH e retorna a planilha VR MENSAL preenchida.
    
    Este endpoint processa todas as planilhas de dados de RH, aplica as regras
    de validação e cálculos específicos, utiliza LLM via Ollama para descobrir
    regras customizadas baseadas em observações, e retorna a planilha VR MENSAL
    devidamente preenchida com os valores calculados e aba de regras aplicadas.
    
    Args:
        file: Arquivo ZIP contendo todas as planilhas necessárias
        ollama_host: URL do servidor Ollama remoto (opcional)
        ollama_model: Modelo Ollama a usar para análise (opcional, padrão: llama2)
    
    Planilhas necessárias no ZIP:
    - ATIVOS.xlsx, ADMISSÃO ABRIL.xlsx, DESLIGADOS.xlsx
    - AFASTAMENTOS.xlsx, FÉRIAS.xlsx, ESTÁGIO.xlsx, APRENDIZ.xlsx
    - EXTERIOR.xlsx, Base sindicato x valor.xlsx, Base dias uteis.xlsx
    - VR MENSAL 05.2025.xlsx (template)
    
    Args:
        file: Arquivo ZIP contendo as planilhas Excel de RH
        
    Returns:
        FileResponse: Planilha VR MENSAL preenchida
    """
    
    # Validar arquivo
    if not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="Arquivo deve ser um ZIP (.zip)"
        )
    
    # Criar diretório temporário
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            logger.info(f"Iniciando processamento do arquivo: {file.filename}")
            
            # Salvar arquivo ZIP
            zip_path = temp_path / "planilhas.zip"
            with open(zip_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            logger.info(f"Arquivo ZIP salvo: {zip_path}")
            
            # Extrair ZIP
            extract_path = temp_path / "planilhas"
            extract_path.mkdir()
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            logger.info(f"Arquivo ZIP extraído em: {extract_path}")
            
            # Listar arquivos extraídos
            arquivos_extraidos = [f.name for f in extract_path.rglob("*.xlsx")]
            logger.info(f"Arquivos Excel encontrados: {arquivos_extraidos}")
            
            if not arquivos_extraidos:
                raise HTTPException(
                    status_code=400,
                    detail="Nenhum arquivo Excel (.xlsx) encontrado no ZIP"
                )
            
            # Processar dados com foco no VR MENSAL (com Ollama customizado se especificado)
            processador = ProcessadorVRMensal(str(extract_path), para_api=True, ollama_host=ollama_host, ollama_model=ollama_model)
            
            # Executar processamento VR MENSAL específico
            sucesso, resultado = processador.executar_processamento_vr_completo()
            
            if not sucesso:
                raise HTTPException(
                    status_code=500,
                    detail=f"Erro durante o processamento VR MENSAL: {resultado}"
                )
            
            # O resultado já é o caminho do arquivo VR MENSAL gerado
            arquivo_vr_mensal = Path(resultado)
            
            logger.info(f"VR MENSAL gerado: {arquivo_vr_mensal}")
            
            # Verificar se arquivo foi criado
            if not arquivo_vr_mensal.exists():
                raise HTTPException(
                    status_code=500,
                    detail="Erro ao gerar planilha VR MENSAL"
                )
            
            # Copiar arquivo para fora do diretório temporário
            final_file_path = temp_path.parent / f"VR_MENSAL_05_2025_final.xlsx"
            shutil.copy2(arquivo_vr_mensal, final_file_path)
            
            # Retornar arquivo VR MENSAL preenchido
            return FileResponse(
                path=str(final_file_path),
                filename="VR_MENSAL_05_2025_preenchido.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro inesperado: {str(e)}")
            logger.error(f"Traceback completo: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro interno do servidor: {str(e)}"
            )

@app.get("/info")
async def service_info():
    """
    Informações sobre o serviço.
    """
    return {
        "service": "Processador de Dados de RH",
        "version": "1.0.0",
        "description": "API para processamento de planilhas Excel de dados de RH",
        "endpoints": {
            "/": "Página inicial e interface web",
            "/processar-planilhas": "POST - Processar arquivo ZIP com planilhas",
            "/health": "GET - Verificação de saúde",
            "/info": "GET - Informações do serviço",
            "/docs": "GET - Documentação Swagger",
            "/redoc": "GET - Documentação ReDoc"
        },
        "arquivos_esperados": [
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
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
