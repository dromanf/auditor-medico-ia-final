import os
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv

# 1. CARGAR CONFIGURACIÓN
load_dotenv()

# Inicializar cliente de Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

# 2. CONFIGURAR CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURACIÓN DE RUTAS PARA VERCEL ---
# Esto localiza el CSV sin importar si ejecutas desde / o desde /backend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "clean.csv")

# 3. GESTIÓN DE MEMORIA Y DATOS
historial_clinico = []

class ConsultaMedica(BaseModel):
    sintomas: str
    examen: str

def obtener_protocolo_csv(nombre_examen_usuario):
    """
    Busca de forma flexible el examen en el archivo clean.csv usando rutas absolutas
    """
    try:
        if not os.path.exists(CSV_PATH):
            print(f"Error: No se encuentra el archivo en {CSV_PATH}")
            return None
            
        df = pd.read_csv(CSV_PATH)
        busqueda = nombre_examen_usuario.lower().strip()
        
        # Filtro flexible
        filtro = df['Nombre del Examen'].str.lower().str.contains(busqueda, na=False)
        resultado = df[filtro]
        
        if not resultado.empty:
            return resultado.iloc[0].to_dict()
        return None
    except Exception as e:
        print(f"Error procesando el CSV: {e}")
        return None

# 4. RUTA PRINCIPAL
@app.post("/validar")
async def validar_consulta(datos: ConsultaMedica):
    try:
        # A. Buscar información en tu base de datos (CSV) con la nueva ruta
        info_csv = obtener_protocolo_csv(datos.examen)
        
        if info_csv:
            contexto_reglas = f"""
            REGLAS OFICIALES DEL SEGURO PARA ESTE EXAMEN:
            - Nombre exacto: {info_csv['Nombre del Examen']}
            - Costo: ${info_csv['Costo']}
            - Especialidad: {info_csv['Especialidad']}
            - Protocolo de Aplicación: {info_csv['Protocolo']}
            """
        else:
            contexto_reglas = "ADVERTENCIA: El examen solicitado no figura en el listado oficial de costos y protocolos."

        # B. Contexto de Memoria
        contexto_memoria = ""
        if historial_clinico:
            ultimos = historial_clinico[-2:]
            contexto_memoria = "HISTORIAL RECIENTE DEL PACIENTE:\n" + "\n".join(
                [f"- Síntomas previos: {h['sintomas']} | Examen previo: {h['examen']}" for h in ultimos]
            )

        # C. Construcción del Prompt
        prompt_sistema = f"""
        Eres un Auditor Médico Experto. Tu función es evaluar si un examen es pertinente basándote en protocolos.
        
        {contexto_reglas}
        
        {contexto_memoria}

        INSTRUCCIONES DE FORMATO:
        Debes responder de forma estructurada con estos encabezados exactos:
        ESTADO: [PROCEDENTE o ALERTA]
        ANÁLISIS TÉCNICO: (Justificación basada en el Protocolo del CSV y coherencia clínica)
        PARA EL PACIENTE: (Explicación sencilla)
        RESUMEN ECONÓMICO: (Menciona el costo del CSV y si se justifica el gasto)
        """

        prompt_usuario = f"SÍNTOMAS ACTUALES: {datos.sintomas}\nEXAMEN SOLICITADO: {datos.examen}"

        # D. Llamada a Groq
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            temperature=0.1
        )

        respuesta_ia = completion.choices[0].message.content

        # E. Actualizar Memoria
        historial_clinico.append({"sintomas": datos.sintomas, "examen": datos.examen})

        return {"respuesta": respuesta_ia}

    except Exception as e:
        print(f"ERROR EN EL SERVIDOR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")